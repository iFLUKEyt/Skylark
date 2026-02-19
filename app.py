from skylark.logging import setup_logging
setup_logging()

import streamlit as st
from skylark.data import load_dataframes, save_pilots_df
from skylark import sheets
from skylark.logic import (
    find_available_pilots,
    match_pilots_to_mission,
    match_drones_to_mission,
    detect_conflicts,
    suggest_urgent_reassignment,
)


st.set_page_config(page_title="Skylark Drone Ops Coordinator", layout="wide")

# Attempt to load data from Google Sheets. If this fails (missing creds,
# sharing, or tab name mismatch) we catch the error and continue with empty
# tables so the UI remains usable and the user can click "Connect Sheets".
import pandas as pd
try:
    df_pilots, df_drones, df_missions = load_dataframes()
except Exception as e:
    st.error(f"Warning: failed to load sheets: {e}")
    # Create empty dataframes with expected columns so the rest of the UI works
    df_pilots = pd.DataFrame(columns=[
        'pilot_id', 'name', 'skills', 'certifications', 'location', 'status',
        'current_assignment', 'available_from', 'daily_rate_inr'
    ])
    df_drones = pd.DataFrame(columns=[
        'drone_id', 'model', 'capabilities', 'status', 'location',
        'current_assignment', 'maintenance_due', 'weather_resistance'
    ])
    df_missions = pd.DataFrame(columns=[
        'project_id', 'client', 'location', 'required_skills', 'required_certs',
        'start_date', 'end_date', 'priority', 'mission_budget_inr', 'weather_forecast',
        'assigned_pilot', 'assigned_drone'
    ])

st.title("Skylark Drone Operations Coordinator — Prototype")

with st.expander("Pilot Roster"):
    st.dataframe(df_pilots)

with st.expander("Drone Fleet"):
    st.dataframe(df_drones)

with st.expander("Missions"):
    st.dataframe(df_missions)

st.sidebar.header("Queries & Actions")

# Google Sheets connection
DEFAULT_SHEET_ID = '1n7qmPBnCE6ozUZmDXQyP-LKS-prE-0DMz-dLUsu7FLE'
st.sidebar.subheader("Google Sheets Sync")
# Hidden: use the default spreadsheet and default tab names internally.
if st.sidebar.button("Connect Sheets"):
    st.session_state['sheet_id'] = DEFAULT_SHEET_ID
    st.session_state['pilot_sheet'] = st.session_state.get('pilot_sheet','pilot_roster')
    st.session_state['drone_sheet'] = st.session_state.get('drone_sheet','drone_fleet')
    st.session_state['missions_sheet'] = st.session_state.get('missions_sheet','missions')
    sid = st.session_state['sheet_id']
    try:
        sp = sheets.read_sheet(sid, sheet_name=st.session_state['pilot_sheet'])
        sd = sheets.read_sheet(sid, sheet_name=st.session_state['drone_sheet'])
        sm = sheets.read_sheet(sid, sheet_name=st.session_state['missions_sheet'])
        if sp is not None:
            df_pilots = sp
        if sd is not None:
            df_drones = sd
        if sm is not None:
            df_missions = sm
        st.success("Sheets loaded (local CSVs preserved if read failed).")
    except Exception as e:
        st.error(f"Error connecting to sheets: {e}")

query_skill = st.sidebar.text_input("Find pilots by skill (comma separated)")
query_loc = st.sidebar.text_input("Location filter (optional)")

if st.sidebar.button("Query available pilots"):
    skills = [s.strip() for s in query_skill.split(",") if s.strip()]
    results = find_available_pilots(df_pilots, skills, location=query_loc)
    st.sidebar.write(f"Found {len(results)} pilots")
    st.write(results)

st.sidebar.markdown("---")
st.sidebar.header("Assign Pilot -> Mission")
sel_mission = st.sidebar.selectbox("Mission", df_missions['project_id'])
if st.sidebar.button("Suggest matches for selected mission"):
    mission = df_missions[df_missions['project_id'] == sel_mission].iloc[0]
    pilot_matches = match_pilots_to_mission(mission, df_pilots)
    drone_matches = match_drones_to_mission(mission, df_drones)
    st.write("Pilot matches:")
    st.write(pilot_matches)
    st.write("Drone matches:")
    st.write(drone_matches)

