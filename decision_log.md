Decision Log — Skylark Drone Ops Coordinator Prototype

Assumptions
- The provided CSVs act as the canonical local dataset for the prototype. Google Sheets sync is implemented as an integration that requires user-provided service account credentials.
- Missions may optionally include `assigned_pilot` and `assigned_drone` columns; matching functions return candidates but do not auto-write assignments.
- Weather compatibility is simplified: any `weather_resistance` string containing `IP` is considered rain-capable.

Trade-offs
- I prioritized a small, runnable Streamlit prototype over a full production orchestration setup. This keeps the demo testable without external credentials.
- Conflict detection is conservative and rule-based (pairwise mission checks) rather than building a scheduling engine — this is faster to implement and easier to reason about for the assignment.

What I'd do with more time
- Add robust scheduling engine (interval tree) and conversion to/from timezone-aware datetimes.
- Implement two-way live sync with Google Sheets including conflict resolution strategy and change logs.
- Add user authentication, audit trail, and an automated assignment recommender that can simulate cost vs. skills trade-offs.

Urgent Reassignments interpretation
- I interpret "urgent reassignments" as: detect when an active mission is at risk (weather, maintenance, pilot unavailable) and propose immediate fallback candidates (next-best pilot/drone meeting skills and budget constraints) with an estimated cost and ETA.
