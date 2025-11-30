#!/usr/bin/env python3
"""
Verification script to show User_Pays vs Stash_Price for different countries.
This helps verify that prices are accurate based on Stash guidelines.
"""

import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cloud-function'))
import tax_calculator

SHEET_ID = "1bTCv5RrWPCqw75eARBbE-IFsH5_lP8-UKho3QhAXkf4"
KEY_FILE = os.path.join(os.path.dirname(__file__), '..', 'service-account-key.json')
if not os.path.exists(KEY_FILE):
    # Try absolute path
    KEY_FILE = os.path.expanduser("~/currency-convertor/service-account-key.json")

def get_sample_prices():
    """Get sample prices from Google Sheet for verification"""
    if not os.path.exists(KEY_FILE):
        print(f"Error: {KEY_FILE} not found")
        return []
    
    creds = service_account.Credentials.from_service_account_file(
        KEY_FILE,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    
    service = build('sheets', 'v4', credentials=creds)
    sheets = service.spreadsheets()
    
    sheet_name = "Price Matrix"
    range_name = f"{sheet_name}!A:O"  # All columns
    
    try:
        result = sheets.values().get(
            spreadsheetId=SHEET_ID,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        if len(values) < 2:
            return []
        
        # Headers: Country, Country_Name, Currency, Price_Tier, AppleStoreSku, GooglePlaySku,
        #          Local_Price, User_Pays, Stash_Price, VAT_Rate, VAT_Amount, Gross_USD, Stash_Fee_USD, Net_USD, Net_vs_Apple
        samples = []
        
        # Get samples for key countries
        target_countries = ['US', 'CA', 'BR', 'DE', 'GB', 'FR', 'JP', 'AU']
        
        for row in values[1:]:  # Skip header
            if len(row) < 9:  # Need at least Stash_Price
                continue
            
            country = row[0].strip() if len(row) > 0 else ''
            if country in target_countries:
                try:
                    country_name = row[1].strip() if len(row) > 1 else ''
                    currency = row[2].strip() if len(row) > 2 else ''
                    price_tier = float(row[3]) if len(row) > 3 and row[3] else 0
                    local_price = float(row[6]) if len(row) > 6 and row[6] else 0
                    user_pays = float(row[7]) if len(row) > 7 and row[7] else 0
                    stash_price = float(row[8]) if len(row) > 8 and row[8] else 0
                    vat_rate = float(row[9]) if len(row) > 9 and row[9] else 0
                    vat_amount = float(row[10]) if len(row) > 10 and row[10] else 0
                    
                    if user_pays > 0:  # Valid price
                        samples.append({
                            'country': country,
                            'country_name': country_name,
                            'currency': currency,
                            'price_tier': price_tier,
                            'local_price': local_price,
                            'user_pays': user_pays,
                            'stash_price': stash_price,
                            'vat_rate': vat_rate,
                            'vat_amount': vat_amount
                        })
                        # Only need one sample per country
                        if len([s for s in samples if s['country'] == country]) >= 1:
                            target_countries.remove(country)
                            if not target_countries:
                                break
                except (ValueError, IndexError):
                    continue
        
        return samples
    except Exception as e:
        print(f"Error reading from sheet: {e}")
        return []


def verify_stash_price(user_pays: float, country: str, stash_price: float) -> tuple[bool, str]:
    """Verify that Stash_Price is calculated correctly"""
    expected_stash = tax_calculator.get_stash_price(user_pays, country)
    
    # Allow small rounding differences
    if abs(expected_stash - stash_price) < 0.01:
        return True, "✓ Correct"
    else:
        return False, f"✗ Expected {expected_stash:.2f}, got {stash_price:.2f}"


def main():
    print("=" * 80)
    print("STASH PRICE VERIFICATION")
    print("=" * 80)
    print()
    print("This shows what the user pays vs what we send to Stash")
    print("Based on Stash guidelines:")
    print("  - US, Canada, Brazil: Stash adds tax on top (pre-tax pricing)")
    print("  - Europe: Prices are VAT inclusive (send price with VAT included)")
    print()
    print("=" * 80)
    print()
    
    samples = get_sample_prices()
    
    if not samples:
        print("No samples found. Running theoretical test instead...")
        print()
        # Run theoretical test
        test_cases = [
            ('US', 4.99, 'USD'),
            ('CA', 5.99, 'CAD'),
            ('BR', 10.00, 'BRL'),
            ('DE', 4.99, 'EUR'),
            ('GB', 5.99, 'GBP'),
            ('FR', 6.99, 'EUR'),
        ]
        
        for country, user_pays, currency in test_cases:
            stash_price = tax_calculator.get_stash_price(user_pays, country)
            is_pre_tax = country in tax_calculator.STASH_PRE_TAX_COUNTRIES
            vat_rate = tax_calculator.get_tax_rate(country)
            is_vat_inclusive = tax_calculator.is_vat_inclusive(country)
            
            print(f"{country} - {currency}")
            print(f"  User_Pays: {user_pays:.2f} {currency}")
            if is_vat_inclusive:
                print(f"    → Includes {vat_rate*100:.0f}% VAT")
            else:
                print(f"    → No VAT (pre-tax)")
            print(f"  Stash_Price: {stash_price:.2f} {currency}")
            if is_pre_tax:
                if country == 'BR':
                    print(f"    → Pre-tax (VAT removed: {user_pays:.2f} / 1.17 = {stash_price:.2f})")
                else:
                    print(f"    → Pre-tax (Stash adds tax on top)")
            else:
                print(f"    → VAT-inclusive (Stash uses as-is)")
            print()
    else:
        # Show real samples
        for sample in samples:
            country = sample['country']
            country_name = sample['country_name']
            currency = sample['currency']
            price_tier = sample['price_tier']
            local_price = sample['local_price']
            user_pays = sample['user_pays']
            stash_price = sample['stash_price']
            vat_rate = sample['vat_rate']
            vat_amount = sample['vat_amount']
            
            is_pre_tax = country in tax_calculator.STASH_PRE_TAX_COUNTRIES
            is_vat_inclusive = tax_calculator.is_vat_inclusive(country)
            
            # Verify
            is_correct, message = verify_stash_price(user_pays, country, stash_price)
            
            print(f"{country} - {country_name} ({currency})")
            print(f"  Price Tier: ${price_tier:.2f} USD")
            print(f"  Local_Price (raw conversion): {local_price:.2f} {currency}")
            print(f"  User_Pays: {user_pays:.2f} {currency}")
            if is_vat_inclusive:
                print(f"    → Includes {vat_rate:.1f}% VAT ({vat_amount:.2f} {currency})")
            else:
                print(f"    → No VAT (pre-tax)")
            print(f"  Stash_Price: {stash_price:.2f} {currency} {message}")
            if is_pre_tax:
                if country == 'BR':
                    expected = user_pays / (1 + vat_rate/100)
                    print(f"    → Pre-tax (VAT removed: {user_pays:.2f} / (1 + {vat_rate/100:.2f}) = {expected:.2f})")
                else:
                    print(f"    → Pre-tax (Stash adds tax on top)")
            else:
                print(f"    → VAT-inclusive (Stash uses as-is)")
            print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Stash Guidelines:")
    print("  1. US, Canada, Brazil → Send PRE-TAX price (Stash adds tax)")
    print("     - US/CA: User_Pays is already pre-tax → Stash_Price = User_Pays")
    print("     - BR: User_Pays includes VAT → Stash_Price = User_Pays / 1.17")
    print()
    print("  2. Europe → Send VAT-INCLUSIVE price (Stash uses as-is)")
    print("     - User_Pays includes VAT → Stash_Price = User_Pays")
    print()
    print("All prices are calculated based on the latest exchange rates from")
    print("the Exchange Rates Log sheet.")


if __name__ == '__main__':
    main()

