#!/usr/bin/env python3
"""
Script to set up Google Sheet with required tabs and data
"""

import os
import sys
import csv
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

# Read CSV files
def read_csv(filename):
    data = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                data.append(row)
    return data

print("Setting up Google Sheet...")
print("=" * 50)

# Get current sheet structure
spreadsheet = sheets.get(spreadsheetId=SHEET_ID).execute()
existing_sheets = {s.get('properties', {}).get('title'): s.get('properties', {}).get('sheetId') 
                   for s in spreadsheet.get('sheets', [])}

print(f"\nCurrent tabs: {list(existing_sheets.keys())}")

# Create required sheets if they don't exist
required_sheets = {
    'Config': read_csv('config_sheet.csv'),
    'Price Matrix': read_csv('price_matrix_headers.csv'),
    'Exchange Rates Log': read_csv('exchange_rates_headers.csv')
}

requests = []
for sheet_name, data in required_sheets.items():
    if sheet_name not in existing_sheets:
        print(f"\nCreating tab: {sheet_name}")
        requests.append({
            'addSheet': {
                'properties': {
                    'title': sheet_name
                }
            }
        })

if requests:
    print("\nAdding new tabs...")
    body = {'requests': requests}
    sheets.batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
    print("✓ Tabs created")
else:
    print("\n✓ All required tabs already exist")

# Wait a moment for sheets to be created
import time
time.sleep(2)

# Populate sheets with data
print("\nPopulating sheets with data...")
for sheet_name, data in required_sheets.items():
    if data:
        print(f"\nWriting data to '{sheet_name}'...")
        range_name = f"{sheet_name}!A1"
        body = {'values': data}
        
        # Clear existing data first
        try:
            sheets.values().clear(
                spreadsheetId=SHEET_ID,
                range=f"{sheet_name}!A:Z"
            ).execute()
        except:
            pass
        
        # Write new data
        sheets.values().update(
            spreadsheetId=SHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        print(f"  ✓ Wrote {len(data)} rows")

# Optionally delete Sheet1 if it's empty
if 'Sheet1' in existing_sheets:
    print("\nNote: 'Sheet1' tab still exists. You can delete it manually if not needed.")

print("\n" + "=" * 50)
print("✓ Sheet setup complete!")
print(f"\nView your sheet:")
print(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")

