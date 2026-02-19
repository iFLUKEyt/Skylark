import os, sys
sys.path.append(r"e:\java(personal)\Skylark assessment")
from skylark import sheets

sid = '1n7qmPBnCE6ozUZmDXQyP-LKS-prE-0DMz-dLUsu7FLE'
print('HAS_GS:', sheets.HAS_GS)
try:
    df = sheets.read_sheet(sid, sheet_name='pilot_roster')
    print('pilot_roster read:', df is not None, 'rows=', None if df is None else len(df))
except Exception as e:
    print('read error:', e)
