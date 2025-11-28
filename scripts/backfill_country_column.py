#!/usr/bin/env python3
"""
Script to backfill Country column in Exchange Rates Log for existing rows
"""

import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Add parent directory to path to import currency_countries
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cloud-function'))
import currency_countries

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

print(f"Reading data from '{sheet_name}' sheet...")

# Read all data
result = sheets.values().get(
    spreadsheetId=SHEET_ID,
    range=f"{sheet_name}!A:E"
).execute()

values = result.get('values', [])

if len(values) < 2:
    print("No data rows found")
    sys.exit(0)

print(f"Found {len(values) - 1} data rows (excluding header)")

# Process rows and add Country if missing
updated_rows = []
updated_count = 0

for i, row in enumerate(values):
    if i == 0:
        # Header row - keep as is
        updated_rows.append(['Date', 'Currency', 'Country', 'Rate', 'Source'])
        continue
    
    # Handle old format (4 columns) vs new format (5 columns)
    date = row[0] if len(row) > 0 else ''
    currency = row[1] if len(row) > 1 else ''
    
    # Check if this is old format (no Country column)
    # Old format: [Date, Currency, Rate, Source]
    # New format: [Date, Currency, Country, Rate, Source]
    if len(row) == 4:
        # Old format - need to insert Country
        rate = row[2] if len(row) > 2 else ''
        source = row[3] if len(row) > 3 else ''
        country = currency_countries.get_country_for_currency(currency)
        updated_count += 1
    elif len(row) == 5:
        # New format - Country might be empty
        country = row[2] if len(row) > 2 else ''
        rate = row[3] if len(row) > 3 else ''
        source = row[4] if len(row) > 4 else ''
        
        # If Country is empty, fill it
        if not country and currency:
            country = currency_countries.get_country_for_currency(currency)
            updated_count += 1
    else:
        # Unexpected format - try to parse
        country = row[2] if len(row) > 2 and row[2] else ''
        if not country and currency:
            country = currency_countries.get_country_for_currency(currency)
            updated_count += 1
        rate = row[3] if len(row) > 3 else ''
        source = row[4] if len(row) > 4 else ''
    
    updated_rows.append([date, currency, country, rate, source])

print(f"\nUpdating {updated_count} rows with Country data...")

# Write all rows back
range_name = f"{sheet_name}!A1:E{len(updated_rows)}"
body = {'values': updated_rows}

try:
    sheets.values().update(
        spreadsheetId=SHEET_ID,
        range=range_name,
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    print(f"✓ Successfully updated {updated_count} rows with Country data!")
    print(f"✓ Total rows in sheet: {len(updated_rows) - 1}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