if st.sidebar.button("Suggest urgent reassignment"):
    mission = df_missions[df_missions['project_id'] == sel_mission].iloc[0]
    p_cands, d_cands = suggest_urgent_reassignment(mission, df_pilots, df_drones)
    st.write("Urgent pilot candidates:")
    st.write(p_cands)
    st.write("Urgent drone candidates:")
    st.write(d_cands)

st.sidebar.markdown("---")
st.sidebar.header("Apply Assignment")
assign_pilot = st.sidebar.selectbox("Assign pilot", options=["-"] + list(df_pilots['pilot_id']))
assign_drone = st.sidebar.selectbox("Assign drone", options=["-"] + list(df_drones['drone_id']))
if st.sidebar.button("Apply assignment to mission"):
    m_idx = df_missions['project_id'] == sel_mission
    if assign_pilot != "-":
        df_missions.loc[m_idx, 'assigned_pilot'] = assign_pilot
        # mark pilot as Assigned
        df_pilots.loc[df_pilots['pilot_id'] == assign_pilot, 'status'] = 'Assigned'
        df_pilots.loc[df_pilots['pilot_id'] == assign_pilot, 'current_assignment'] = sel_mission
    if assign_drone != "-":
        df_missions.loc[m_idx, 'assigned_drone'] = assign_drone
        df_drones.loc[df_drones['drone_id'] == assign_drone, 'status'] = 'Assigned'
        df_drones.loc[df_drones['drone_id'] == assign_drone, 'current_assignment'] = sel_mission
    # save back
    from skylark.data import save_pilots_df, save_missions_df, save_drones_df
    save_pilots_df(df_pilots)
    save_drones_df(df_drones)
    save_missions_df(df_missions)
    # attempt to write missions back to sheet if connected
    sid = st.session_state.get('sheet_id')
    m_sheet = st.session_state.get('missions_sheet')
    if sid and m_sheet and sheets.HAS_GS:
        try:
            sheets.write_sheet(df_missions, sid, sheet_name=m_sheet)
        except Exception:
            pass
    # refresh the app so displayed dataframes update; use query-param refresh
    import time
    try:
        st.experimental_set_query_params(_refresh=int(time.time()))
    except Exception:
        pass
    st.sidebar.success("Assignment applied and saved to CSV(s).")

st.sidebar.markdown("---")
st.sidebar.header("Conflict Detection")
if st.sidebar.button("Run conflict check"):
    issues = detect_conflicts(df_pilots, df_drones, df_missions)
    if not issues:
        st.success("No conflicts detected")
    else:
        st.warning(f"{len(issues)} issues found")
        for i in issues:
            st.write(i)

st.sidebar.markdown("---")
st.sidebar.header("Update Pilot Status")
pilot_id = st.sidebar.selectbox("Pilot", df_pilots['pilot_id'])
new_status = st.sidebar.selectbox("New status", ["Available", "Assigned", "On Leave", "Unavailable"])
if st.sidebar.button("Update status"):
    df_pilots.loc[df_pilots['pilot_id'] == pilot_id, 'status'] = new_status
    # save locally
    save_pilots_df(df_pilots)
    # attempt to write back to connected sheet if available
    sid = st.session_state.get('sheet_id')
    psheet = st.session_state.get('pilot_sheet')
    if sid and psheet and sheets.HAS_GS:
        ok = False
        try:
            ok = sheets.write_sheet(df_pilots, sid, sheet_name=psheet)
        except Exception:
            ok = False
        if ok:
            st.sidebar.success(f"Updated {pilot_id} -> {new_status} (saved to sheet).")
        else:
            st.sidebar.warning(f"Updated {pilot_id} locally; sheet write failed or not configured.")
    else:
        st.sidebar.success(f"Updated {pilot_id} -> {new_status} (saved to CSV).")
