"""
Cloud Function entry point for currency conversion system.
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, Any

import exchange_rates
import price_converter
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
        
        # Get country-currency mapping
        country_currency_map = get_country_currency_map()
        
        # Process all SKUs
        price_data = converter.process_all_skus(country_currency_map)
        
        if not price_data:
            logger.warning("No price data generated")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No price data generated', 'count': 0})
            }
        
        # Write to Google Sheets
        sheets.write_price_matrix(price_data)
        
        # Log exchange rates - use the date from the API response
        exchange_rates_dict, api_date = exchange_client.fetch_rates()
        sheets.log_exchange_rates(exchange_rates_dict, api_date)
        
        logger.info(f"Successfully processed {len(price_data)} price combinations")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Currency conversion completed successfully',
                'count': len(price_data),
                'date': api_date
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

