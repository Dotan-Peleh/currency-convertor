"""
Google Sheets API client for reading config and writing results.
"""

import logging
import os
from typing import List, Dict, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import config
import currency_countries

logger = logging.getLogger(__name__)


class SheetsClient:
    """Client for interacting with Google Sheets"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the Google Sheets client.
        
        Args:
            credentials_path: Path to service account JSON credentials file
        """
        self.sheets_id = os.environ.get('GOOGLE_SHEETS_ID') or config.GOOGLE_SHEETS_ID
        if not self.sheets_id:
            raise ValueError("GOOGLE_SHEETS_ID must be set in environment or config")
        
        # Load credentials
        if credentials_path:
            creds = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
        else:
            # Try to load from environment variable or default location
            creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if creds_path and os.path.exists(creds_path):
                creds = service_account.Credentials.from_service_account_file(
                    creds_path,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
            else:
                # Try Application Default Credentials (for Cloud Functions)
                try:
                    from google.auth import default
                    creds, _ = default(scopes=['https://www.googleapis.com/auth/spreadsheets'])
                except Exception as e:
                    raise ValueError(f"Google credentials not found. Set GOOGLE_APPLICATION_CREDENTIALS or use Application Default Credentials. Error: {e}")
        
        self.service = build('sheets', 'v4', credentials=creds)
        self.sheets = self.service.spreadsheets()
        
    def read_config_sheet(self) -> List[Dict[str, str]]:
        """
        Read the Config sheet and return SKU data.
        
        Returns:
            List of dictionaries with AppleStoreSku, GooglePlaySku, Cost
        """
        try:
            sheet_name = config.GOOGLE_SHEETS_CONFIG_SHEET
            range_name = f"{sheet_name}!A:C"
            
            result = self.sheets.values().get(
                spreadsheetId=self.sheets_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not values:
                logger.warning("Config sheet is empty")
                return []
            
            # Skip header row
            headers = values[0] if values else []
            skus = []
            
            for row in values[1:]:
                if len(row) < 3:
                    continue
                    
                # Filter to only process SKUs matching the pattern
                apple_sku = row[0].strip()
                if not apple_sku.startswith('com.peerplay.mergecruise.credit'):
                    continue
                
                skus.append({
                    'AppleStoreSku': apple_sku,
                    'GooglePlaySku': row[1].strip() if len(row) > 1 else apple_sku,
                    'Cost': row[2].strip() if len(row) > 2 else '0.00'
                })
            
            logger.info(f"Read {len(skus)} SKUs from config sheet")
            return skus
            
        except HttpError as e:
            logger.error(f"Error reading config sheet: {e}")
            raise
    
    def read_price_matrix(self) -> Dict[str, Dict[str, any]]:
        """
        Read existing price data from the Price Matrix sheet.
        Used for price stability - to compare with new prices and keep stable rows.
        
        Returns:
            Dictionary mapping (country:sku) -> full price data dictionary
        """
        try:
            sheet_name = config.GOOGLE_SHEETS_PRICE_MATRIX_SHEET
            # Read all columns
            range_name = f"{sheet_name}!A:N"
            
            result = self.sheets.values().get(
                spreadsheetId=self.sheets_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:  # No data rows
                logger.info("No existing price data found - first run")
                return {}
            
            # Headers: Country, Country_Name, Currency, Price_Tier, AppleStoreSku, GooglePlaySku, Local_Price, User_Pays, VAT_Rate, VAT_Amount, Gross_USD, Stash_Fee_USD, Net_USD, Net_vs_Apple
            existing_data = {}
            
            for row in values[1:]:  # Skip header
                if len(row) < 8:  # Need at least User_Pays column
                    continue
                
                try:
                    country = row[0].strip() if len(row) > 0 else ''
                    sku = row[4].strip() if len(row) > 4 else ''  # AppleStoreSku (index 4)
                    user_pays_str = row[7].strip() if len(row) > 7 else '0'  # User_Pays (index 7)
                    
                    if country and sku and user_pays_str:
                        try:
                            user_pays = float(user_pays_str) if user_pays_str.replace('.', '').replace('-', '').replace('+', '').isdigit() else 0.0
                            if user_pays > 0:  # Only store valid prices
                                lookup_key = f"{country}:{sku}"
                                # Store just the User_Pays for comparison (we'll keep entire row if stable)
                                existing_data[lookup_key] = user_pays
                        except (ValueError, AttributeError):
                            continue
                except (IndexError, AttributeError) as e:
                    logger.debug(f"Error parsing row for price stability: {e}")
                    continue
            
            logger.info(f"Read {len(existing_data)} existing prices for stability check")
            return existing_data
            
        except Exception as e:
            logger.warning(f"Could not read existing prices for stability: {e}. Will update all prices.")
            return {}
    
    def write_price_matrix(self, price_data: List[Dict[str, any]]):
        """
        Write price matrix data to the Price Matrix sheet.
        
        Args:
            price_data: List of dictionaries with price information
        """
        try:
            sheet_name = config.GOOGLE_SHEETS_PRICE_MATRIX_SHEET
            
            # Prepare headers
            headers = [
                'Country', 'Country_Name', 'Currency', 'Price_Tier', 'AppleStoreSku', 'GooglePlaySku', 
                'Local_Price', 'User_Pays', 'VAT_Rate', 'VAT_Amount', 
                'Gross_USD', 'Stash_Fee_USD', 'Net_USD', 'Net_vs_Apple'
            ]
            
            # Prepare data rows
            rows = [headers]
            for row_data in price_data:
                # Format Net_vs_Apple as text to preserve percentage format
                net_vs_apple = row_data.get('Net_vs_Apple', '')
                # If it's already a string with %, keep it; otherwise format it
                if isinstance(net_vs_apple, (int, float)):
                    if net_vs_apple > 0:
                        net_vs_apple = f"+{net_vs_apple:.1f}%"
                    else:
                        net_vs_apple = f"{net_vs_apple:.1f}%"
                
                rows.append([
                    row_data.get('Country', ''),
                    row_data.get('Country_Name', ''),
                    row_data.get('Currency', ''),
                    row_data.get('Price_Tier', 0),  # USD base price tier (0.99, 1.99, etc.)
                    row_data.get('AppleStoreSku', ''),
                    row_data.get('GooglePlaySku', ''),
                    row_data.get('Local_Price', 0),  # Raw conversion: USD * exchange_rate
                    row_data.get('User_Pays', 0),  # What user will pay (including VAT) - this is the visibility price
                    row_data.get('VAT_Rate', 0),
                    row_data.get('VAT_Amount', 0),
                    row_data.get('Gross_USD', 0),
                    row_data.get('Stash_Fee_USD', 0),
                    row_data.get('Net_USD', 0),  # What I will be left with
                    net_vs_apple  # Format as text to preserve percentage
                ])
            
            # Clear existing data and write new data
            range_name = f"{sheet_name}!A1"
            body = {
                'values': rows
            }
            
            self.sheets.values().clear(
                spreadsheetId=self.sheets_id,
                range=f"{sheet_name}!A:Z"
            ).execute()
            
            self.sheets.values().update(
                spreadsheetId=self.sheets_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            # Set number formatting for currency columns (USD columns should be currency format)
            # After adding Price_Tier: Column K (index 10) = Gross_USD, Column L (index 11) = Stash_Fee_USD, Column M (index 12) = Net_USD
            # Also format Price_Tier (column D, index 3) as currency
            # Get the sheet ID first
            try:
                sheet_metadata = self.sheets.get(
                    spreadsheetId=self.sheets_id
                ).execute()
                sheet_id = None
                for sheet in sheet_metadata.get('sheets', []):
                    if sheet['properties']['title'] == sheet_name:
                        sheet_id = sheet['properties']['sheetId']
                        break
                
                if sheet_id is not None:
                    requests = []
                    
                    # Format Price_Tier (column D, index 3) as currency
                    requests.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': 1,  # Skip header row
                                'endRowIndex': len(price_data) + 1,
                                'startColumnIndex': 3,  # Column D (Price_Tier)
                                'endColumnIndex': 4
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'numberFormat': {
                                        'type': 'CURRENCY',
                                        'pattern': '"$"#,##0.00'
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat.numberFormat'
                        }
                    })
                    
                    # Format USD columns as currency (columns K, L, M = Gross_USD, Stash_Fee_USD, Net_USD)
                    # Column indices: K=10, L=11, M=12 (0-based)
                    
                    # Format Gross_USD (column K, index 10) as currency
                    requests.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': 1,  # Skip header row
                                'endRowIndex': len(price_data) + 1,
                                'startColumnIndex': 10,  # Column K (Gross_USD)
                                'endColumnIndex': 11
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'numberFormat': {
                                        'type': 'CURRENCY',
                                        'pattern': '"$"#,##0.00'
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat.numberFormat'
                        }
                    })
                    
                    # Format Stash_Fee_USD (column L, index 11) as currency
                    requests.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': 1,
                                'endRowIndex': len(price_data) + 1,
                                'startColumnIndex': 11,  # Column L (Stash_Fee_USD)
                                'endColumnIndex': 12
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'numberFormat': {
                                        'type': 'CURRENCY',
                                        'pattern': '"$"#,##0.00'
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat.numberFormat'
                        }
                    })
                    
                    # Format Net_USD (column M, index 12) as currency
                    requests.append({
                        'repeatCell': {
                            'range': {
                                'sheetId': sheet_id,
                                'startRowIndex': 1,
                                'endRowIndex': len(price_data) + 1,
                                'startColumnIndex': 12,  # Column M (Net_USD)
                                'endColumnIndex': 13
                            },
                            'cell': {
                                'userEnteredFormat': {
                                    'numberFormat': {
                                        'type': 'CURRENCY',
                                        'pattern': '"$"#,##0.00'
                                    }
                                }
                            },
                            'fields': 'userEnteredFormat.numberFormat'
                        }
                    })
                    
                    # Apply all formatting requests
                    if requests:
                        self.sheets.batchUpdate(
                            spreadsheetId=self.sheets_id,
                            body={'requests': requests}
                        ).execute()
                        logger.info(f"Applied currency formatting to Price_Tier and USD columns (D, K, L, M)")
            except Exception as e:
                logger.warning(f"Could not apply number formatting: {e}. Values are correct but may need manual formatting in Google Sheets.")
            
            logger.info(f"Wrote {len(price_data)} rows to price matrix")
            
        except HttpError as e:
            logger.error(f"Error writing price matrix: {e}")
            raise
    
    def has_exchange_rates_for_date(self, date: str) -> bool:
        """
        Check if exchange rates for a specific date are already logged.
        
        Args:
            date: Date string (YYYY-MM-DD)
            
        Returns:
            True if rates for this date exist, False otherwise
        """
        try:
            sheet_name = config.GOOGLE_SHEETS_EXCHANGE_RATES_SHEET
            # Read first column to check for the date
            range_name = f"{sheet_name}!A:A"
            result = self.sheets.values().get(
                spreadsheetId=self.sheets_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            # Skip header row (index 0) and check if date exists
            for row in values[1:]:
                if row and len(row) > 0 and row[0] == date:
                    return True
            return False
        except Exception as e:
            logger.warning(f"Error checking if date exists: {e}")
            # If we can't check, assume it doesn't exist to avoid skipping
            return False
    
    def get_last_logged_date(self) -> Optional[str]:
        """
        Get the most recent date for which exchange rates are logged.
        
        Returns:
            Date string (YYYY-MM-DD) of the last logged rates, or None if no rates exist
        """
        try:
            sheet_name = config.GOOGLE_SHEETS_EXCHANGE_RATES_SHEET
            # Read first column to get all dates
            range_name = f"{sheet_name}!A:A"
            result = self.sheets.values().get(
                spreadsheetId=self.sheets_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if len(values) < 2:  # Only header or empty
                return None
            
            # Get all dates (skip header)
            dates = []
            for row in values[1:]:
                if row and len(row) > 0:
                    dates.append(row[0])
            
            if not dates:
                return None
            
            # Return the most recent date (assuming dates are in chronological order)
            # If not sorted, we'd need to parse and compare, but typically they are appended chronologically
            return dates[-1]
        except Exception as e:
            logger.warning(f"Error getting last logged date: {e}")
            return None
    
    def log_exchange_rates(self, rates: Dict[str, float], date: str):
        """
        Log exchange rates to the Exchange Rates Log sheet.
        Always writes to the fixed range A1:E1661, replacing all data with the latest date and rates.
        
        Args:
            rates: Dictionary mapping currency codes to rates
            date: Date string (YYYY-MM-DD)
        """
        try:
            sheet_name = config.GOOGLE_SHEETS_EXCHANGE_RATES_SHEET
            
            # Prepare header row
            header = ['Date', 'Currency', 'Country', 'Rate', 'Source']
            
            # Prepare data rows with country names - all with the same date
            rows = [header]
            for currency, rate in sorted(rates.items()):
                country = currency_countries.get_country_for_currency(currency)
                rows.append([date, currency, country, rate, 'exchangerate-api.com'])
            
            # Clear the fixed range A1:E1661 first
            self.sheets.values().clear(
                spreadsheetId=self.sheets_id,
                range=f"{sheet_name}!A1:E1661"
            ).execute()
            
            # Write all data to the fixed range A1:E1661
            body = {
                'values': rows
            }
            
            self.sheets.values().update(
                spreadsheetId=self.sheets_id,
                range=f"{sheet_name}!A1:E1661",
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info(f"Updated exchange rates in range A1:E1661 with {len(rates)} rates for date {date}")
            
        except HttpError as e:
            logger.error(f"Error logging exchange rates: {e}")
            # Don't raise - this is not critical

