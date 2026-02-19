# Skylark Drone Ops Coordinator — Prototype

Overview
- Small Streamlit prototype that loads the provided CSVs (`pilot_roster.csv`, `drone_fleet.csv`, `missions.csv`) and provides:
  - Pilot queries, assignment suggestions, drone matching, conflict detection
  - Pilot status update which writes back to `pilot_roster.csv`

Run locally
1. Create a Python environment and install dependencies:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

2. Run the Streamlit app:

```bash
streamlit run app.py
```

Google Sheets sync
- The `skylark/sheets.py` module includes helper functions using `gspread` and a service account JSON key. To enable:
  - Create service account and grant it access to the Google Sheets you want to use.
  - Set `GOOGLE_APPLICATION_CREDENTIALS` to the JSON key path.

Google Sheets 2-way sync setup (detailed)
- Steps to enable read/write to your spreadsheet:
  1. Create a Google Cloud service account (IAM) and generate a JSON key.
  2. In Google Sheets, open the target spreadsheet and share it with the service account email (the JSON contains an email like `svc-account@...`); give Editor access.
  3. On your machine, set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the JSON key path. In PowerShell:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\path\to\service_account_key.json'
```

  4. Run the Streamlit app and use the sidebar `Spreadsheet ID` field to paste your spreadsheet id (for example: `1n7qmPBnCE6ozUZmDXQyP-LKS-prE-0DMz-dLUsu7FLE`), and set the sheet/tab names for Pilots, Drones, Missions (defaults: `pilot_roster`, `drone_fleet`, `missions`). Click `Connect Sheets`.
  5. If connection succeeds, the app will load the sheet tabs into the UI. When you use `Update status` the app will write back to the Pilots sheet. Note: local CSVs are still written as a fallback.

Troubleshooting
- If `Connect Sheets` returns an error, verify:
  - `GOOGLE_APPLICATION_CREDENTIALS` points to the correct JSON file.
  - The spreadsheet is shared with the service account email.
  - The sheet/tab names match the tabs in the spreadsheet (try `Sheet1` if unsure).


Files
- `app.py`: Streamlit app
- `skylark/data.py`: CSV loader + save helpers
- `skylark/logic.py`: Matching and conflict detection
- `skylark/sheets.py`: Google Sheets helpers (optional)
- `decision_log.md`: short decision log
