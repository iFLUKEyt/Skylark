"""
Google Sheets sync helpers. This module provides functions that attempt to read/write
to Google Sheets using `gspread`. It falls back to CSV if credentials aren't available.

To enable Google Sheets sync:
 - Create a Google Cloud service account, grant access to the target sheet,
 - Download the JSON key and set env var `GOOGLE_APPLICATION_CREDENTIALS` to its path,
 - Install `gspread` and `google-auth` (included in requirements.txt).

This prototype does not require credentials to run locally using the CSVs.
"""
from typing import Optional
import os
import pandas as pd

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GS = True
except Exception:
    HAS_GS = False


def read_sheet(sheet_id: str, sheet_name: str = 'Sheet1') -> Optional[pd.DataFrame]:
    if not HAS_GS:
        return None
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path or not os.path.exists(creds_path):
        return None
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(sheet_name)
    data = ws.get_all_records()
    return pd.DataFrame(data)


def write_sheet(df: pd.DataFrame, sheet_id: str, sheet_name: str = 'Sheet1') -> bool:
    if not HAS_GS:
        return False
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path or not os.path.exists(creds_path):
        return False
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(sheet_name)
    except Exception:
        ws = sh.add_worksheet(title=sheet_name, rows=df.shape[0]+10, cols=df.shape[1]+5)
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.fillna('').astype(str).values.tolist())
    return True
