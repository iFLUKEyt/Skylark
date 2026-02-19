from datetime import timedelta
import pandas as pd


def find_available_pilots(df_pilots: pd.DataFrame, skills: list, location: str = None):
    df = df_pilots.copy()
    df = df[df['status'].str.contains('Available', na=False)]
    if location:
        df = df[df['location'].str.contains(location, na=False)]
    if skills:
        mask = False
        for s in skills:
            mask = mask | df['skills'].str.contains(s, na=False)
        df = df[mask]
    return df


def mission_duration_days(mission_row) -> int:
    sd = mission_row['start_date']
    ed = mission_row['end_date']
    if pd.isna(sd) or pd.isna(ed):
        return 1
    return max(1, (ed - sd).days + 1)


def match_pilots_to_mission(mission_row, df_pilots: pd.DataFrame):
    required_skills = [s.strip() for s in str(mission_row.get('required_skills', '')).split(',') if s.strip()]
    required_certs = [s.strip() for s in str(mission_row.get('required_certs', '')).split(',') if s.strip()]
    loc = mission_row.get('location')
    candidates = df_pilots.copy()
    # NOTE: do not strictly require location; prefer it in ranking. Location filtering
    # may be applied by callers if needed.
    # skill filter
    for s in required_skills:
        candidates = candidates[candidates['skills'].str.contains(s, na=False)]
    # cert filter: require certs
    for c in required_certs:
        candidates = candidates[candidates['certifications'].str.contains(c, na=False)]
    # cost estimate
    days = mission_duration_days(mission_row)
    candidates = candidates.copy()
    candidates['estimated_cost_inr'] = candidates['daily_rate_inr'].astype(float) * days
    # budget flag
    budget = mission_row.get('mission_budget_inr')
    if pd.notna(budget):
        candidates['within_budget'] = candidates['estimated_cost_inr'] <= float(budget)
    else:
        candidates['within_budget'] = True
    return candidates.sort_values(['within_budget', 'estimated_cost_inr'], ascending=[False, True])


def _drone_ok_for_weather(drone_row, weather: str) -> bool:
    wr = str(drone_row.get('weather_resistance', '')).lower()
    if 'rain' in weather.lower():
        return 'ip' in wr
    # default: if None or 'clear' allow
    return True


def match_drones_to_mission(mission_row, df_drones: pd.DataFrame):
    weather = mission_row.get('weather_forecast', '')
    required_skill = mission_row.get('required_skills', '')
    candidates = df_drones.copy()
    # status available
    candidates = candidates[candidates['status'].str.contains('Available', na=False)]
    # capability match (simple substring match) as preference (not strict)
    candidates['capability_match'] = candidates['capabilities'].str.contains(str(required_skill), na=False).astype(int)
    # weather
    candidates['weather_ok'] = candidates.apply(lambda r: _drone_ok_for_weather(r, weather), axis=1)
    return candidates.sort_values(['capability_match', 'weather_ok', 'maintenance_due'], ascending=[False, False, True])


