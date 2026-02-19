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
import json
import pandas as pd
import logging

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GS = True
except Exception:
    HAS_GS = False


def _get_credentials():
    """Return google.oauth2.service_account.Credentials built from either:
    - a file path in `GOOGLE_APPLICATION_CREDENTIALS` (existing behavior), or
    - a JSON string in `GOOGLE_SERVICE_ACCOUNT_JSON` (useful for cloud secrets).
    """
    if not HAS_GS:
        return None
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]
    # Prefer JSON payload from environment variable or Streamlit secrets
    # Streamlit Cloud typically exposes secrets via `st.secrets`, so check
    # there as well if Streamlit is available.
    json_payload = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    # Try common alternate names
    if not json_payload:
        json_payload = os.environ.get('GOOGLE_SERVICE_ACCOUNT') or os.environ.get('SERVICE_ACCOUNT_JSON')
    # Try Streamlit secrets if present
    if not json_payload:
        try:
            import streamlit as _st
            # check several common keys that users may name their secret
            for key in ('GOOGLE_SERVICE_ACCOUNT_JSON', 'GOOGLE_SERVICE_ACCOUNT', 'SERVICE_ACCOUNT_JSON'):
                if key in _st.secrets:
                    json_payload = _st.secrets[key]
                    break
            # also allow nested secret like st.secrets['google']['service_account']
            if not json_payload and 'google' in _st.secrets and 'service_account' in _st.secrets['google']:
                json_payload = _st.secrets['google']['service_account']
        except Exception:
            pass
    if json_payload:
        try:
            info = json.loads(json_payload)
            return Credentials.from_service_account_info(info, scopes=scopes)
        except Exception:
            pass
    # Fallback to file path
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    # also look in Streamlit secrets for a path-like entry
    if not creds_path:
        try:
            import streamlit as _st
            if 'GOOGLE_APPLICATION_CREDENTIALS' in _st.secrets:
                creds_path = _st.secrets['GOOGLE_APPLICATION_CREDENTIALS']
        except Exception:
            pass
    if creds_path and os.path.exists(creds_path):
        try:
            return Credentials.from_service_account_file(creds_path, scopes=scopes)
        except Exception:
            pass
    return None


def check_connectivity(sheet_id: str):
    """Return a dict with diagnostics about Sheets connectivity.

    Keys:
    - has_gs: whether gspread/google-auth are importable
    - creds_loaded: whether credentials were found
    - creds_source: 'env_json'|'file'|None
    - client_email: service account email (masked) if available
    - can_open: whether the spreadsheet could be opened
    - worksheets: list of worksheet titles when available
    - error: error message if any
    """
    log = logging.getLogger(__name__)
    out = {
        'has_gs': HAS_GS,
        'creds_loaded': False,
        'creds_source': None,
        'client_email': None,
        'can_open': False,
        'worksheets': [],
        'error': None,
    }
    if not HAS_GS:
        out['error'] = 'gspread/google-auth not installed.'
        return out

    # Check env var payload first
    json_payload = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    if json_payload:
        try:
            info = json.loads(json_payload)
            out['creds_loaded'] = True
            out['creds_source'] = 'env_json'
            out['client_email'] = info.get('client_email')
        except Exception as e:
            out['error'] = f'Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e}'
            return out

    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not out['creds_loaded'] and creds_path:
        if os.path.exists(creds_path):
            try:
                with open(creds_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                out['creds_loaded'] = True
                out['creds_source'] = 'file'
                out['client_email'] = info.get('client_email')
            except Exception as e:
                out['error'] = f'Failed to load credentials file: {e}'
                return out

    if not out['creds_loaded']:
        out['error'] = 'No credentials found in GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS.'
        return out

    try:
        creds = _get_credentials()
        if creds is None:
            out['error'] = 'Credentials were detected but failed to build Credentials object.'
            return out
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        out['can_open'] = True
        out['worksheets'] = [ws.title for ws in sh.worksheets()]
    except Exception as e:
        log.exception('Sheets connectivity check failed')
        out['error'] = str(e)

    return out


def read_sheet(sheet_id: str, sheet_name: str = 'Sheet1') -> Optional[pd.DataFrame]:
    if not HAS_GS:
        return None
    creds = _get_credentials()
    if creds is None:
        return None
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(sheet_name)
    data = ws.get_all_records()
    return pd.DataFrame(data)


def write_sheet(df: pd.DataFrame, sheet_id: str, sheet_name: str = 'Sheet1') -> bool:
    if not HAS_GS:
        return False
    creds = _get_credentials()
    if creds is None:
        return False
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    try:
        ws = sh.worksheet(sheet_name)
    except Exception:
        ws = sh.add_worksheet(title=sheet_name, rows=df.shape[0]+10, cols=df.shape[1]+5)
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.fillna('').astype(str).values.tolist())
    return True
