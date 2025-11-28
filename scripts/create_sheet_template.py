#!/usr/bin/env python3
"""
Script to help create the Google Sheet template.
This generates a CSV file that can be imported into Google Sheets.
"""

import csv
import sys

# Unique SKUs extracted from the provided data
SKUS = [
    ("com.peerplay.mergecruise.credits99", "com.peerplay.mergecruise.credits99", "0.99"),
    ("com.peerplay.mergecruise.credits199", "com.peerplay.mergecruise.credits199", "1.99"),
    ("com.peerplay.mergecruise.credits299", "com.peerplay.mergecruise.credits299", "2.99"),
    ("com.peerplay.mergecruise.credits399", "com.peerplay.mergecruise.credits399", "3.99"),
    ("com.peerplay.mergecruise.credits499", "com.peerplay.mergecruise.credits499", "4.99"),
    ("com.peerplay.mergecruise.credits599", "com.peerplay.mergecruise.credits599", "5.99"),
    ("com.peerplay.mergecruise.credits699", "com.peerplay.mergecruise.credits699", "6.99"),
    ("com.peerplay.mergecruise.credits799", "com.peerplay.mergecruise.credits799", "7.99"),
    ("com.peerplay.mergecruise.credits899", "com.peerplay.mergecruise.credits899", "8.99"),
    ("com.peerplay.mergecruise.credits999", "com.peerplay.mergecruise.credits999", "9.99"),
    ("com.peerplay.mergecruise.credits1099", "com.peerplay.mergecruise.credits1099", "10.99"),
    ("com.peerplay.mergecruise.credits1199", "com.peerplay.mergecruise.credits1199", "11.99"),
    ("com.peerplay.mergecruise.credits1299", "com.peerplay.mergecruise.credits1299", "12.99"),
    ("com.peerplay.mergecruise.credits1399", "com.peerplay.mergecruise.credits1399", "13.99"),
    ("com.peerplay.mergecruise.credits1499", "com.peerplay.mergecruise.credits1499", "14.99"),
    ("com.peerplay.mergecruise.credits1599", "com.peerplay.mergecruise.credits1599", "15.99"),
    ("com.peerplay.mergecruise.credits1699", "com.peerplay.mergecruise.credits1699", "16.99"),
    ("com.peerplay.mergecruise.credits1799", "com.peerplay.mergecruise.credits1799", "17.99"),
    ("com.peerplay.mergecruise.credits1899", "com.peerplay.mergecruise.credits1899", "18.99"),
    ("com.peerplay.mergecruise.credits1999", "com.peerplay.mergecruise.credits1999", "19.99"),
    ("com.peerplay.mergecruise.credits2099", "com.peerplay.mergecruise.credits2099", "20.99"),
    ("com.peerplay.mergecruise.credits2199", "com.peerplay.mergecruise.credits2199", "21.99"),
    ("com.peerplay.mergecruise.credits2299", "com.peerplay.mergecruise.credits2299", "22.99"),
    ("com.peerplay.mergecruise.credits2399", "com.peerplay.mergecruise.credits2399", "23.99"),
    ("com.peerplay.mergecruise.credits2499", "com.peerplay.mergecruise.credits2499", "24.99"),
    ("com.peerplay.mergecruise.credits2599", "com.peerplay.mergecruise.credits2599", "25.99"),
    ("com.peerplay.mergecruise.credits2699", "com.peerplay.mergecruise.credits2699", "26.99"),
    ("com.peerplay.mergecruise.credits2799", "com.peerplay.mergecruise.credits2799", "27.99"),
    ("com.peerplay.mergecruise.credits2899", "com.peerplay.mergecruise.credits2899", "28.99"),
    ("com.peerplay.mergecruise.credits2999", "com.peerplay.mergecruise.credits2999", "29.99"),
    ("com.peerplay.mergecruise.credits3099", "com.peerplay.mergecruise.credits3099", "30.99"),
    ("com.peerplay.mergecruise.credits3199", "com.peerplay.mergecruise.credits3199", "31.99"),
    ("com.peerplay.mergecruise.credits3299", "com.peerplay.mergecruise.credits3299", "32.99"),
    ("com.peerplay.mergecruise.credits3399", "com.peerplay.mergecruise.credits3399", "33.99"),
    ("com.peerplay.mergecruise.credits3499", "com.peerplay.mergecruise.credits3499", "34.99"),
    ("com.peerplay.mergecruise.credits3599", "com.peerplay.mergecruise.credits3599", "35.99"),
    ("com.peerplay.mergecruise.credits3699", "com.peerplay.mergecruise.credits3699", "36.99"),
    ("com.peerplay.mergecruise.credits3799", "com.peerplay.mergecruise.credits3799", "37.99"),
    ("com.peerplay.mergecruise.credits3899", "com.peerplay.mergecruise.credits3899", "38.99"),
    ("com.peerplay.mergecruise.credits3999", "com.peerplay.mergecruise.credits3999", "39.99"),
    ("com.peerplay.mergecruise.credits4099", "com.peerplay.mergecruise.credits4099", "40.99"),
    ("com.peerplay.mergecruise.credits4199", "com.peerplay.mergecruise.credits4199", "41.99"),
    ("com.peerplay.mergecruise.credits4299", "com.peerplay.mergecruise.credits4299", "42.99"),
    ("com.peerplay.mergecruise.credits4399", "com.peerplay.mergecruise.credits4399", "43.99"),
    ("com.peerplay.mergecruise.credits4499", "com.peerplay.mergecruise.credits4499", "44.99"),
    ("com.peerplay.mergecruise.credits4599", "com.peerplay.mergecruise.credits4599", "45.99"),
    ("com.peerplay.mergecruise.credits4699", "com.peerplay.mergecruise.credits4699", "46.99"),
    ("com.peerplay.mergecruise.credits4799", "com.peerplay.mergecruise.credits4799", "47.99"),
    ("com.peerplay.mergecruise.credits4899", "com.peerplay.mergecruise.credits4899", "48.99"),
    ("com.peerplay.mergecruise.credits4999", "com.peerplay.mergecruise.credits4999", "49.99"),
    ("com.peerplay.mergecruise.credits5499", "com.peerplay.mergecruise.credits5499", "54.99"),
    ("com.peerplay.mergecruise.credits5999", "com.peerplay.mergecruise.credits5999", "59.99"),
    ("com.peerplay.mergecruise.credits6499", "com.peerplay.mergecruise.credits6499", "64.99"),
    ("com.peerplay.mergecruise.credits6999", "com.peerplay.mergecruise.credits6999", "69.99"),
    ("com.peerplay.mergecruise.credits7499", "com.peerplay.mergecruise.credits7499", "74.99"),
    ("com.peerplay.mergecruise.credits7999", "com.peerplay.mergecruise.credits7999", "79.99"),
    ("com.peerplay.mergecruise.credits8499", "com.peerplay.mergecruise.credits8499", "84.99"),
    ("com.peerplay.mergecruise.credits8999", "com.peerplay.mergecruise.credits8999", "89.99"),
    ("com.peerplay.mergecruise.credits9499", "com.peerplay.mergecruise.credits9499", "94.99"),
    ("com.peerplay.mergecruise.credits9999", "com.peerplay.mergecruise.credits9999", "99.99"),
    ("com.peerplay.mergecruise.credits200000", "com.peerplay.mergecruise.credits200000", "199.99"),
]

