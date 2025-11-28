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
                'Country', 'Country_Name', 'Currency', 'AppleStoreSku', 'GooglePlaySku', 
                'Local_Price', 'User_Pays', 'VAT_Rate', 'VAT_Amount', 
                'Gross_USD', 'Stash_Fee_USD', 'Net_USD', 'Net_vs_Apple'
            ]
            
            # Prepare data rows
            rows = [headers]
            for row_data in price_data:
                rows.append([
                    row_data.get('Country', ''),
                    row_data.get('Country_Name', ''),
                    row_data.get('Currency', ''),
                    row_data.get('AppleStoreSku', ''),
                    row_data.get('GooglePlaySku', ''),
                    row_data.get('Local_Price', 0),
                    row_data.get('User_Pays', 0),  # What user will pay
                    row_data.get('VAT_Rate', 0),
                    row_data.get('VAT_Amount', 0),
                    row_data.get('Gross_USD', 0),
                    row_data.get('Stash_Fee_USD', 0),
                    row_data.get('Net_USD', 0),  # What I will be left with
                    row_data.get('Net_vs_Apple', '')
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
            
            logger.info(f"Wrote {len(price_data)} rows to price matrix")
            
        except HttpError as e:
            logger.error(f"Error writing price matrix: {e}")
            raise
    
    def log_exchange_rates(self, rates: Dict[str, float], date: str):
        """
        Log exchange rates to the Exchange Rates Log sheet.
        
        Args:
            rates: Dictionary mapping currency codes to rates
            date: Date string (YYYY-MM-DD)
        """
        try:
            sheet_name = config.GOOGLE_SHEETS_EXCHANGE_RATES_SHEET
            
            # Prepare data rows
            rows = []
            for currency, rate in sorted(rates.items()):
                rows.append([date, currency, rate, 'exchangerate-api.com'])
            
            # Append to sheet
            range_name = f"{sheet_name}!A:D"
            body = {
                'values': rows
            }
            
            self.sheets.values().append(
                spreadsheetId=self.sheets_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.info(f"Logged {len(rates)} exchange rates for {date}")
            
        except HttpError as e:
            logger.error(f"Error logging exchange rates: {e}")
            # Don't raise - this is not critical

