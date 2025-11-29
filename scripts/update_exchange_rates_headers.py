#!/usr/bin/env python3
"""
Script to update Exchange Rates Log sheet headers to include Country column
"""

import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID = "1bTCv5RrWPCqw75eARBbE-IFsH5_lP8-UKho3QhAXkf4"
KEY_FILE = "service-account-key.json"

if not os.path.exists(KEY_FILE):
    print(f"Error: {KEY_FILE} not found")
    sys.exit(1)

creds = service_account.Credentials.from_service_account_file(
    KEY_FILE,
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

service = build('sheets', 'v4', credentials=creds)
sheets = service.spreadsheets()

sheet_name = "Exchange Rates Log"

print(f"Updating headers in '{sheet_name}' sheet...")

# Update header row
headers = ['Date', 'Currency', 'Country', 'Rate', 'Source']
range_name = f"{sheet_name}!A1:E1"
body = {'values': [headers]}

try:
    sheets.values().update(
        spreadsheetId=SHEET_ID,
        range=range_name,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    print(f"✓ Headers updated successfully!")
    print(f"  New headers: {', '.join(headers)}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

