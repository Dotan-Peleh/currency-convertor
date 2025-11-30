"""
Cloud Function entry point for currency conversion system.
"""

import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any

import exchange_rates
import price_converter
import price_stability
import sheets_client
import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Country to currency mapping (simplified - in production, use a comprehensive mapping)
COUNTRY_CURRENCY_MAP = {
    'US': 'USD', 'GB': 'GBP', 'DE': 'EUR', 'FR': 'EUR', 'IT': 'EUR', 'ES': 'EUR',
    'NL': 'EUR', 'BE': 'EUR', 'AT': 'EUR', 'CH': 'CHF', 'SE': 'SEK', 'NO': 'NOK',
    'DK': 'DKK', 'PL': 'PLN', 'CZ': 'CZK', 'IE': 'EUR', 'PT': 'EUR', 'GR': 'EUR',
    'FI': 'EUR', 'HU': 'HUF', 'RO': 'RON', 'SK': 'EUR', 'BG': 'BGN', 'HR': 'HRK',
    'JP': 'JPY', 'CN': 'CNY', 'KR': 'KRW', 'IN': 'INR', 'AU': 'AUD', 'NZ': 'NZD',
    'CA': 'CAD', 'MX': 'MXN', 'BR': 'BRL', 'AR': 'ARS', 'CL': 'CLP', 'CO': 'COP',
    'PE': 'PEN', 'ZA': 'ZAR', 'AE': 'AED', 'SA': 'SAR', 'IL': 'ILS', 'TR': 'TRY',
    'RU': 'RUB', 'SG': 'SGD', 'HK': 'HKD', 'TW': 'TWD', 'TH': 'THB', 'MY': 'MYR',
    'ID': 'IDR', 'PH': 'PHP', 'VN': 'VND', 'QA': 'QAR', 'KW': 'KWD', 'BH': 'BHD',
    'OM': 'OMR', 'EG': 'EGP', 'NG': 'NGN', 'KE': 'KES', 'GH': 'GHS', 'MA': 'MAD',
    # Add more as needed
}


def get_country_currency_map() -> Dict[str, str]:
    """
    Get mapping of country codes to currency codes.
    Can be extended or loaded from external source.
    """
    return COUNTRY_CURRENCY_MAP


def currency_conversion_handler(request):
    """
    Cloud Function entry point.
    
    Args:
        request: Flask request object (for HTTP triggers)
        
    Returns:
        Response dictionary
    """
    try:
        logger.info("Starting currency conversion process")
        
        # Initialize clients
        exchange_client = exchange_rates.ExchangeRateClient()
        sheets = sheets_client.SheetsClient()
        converter = price_converter.PriceConverter(sheets, exchange_client)
        
        # Check for missed days - ensure we haven't skipped any dates
        today = datetime.utcnow().strftime('%Y-%m-%d')
        last_logged_date = sheets.get_last_logged_date()
        
        if last_logged_date:
            try:
                last_date_obj = datetime.strptime(last_logged_date, '%Y-%m-%d')
                today_obj = datetime.strptime(today, '%Y-%m-%d')
                days_missing = (today_obj - last_date_obj).days
                
                if days_missing > 1:
                    logger.warning(
                        f"Gap detected: Last logged date was {last_logged_date}, today is {today}. "
                        f"Missing {days_missing - 1} day(s) of exchange rates. "
                        f"This may indicate the cron job failed or was not running."
                    )
                elif days_missing == 1:
                    logger.info(f"Last logged date was {last_logged_date}, today is {today}. This is expected.")
            except ValueError as e:
                logger.warning(f"Could not parse last logged date '{last_logged_date}': {e}")
        
        # Check if today's rates are already logged (will be overwritten)
        if sheets.has_exchange_rates_for_date(today):
            logger.info(f"Exchange rates for {today} already exist. Will overwrite with fresh data.")
        
        # Get country-currency mapping
        country_currency_map = get_country_currency_map()
        
        # Read existing prices for stability check
        existing_prices = sheets.read_price_matrix()
        
        # Try to read exchange rates from sheet first (latest rates from Exchange Rates Log)
        # This ensures we use the most recent rates that were logged
        exchange_rates_from_sheet = sheets.read_exchange_rates_from_sheet()
        
        if exchange_rates_from_sheet:
            logger.info(f"Using {len(exchange_rates_from_sheet)} exchange rates from Exchange Rates Log sheet")
            # Use rates from sheet for calculations
            exchange_rates_dict = exchange_rates_from_sheet
        else:
            logger.info("No rates found in sheet, fetching from API")
            # Fetch from API if sheet is empty
            exchange_rates_dict, _ = exchange_client.fetch_rates()
        
        # Process all SKUs with the exchange rates (from sheet or API)
        price_data = converter.process_all_skus_with_rates(country_currency_map, exchange_rates_dict)
        
        if not price_data:
            logger.warning("No price data generated")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No price data generated', 'count': 0})
            }
        
        # Apply price stability rules (prevent frequent changes)
        stable_price_data = []
        prices_kept_stable = 0
        prices_updated = 0
        
        for price_row in price_data:
            stable_row, was_updated = price_stability.apply_price_stability(price_row, existing_prices)
            stable_price_data.append(stable_row)
            
            if was_updated:
                prices_updated += 1
            else:
                prices_kept_stable += 1
        
        logger.info(f"Price stability: {prices_kept_stable} prices kept stable, {prices_updated} prices updated")
        
        # Write to Google Sheets
        sheets.write_price_matrix(stable_price_data)
        
        # Log exchange rates - use the date from the API response
        # fetch_rates will retry if API returns stale data
        exchange_rates_dict, api_date = exchange_client.fetch_rates(max_retries=3, retry_delay=300)
        sheets.log_exchange_rates(exchange_rates_dict, api_date)
        
        # Final validation - ensure we logged today's rates (or at least recent rates)
        if api_date != today:
            logger.warning(
                f"Logged rates for {api_date} but today is {today}. "
                f"API may not have updated yet. Consider checking manually later."
            )
        
        logger.info(f"Successfully processed {len(price_data)} price combinations")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Currency conversion completed successfully',
                'count': len(price_data),
                'date': api_date,
                'expected_date': today,
                'date_match': api_date == today
            })
        }
        
    except Exception as e:
        logger.error(f"Error in currency conversion: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Currency conversion failed'
            })
        }


# For Cloud Functions HTTP trigger
def main(request):
    """Main entry point for Cloud Function"""
    return currency_conversion_handler(request)


# For local testing
if __name__ == '__main__':
    class MockRequest:
        pass
    
    result = currency_conversion_handler(MockRequest())
    print(json.dumps(result, indent=2))

