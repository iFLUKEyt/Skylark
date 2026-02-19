"""Streamlit-friendly Google Sheets helpers.

This module reads service-account credentials from `st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]`
or from the environment variable `GOOGLE_SERVICE_ACCOUNT_JSON`. It safely parses
the JSON and normalizes the `private_key` so the google-auth library can consume it.

Design choices:
- Avoids reading credential files from disk so it's deployment-safe.
- Provides clear RuntimeError messages with logging for deploy-time debugging.
"""

from typing import Optional, Dict, Any
import os
import json
import logging
import pandas as pd

log = logging.getLogger(__name__)

try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GS = True
except Exception:
    HAS_GS = False


def _load_service_account_info() -> Optional[Dict[str, Any]]:
    """Load and return service-account info dict from Streamlit secrets or env.

    Returns a parsed dict or None. Raises RuntimeError when JSON is present but invalid.
    """
    payload = None
    # Try Streamlit secrets first if available
    try:
        import streamlit as st
        if 'GOOGLE_SERVICE_ACCOUNT_JSON' in st.secrets:
            payload = st.secrets['GOOGLE_SERVICE_ACCOUNT_JSON']
        elif 'google' in st.secrets and 'service_account' in st.secrets['google']:
            payload = st.secrets['google']['service_account']
    except Exception:
        payload = None

    # Fallback to env var
    if payload is None:
        payload = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')

    if not payload:
        return None

    # If payload already a dict (Streamlit parsed TOML), use it
    if isinstance(payload, dict):
        info = payload
    else:
        # Attempt to parse JSON string
        try:
            info = json.loads(payload)
        except Exception as e:
            # Try a tolerant repair: replace literal "\\n" sequences with actual newlines
            try:
                repaired = payload.replace('\\n', '\n')
                info = json.loads(repaired)
            except Exception as e2:
                log.exception('Failed to parse service-account JSON')
                raise RuntimeError(f'Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e2}') from e2

    # Normalize private_key to contain real newlines (some formats store \n)
    try:
        pk = info.get('private_key')
        if isinstance(pk, str) and '\\n' in pk:
            info['private_key'] = pk.replace('\\n', '\n')
    except Exception:
        # non-fatal
        pass

    return info


def get_credentials() -> Credentials:
    """Return a google.oauth2.service_account.Credentials built from secrets.

    Raises RuntimeError with a helpful message when credentials are missing or invalid.
    """
    if not HAS_GS:
        raise RuntimeError('gspread/google-auth are not installed in the environment')

    info = _load_service_account_info()
    if not info:
        raise RuntimeError('No service-account JSON found in st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"] or in the GOOGLE_SERVICE_ACCOUNT_JSON environment variable.')

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]

    try:
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return creds
    except Exception as e:
        log.exception('Failed to construct Credentials from provided service-account info')
        raise RuntimeError(f'Failed to build credentials from provided JSON: {e}') from e


def read_sheet(sheet_id: str, sheet_name: str = 'Sheet1') -> pd.DataFrame:
    """Open a sheet and return its contents as a DataFrame.

    Raises RuntimeError with an explanatory message on failure.
    """
    if not HAS_GS:
        raise RuntimeError('gspread/google-auth libraries are not available')

    creds = get_credentials()
    try:
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
    except Exception as e:
        log.exception('Failed to open spreadsheet')
        raise RuntimeError(f'Failed to open spreadsheet {sheet_id}: {e}') from e

    try:
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        log.exception('Failed to read worksheet')
        raise RuntimeError(f'Failed to read worksheet {sheet_name} from spreadsheet {sheet_id}: {e}') from e


def write_sheet(df: pd.DataFrame, sheet_id: str, sheet_name: str = 'Sheet1') -> None:
    """Write a DataFrame to a worksheet. Raises RuntimeError on failure."""
    if not HAS_GS:
        raise RuntimeError('gspread/google-auth libraries are not available')

    creds = get_credentials()
    try:
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
    except Exception as e:
        log.exception('Failed to open spreadsheet for write')
        raise RuntimeError(f'Failed to open spreadsheet {sheet_id}: {e}') from e

    try:
        try:
            ws = sh.worksheet(sheet_name)
        except Exception:
            ws = sh.add_worksheet(title=sheet_name, rows=df.shape[0] + 10, cols=df.shape[1] + 5)
        ws.clear()
        ws.update([df.columns.values.tolist()] + df.fillna('').astype(str).values.tolist())
    except Exception as e:
        log.exception('Failed to write worksheet')
        raise RuntimeError(f'Failed to write worksheet {sheet_name} to spreadsheet {sheet_id}: {e}') from e


def check_connectivity(sheet_id: str) -> Dict[str, Any]:
    """Return diagnostics about whether Sheets can be accessed.

    Keys: has_gs, creds_present, client_email, can_open, worksheets, error
    """
    out = {
        'has_gs': HAS_GS,
        'creds_present': False,
        'client_email': None,
        'can_open': False,
        'worksheets': [],
        'error': None,
    }

    if not HAS_GS:
        out['error'] = 'gspread/google-auth not installed.'
        return out

    # quick check for presence of JSON (don't try building creds here)
    try:
        info = _load_service_account_info()
        if info:
            out['creds_present'] = True
            out['client_email'] = info.get('client_email')
        else:
            out['error'] = 'No service-account JSON found in st.secrets or GOOGLE_SERVICE_ACCOUNT_JSON env var.'
            return out
    except Exception as e:
        out['error'] = str(e)
        return out

    # Try full auth + open
    try:
        creds = get_credentials()
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
        out['can_open'] = True
        out['worksheets'] = [ws.title for ws in sh.worksheets()]
    except Exception as e:
        log.exception('Connectivity check failed')
        out['error'] = str(e)

    return out
