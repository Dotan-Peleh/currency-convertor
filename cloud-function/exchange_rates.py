"""
Exchange rate API client for fetching currency conversion rates.
"""

import requests
import logging
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import config

logger = logging.getLogger(__name__)


class ExchangeRateClient:
    """Client for fetching exchange rates from exchangerate-api.com"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the exchange rate client.
        
        Args:
            api_key: Optional API key (free tier doesn't require it)
        """
        self.base_url = config.EXCHANGE_RATE_API_BASE_URL
        self.api_key = api_key or config.EXCHANGE_RATE_API_KEY
        self.cache: Dict[str, Dict] = {}
        self.last_fetch_date: Optional[str] = None
        
    def fetch_rates(self, max_retries: int = 3, retry_delay: int = 300) -> Tuple[Dict[str, float], str]:
        """
        Fetch current exchange rates from USD to all currencies.
        Retries if API returns stale data (yesterday's rates) to ensure we get today's rates.
        
        Args:
            max_retries: Maximum number of retries if API returns stale data
            retry_delay: Delay in seconds between retries
            
        Returns:
            Tuple of (rates dictionary, date string)
            - rates: Dictionary mapping currency codes to exchange rates (USD to currency)
            - date: Date string (YYYY-MM-DD) from the API response
            
        Raises:
            requests.RequestException: If API request fails after all retries
        """
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        for attempt in range(max_retries):
            try:
                url = self.base_url
                if self.api_key:
                    url = f"{url}?api_key={self.api_key}"
                
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{max_retries} - waiting {retry_delay}s for API to update...")
                    time.sleep(retry_delay)
                
                logger.info(f"Fetching exchange rates from {url}")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                rates = data.get('rates', {})
                
                # Extract date from API response - this is the actual date of the rates
                api_date = data.get('date')
                if not api_date:
                    # Fallback to today if API doesn't provide date
                    api_date = today
                    logger.warning("API response did not include date field, using current UTC date")
                else:
                    # Ensure date is in YYYY-MM-DD format
                    if isinstance(api_date, str):
                        api_date = api_date[:10]  # Take first 10 characters (YYYY-MM-DD)
                
                # Validate that the API date is today (or warn if not)
                try:
                    api_date_obj = datetime.strptime(api_date, '%Y-%m-%d')
                    today_obj = datetime.strptime(today, '%Y-%m-%d')
                    days_diff = (today_obj - api_date_obj).days
                    
                    if days_diff < 0:
                        logger.error(
                            f"API returned future date {api_date} (today is {today}). "
                            f"This should never happen - there may be a timezone or API issue."
                        )
                        # Use the API date even if it's in the future (might be timezone issue)
                        pass
                    elif days_diff == 0:
                        logger.info(f"API returned rates for today ({api_date})")
                        # Success - we have today's rates
                    elif days_diff == 1:
                        logger.warning(
                            f"API returned rates for yesterday ({api_date}, today is {today}). "
                            f"Rates may be stale. The API may not have updated yet for today."
                        )
                        # If this is not the last attempt, retry
                        if attempt < max_retries - 1:
                            logger.info(f"Will retry in {retry_delay}s to get today's rates...")
                            continue
                        else:
                            logger.error(
                                f"API still returning yesterday's rates after {max_retries} attempts. "
                                f"Using yesterday's rates but this should be investigated."
                            )
                    else:
                        logger.error(
                            f"API returned rates for {days_diff} days ago ({api_date}, today is {today}). "
                            f"Rates are significantly stale!"
                        )
                        # If this is not the last attempt, retry
                        if attempt < max_retries - 1:
                            logger.info(f"Will retry in {retry_delay}s to get fresher rates...")
                            continue
                except ValueError as e:
                    logger.error(f"Failed to parse API date '{api_date}': {e}")
                    # Use today as fallback
                    api_date = today
                    logger.warning(f"Using today's date ({today}) as fallback")
                
                # Add USD to USD rate (1.0)
                rates['USD'] = 1.0
                
                # Cache the rates with the API date
                self.cache[api_date] = rates
                self.last_fetch_date = api_date
                
                logger.info(f"Fetched {len(rates)} exchange rates for date {api_date}")
                return rates, api_date
                
            except requests.RequestException as e:
                logger.error(f"Failed to fetch exchange rates (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    # Last attempt failed - try to use cached rates if available
                    if self.cache:
                        latest_date = max(self.cache.keys())
                        logger.warning(f"Using cached rates from {latest_date}")
                        return self.cache[latest_date], latest_date
                    raise
        
        # Should never reach here, but just in case
        raise requests.RequestException("Failed to fetch exchange rates after all retries")
    
    def get_rate(self, currency: str, rates: Optional[Dict[str, float]] = None) -> float:
        """
        Get exchange rate for a specific currency.
        
        Args:
            currency: Currency code (e.g., 'EUR', 'GBP')
            rates: Optional pre-fetched rates dictionary
            
        Returns:
            Exchange rate from USD to the specified currency
        """
        if rates is None:
            rates, _ = self.fetch_rates()
            
        currency = currency.upper()
        rate = rates.get(currency)
        
        if rate is None:
            logger.warning(f"Exchange rate not found for {currency}, using 1.0")
            return 1.0
            
        return rate
    
    def convert_usd_to_currency(self, usd_amount: float, currency: str, rates: Optional[Dict[str, float]] = None) -> float:
        """
        Convert USD amount to target currency.
        
        Args:
            usd_amount: Amount in USD
            currency: Target currency code
            rates: Optional pre-fetched rates dictionary (ignores date from tuple)
            
        Returns:
            Amount in target currency
        """
        # Handle tuple return from fetch_rates
        if rates is not None and isinstance(rates, tuple):
            rates = rates[0]
        rate = self.get_rate(currency, rates)
        return usd_amount * rate
    
    def convert_currency_to_usd(self, amount: float, currency: str, rates: Optional[Dict[str, float]] = None) -> float:
        """
        Convert currency amount back to USD.
        
        Args:
            amount: Amount in target currency
            currency: Source currency code
            rates: Optional pre-fetched rates dictionary (ignores date from tuple)
            
        Returns:
            Amount in USD
        """
        # Handle tuple return from fetch_rates
        if rates is not None and isinstance(rates, tuple):
            rates = rates[0]
        rate = self.get_rate(currency, rates)
        if rate == 0:
            return 0.0
        return amount / rate