def suggest_urgent_reassignment(mission_row, df_pilots: pd.DataFrame, df_drones: pd.DataFrame, max_candidates: int = 3):
    """Return fallback pilot and drone candidates for an urgent mission.

    Criteria:
    - Pilots: available, skill & cert match, within budget preferred, location match preferred
    - Drones: available, capability match, weather_ok true
    """
    # Build a relaxed candidate list: available pilots, score by skill/cert matches and budget
    loc = mission_row.get('location','')
    req_skills = [s.strip().lower() for s in str(mission_row.get('required_skills','')).split(',') if s.strip()]
    req_certs = [s.strip().lower() for s in str(mission_row.get('required_certs','')).split(',') if s.strip()]

    candidates = df_pilots[df_pilots['status'].str.contains('Available', na=False)].copy()
    candidates['skill_match_count'] = candidates['skills'].str.lower().apply(lambda x: sum(1 for s in req_skills if s in str(x)))
    candidates['cert_match_count'] = candidates['certifications'].str.lower().apply(lambda x: sum(1 for c in req_certs if c in str(x)))
    days = mission_duration_days(mission_row)
    candidates['estimated_cost_inr'] = candidates['daily_rate_inr'].astype(float) * days
    budget = mission_row.get('mission_budget_inr')
    candidates['within_budget'] = True
    if pd.notna(budget):
        candidates['within_budget'] = candidates['estimated_cost_inr'] <= float(budget)
    candidates['loc_match'] = candidates['location'].str.contains(loc, na=False).astype(int)
    # score: prefer more cert & skill matches, within budget, location match, lower cost
    candidates['score'] = (
        candidates['skill_match_count'] * 3 +
        candidates['cert_match_count'] * 4 +
        candidates['within_budget'].astype(int) * 2 +
        candidates['loc_match']
    ) - (candidates['estimated_cost_inr'] / 10000.0)
    pilots = candidates.sort_values(['score', 'estimated_cost_inr'], ascending=[False, True])

    drones = match_drones_to_mission(mission_row, df_drones)
    drones = drones[drones['status'].str.contains('Available', na=False)].copy()
    drones['loc_match'] = drones['location'].str.contains(loc, na=False).astype(int)
    drones['score'] = drones['loc_match'] + drones['weather_ok'].astype(int)*2
    drones = drones.sort_values(['score', 'maintenance_due'], ascending=[False, True])

    return pilots.head(max_candidates), drones.head(max_candidates)


def _overlap(a_start, a_end, b_start, b_end):
    if pd.isna(a_start) or pd.isna(a_end) or pd.isna(b_start) or pd.isna(b_end):
        return False
    latest_start = max(a_start, b_start)
    earliest_end = min(a_end, b_end)
    return latest_start <= earliest_end


def detect_conflicts(df_pilots, df_drones, df_missions):
    issues = []
    # build simple assignment maps
    # check pilot double-booking
    for _, p in df_pilots.iterrows():
        pid = p['pilot_id']
        assigned = df_missions[df_missions['project_id'] == p.get('current_assignment')]
        # if pilot has multiple assignments in missions table, naive overlap check
    # naive pairwise mission checks
    for i, m1 in df_missions.iterrows():
        for j, m2 in df_missions.iterrows():
            if i >= j:
                continue
            # check pilot overlap
            p1 = m1.get('assigned_pilot') if 'assigned_pilot' in m1 else None
            p2 = m2.get('assigned_pilot') if 'assigned_pilot' in m2 else None
            if p1 and p2 and p1 == p2:
                if _overlap(m1['start_date'], m1['end_date'], m2['start_date'], m2['end_date']):
                    issues.append(f"Pilot {p1} double-booked between {m1['project_id']} and {m2['project_id']}")
            # drone overlap
            d1 = m1.get('assigned_drone') if 'assigned_drone' in m1 else None
            d2 = m2.get('assigned_drone') if 'assigned_drone' in m2 else None
            if d1 and d2 and d1 == d2:
                if _overlap(m1['start_date'], m1['end_date'], m2['start_date'], m2['end_date']):
                    issues.append(f"Drone {d1} double-booked between {m1['project_id']} and {m2['project_id']}")
        # skill/cert warnings
        req_skills = [s.strip() for s in str(m1.get('required_skills','')).split(',') if s.strip()]
        ap = m1.get('assigned_pilot') if 'assigned_pilot' in m1 else None
        if ap:
            pilot = df_pilots[df_pilots['pilot_id'] == ap]
            if not pilot.empty:
                pskills = pilot.iloc[0]['skills']
                for rs in req_skills:
                    if rs and rs not in str(pskills):
                        issues.append(f"Pilot {ap} lacks skill {rs} for {m1['project_id']}")
        # weather/drone mismatch
        ad = m1.get('assigned_drone') if 'assigned_drone' in m1 else None
        if ad:
            drone = df_drones[df_drones['drone_id'] == ad]
            if not drone.empty:
                if not _drone_ok_for_weather(drone.iloc[0], m1.get('weather_forecast','')):
                    issues.append(f"Drone {ad} not rated for weather {m1.get('weather_forecast','')} on {m1['project_id']}")
    return issues