def create_config_csv(filename="config_sheet.csv"):
    """Create a CSV file for the Config sheet"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # Header
        writer.writerow(['AppleStoreSku', 'GooglePlaySku', 'Cost'])
        # Data
        for apple_sku, google_sku, cost in SKUS:
            writer.writerow([apple_sku, google_sku, cost])
    print(f"✓ Created {filename}")
    print(f"  Import this into the 'Config' sheet in your Google Sheet")

def create_price_matrix_headers(filename="price_matrix_headers.csv"):
    """Create headers for Price Matrix sheet"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Country', 'Currency', 'AppleStoreSku', 'GooglePlaySku', 'Local_Price',
            'VAT_Rate', 'VAT_Amount', 'Gross_USD', 'Stash_Fee_USD', 'Net_USD', 'Net_vs_Apple'
        ])
    print(f"✓ Created {filename}")
    print(f"  Import this into the 'Price Matrix' sheet in your Google Sheet")

def create_exchange_rates_headers(filename="exchange_rates_headers.csv"):
    """Create headers for Exchange Rates Log sheet"""
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Currency', 'Rate', 'Source'])
    print(f"✓ Created {filename}")
    print(f"  Import this into the 'Exchange Rates Log' sheet in your Google Sheet")

if __name__ == '__main__':
    print("Creating Google Sheets template files...")
    print("")
    create_config_csv()
    create_price_matrix_headers()
    create_exchange_rates_headers()
    print("")
    print("Next steps:")
    print("1. Create a new Google Sheet")
    print("2. Create 3 sheets: 'Config', 'Price Matrix', 'Exchange Rates Log'")
    print("3. Import the CSV files into their respective sheets")
    print("4. Share the sheet with your service account email")
    print("5. Copy the Sheet ID from the URL")

