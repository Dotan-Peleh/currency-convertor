#!/usr/bin/env python3
"""
Script to verify Google Sheet structure
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

try:
    # Get sheet metadata
    spreadsheet = sheets.get(spreadsheetId=SHEET_ID).execute()
    
    print("Sheet Title:", spreadsheet.get('properties', {}).get('title'))
    print("\nTabs/Sheets found:")
    print("-" * 50)
    
    for sheet in spreadsheet.get('sheets', []):
        title = sheet.get('properties', {}).get('title')
        sheet_id = sheet.get('properties', {}).get('sheetId')
        print(f"  • {title} (ID: {sheet_id})")
    
    print("\n" + "-" * 50)
    print("\nRequired tabs:")
    required = ['Config', 'Price Matrix', 'Exchange Rates Log']
    found_tabs = [s.get('properties', {}).get('title') for s in spreadsheet.get('sheets', [])]
    
    for req in required:
        if req in found_tabs:
            print(f"  ✓ {req}")
        else:
            print(f"  ✗ {req} - MISSING!")
    
    # Try to read Config sheet
    print("\n" + "=" * 50)
    print("Testing Config sheet read...")
    try:
        result = sheets.values().get(
            spreadsheetId=SHEET_ID,
            range="Config!A:C"
        ).execute()
        values = result.get('values', [])
        print(f"✓ Successfully read Config sheet")
        print(f"  Found {len(values)} rows")
        if values:
            print(f"  First row: {values[0]}")
            if len(values) > 1:
                print(f"  Second row: {values[1]}")
    except Exception as e:
        print(f"✗ Error reading Config sheet: {e}")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

