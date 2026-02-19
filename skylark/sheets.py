"""
Google Sheets sync helpers. This module provides functions that attempt to read/write
to Google Sheets using `gspread`. It falls back to CSV if credentials aren't available.

To enable Google Sheets sync:
 - Create a Google Cloud service account, grant access to the target sheet,
 - Download the JSON key and set env var `GOOGLE_APPLICATION_CREDENTIALS` to its path,
 - Install `gspread` and `google-auth` (included in requirements.txt).

This prototype does not require credentials to run locally using the CSVs.
"""
"""Google Sheets helpers tuned for Streamlit Cloud deployments.

This module reads service-account credentials from `st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"]`
or from the environment variable `GOOGLE_SERVICE_ACCOUNT_JSON`. It safely parses
the JSON and ensures the `private_key` contains actual newlines (not literal "\\n"
sequences) before building `google.oauth2.service_account.Credentials`.

Deployment notes:
- This implementation intentionally avoids reading credential files from disk
  (no `from_service_account_file`) so it is safe for Streamlit Cloud.
- The app expects a TOML triple-quoted JSON in Streamlit Secrets, or the raw
  JSON string in the environment variable `GOOGLE_SERVICE_ACCOUNT_JSON`.
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


def _load_service_account_info_from_secrets() -> Optional[Dict[str, Any]]:
    """Load service account JSON from Streamlit secrets or environment.

    Returns a dict suitable for `Credentials.from_service_account_info` or None.
    Provides helpful error messages when parsing fails.
    """
    # Try Streamlit secrets first (if Streamlit is available in the runtime)
    payload = None
    try:
        import streamlit as st
        # Prefer exact key name
        if 'GOOGLE_SERVICE_ACCOUNT_JSON' in st.secrets:
            payload = st.secrets['GOOGLE_SERVICE_ACCOUNT_JSON']
        # Allow nested secret tables like st.secrets['google']['service_account']
        elif 'google' in st.secrets and 'service_account' in st.secrets['google']:
            payload = st.secrets['google']['service_account']
    except Exception:
        # Streamlit not available or st.secrets not present; fall through
        payload = None

    # Next, try environment variable
    if payload is None:
        payload = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')

    if not payload:
        log.debug('No service account JSON found in st.secrets or GOOGLE_SERVICE_ACCOUNT_JSON env var')
        return None

    # If payload is already a dict (Streamlit may parse TOML into dict), use it
    if isinstance(payload, dict):
        info = payload
    else:
        # payload is expected to be a JSON string; try to parse
        try:
            info = json.loads(payload)
        except Exception as e:
            # Try a common repair: replace literal unescaped newlines inside the private_key
            try:
                s = payload
                # Replace occurrences of '\\n' (two characters) with actual newlines
                # after extracting JSON-like content. Many users paste JSON with escaped
                # newlines; others paste a raw block that can confuse parsing. Attempt
                # a tolerant repair by replacing literal "\\n" sequences so json.loads succeeds.
                repaired = s.replace('\\n', '\n')
                info = json.loads(repaired)
            except Exception as e2:
                log.exception('Failed to parse service account JSON from secrets')
                raise RuntimeError(f'Invalid JSON in GOOGLE_SERVICE_ACCOUNT_JSON: {e2}') from e2

    # Ensure private_key uses real newlines (not literal backslash+n sequences)
    try:
        pk = info.get('private_key')
        if isinstance(pk, str) and '\\n' in pk:
            info['private_key'] = pk.replace('\\n', '\n')
    except Exception:
        # Non-fatal; continue
        pass

    return info


def _get_credentials() -> Optional[Credentials]:
    """Build google.oauth2.service_account.Credentials from secrets.

    Returns Credentials or None. Raises RuntimeError with helpful message
    when parsing fails.
    """
    if not HAS_GS:
        raise RuntimeError('gspread/google-auth not installed')

    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]

    info = _load_service_account_info_from_secrets()
    if not info:
        raise RuntimeError('No service account JSON found in st.secrets["GOOGLE_SERVICE_ACCOUNT_JSON"] or GOOGLE_SERVICE_ACCOUNT_JSON env var')

    try:
        creds = Credentials.from_service_account_info(info, scopes=scopes)
        return creds
    except Exception as e:
        log.exception('Failed to build Credentials from service account info')
        raise RuntimeError(f'Failed to build credentials from provided JSON: {e}') from e


def read_sheet(sheet_id: str, sheet_name: str = 'Sheet1') -> Optional[pd.DataFrame]:
    """Open the spreadsheet and return the worksheet contents as a DataFrame.

    Raises RuntimeError with explanatory messages on failure.
    """
    if not HAS_GS:
        raise RuntimeError('gspread/google-auth libraries are not available')

    creds = _get_credentials()
    gc = gspread.authorize(creds)
    try:
        sh = gc.open_by_key(sheet_id)
    except Exception as e:
        log.exception('Failed to open spreadsheet by key')
        raise RuntimeError(f'Failed to open spreadsheet {sheet_id}: {e}') from e

    try:
        ws = sh.worksheet(sheet_name)
        data = ws.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        log.exception('Failed to read worksheet')
        raise RuntimeError(f'Failed to read worksheet {sheet_name}: {e}') from e


def write_sheet(df: pd.DataFrame, sheet_id: str, sheet_name: str = 'Sheet1') -> bool:
    """Write a DataFrame to the given worksheet. Returns True on success.
    Raises RuntimeError on failure with helpful messages.
    """
    if not HAS_GS:
        raise RuntimeError('gspread/google-auth libraries are not available')

    creds = _get_credentials()
    gc = gspread.authorize(creds)
    try:
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
        return True
    except Exception as e:
        log.exception('Failed to write worksheet')
        raise RuntimeError(f'Failed to write worksheet {sheet_name}: {e}') from e

                                    if ch == '\\':
                                        esc = True
                                        # we will handle the next char in escaped branch
                                    elif ch == '"':
                                        # end of string
                                        idx += 1
                                        break
                                    elif ch == '\n' or ch == '\r':
                                        # replace literal newline with escape sequence
                                        val_chars.append('\\n')
                                        repaired = True
                                    else:
                                        val_chars.append(ch)
                                idx += 1
                            # reconstruct candidate JSON
                            candidate = prefix + ''.join(val_chars) + s[idx-1:]
                            info = json.loads(candidate)
                            return Credentials.from_service_account_info(info, scopes=scopes)
            except Exception:
                pass
            # fallthrough
            return None
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
