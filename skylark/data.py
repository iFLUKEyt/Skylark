import pandas as pd
from pathlib import Path
from datetime import datetime
import os
from . import sheets


ROOT = Path(__file__).resolve().parents[1]
# This prototype uses Google Sheets as the canonical source. Set a default
# spreadsheet ID here (from the project). The app also sets this ID when
# connecting; keep them in sync.
DEFAULT_SHEET_ID = '1n7qmPBnCE6ozUZmDXQyP-LKS-prE-0DMz-dLUsu7FLE'

# Local CSVs are no longer used as the primary store. If you want local
# persistence re-enable a backup path here.
PILOT_CSV = ROOT / "pilot_roster.csv"
DRONE_CSV = ROOT / "drone_fleet.csv"
MISSIONS_CSV = ROOT / "missions.csv"


def _parse_dates(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")


def load_dataframes(sheet_id: str = None, pilot_sheet: str = 'pilot_roster', drone_sheet: str = 'drone_fleet', missions_sheet: str = 'missions'):
    """
    Load the three dataframes from Google Sheets. This function expects that
    `GOOGLE_APPLICATION_CREDENTIALS` points to a valid service account JSON and
    that the service account has Editor access to the spreadsheet.

    Parameters:
    - sheet_id: Spreadsheet ID. If None, uses DEFAULT_SHEET_ID.
    - pilot_sheet/drone_sheet/missions_sheet: tab names inside the spreadsheet.

    Raises a RuntimeError if Sheets access is not available or reads return None.
    """
    sid = sheet_id or DEFAULT_SHEET_ID
    if not sheets.HAS_GS:
        raise RuntimeError("Google Sheets client libraries are not available. Install gspread and google-auth.")

    df_pilots = sheets.read_sheet(sid, sheet_name=pilot_sheet)
    df_drones = sheets.read_sheet(sid, sheet_name=drone_sheet)
    df_missions = sheets.read_sheet(sid, sheet_name=missions_sheet)

    if df_pilots is None or df_drones is None or df_missions is None:
        raise RuntimeError("Failed to read one or more sheets. Verify `GOOGLE_APPLICATION_CREDENTIALS`, spreadsheet sharing, and tab names.")

    _parse_dates(df_pilots, ["available_from"])
    _parse_dates(df_missions, ["start_date", "end_date"])
    return df_pilots, df_drones, df_missions


def save_pilots_df(df_pilots: pd.DataFrame, sheet_id: str = None, pilot_sheet: str = 'pilot_roster'):
    """Write the pilots dataframe back to the spreadsheet (primary) and also
    optionally to a local CSV if you want a backup.
    """
    sid = sheet_id or DEFAULT_SHEET_ID
    if not sheets.HAS_GS:
        raise RuntimeError("Google Sheets client libraries are not available; cannot save pilots.")
    sheets.write_sheet(df_pilots, sid, sheet_name=pilot_sheet)


def save_missions_df(df_missions: pd.DataFrame, sheet_id: str = None, missions_sheet: str = 'missions'):
    sid = sheet_id or DEFAULT_SHEET_ID
    if not sheets.HAS_GS:
        raise RuntimeError("Google Sheets client libraries are not available; cannot save missions.")
    sheets.write_sheet(df_missions, sid, sheet_name=missions_sheet)


def save_drones_df(df_drones: pd.DataFrame, sheet_id: str = None, drone_sheet: str = 'drone_fleet'):
    sid = sheet_id or DEFAULT_SHEET_ID
    if not sheets.HAS_GS:
        raise RuntimeError("Google Sheets client libraries are not available; cannot save drones.")
    sheets.write_sheet(df_drones, sid, sheet_name=drone_sheet)


if __name__ == "__main__":
    a, b, c = load_dataframes()
    print("Loaded", len(a), "pilots", len(b), "drones", len(c), "missions")
