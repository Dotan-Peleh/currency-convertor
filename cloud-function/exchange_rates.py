"""
Exchange rate API client for fetching currency conversion rates.
"""

import requests
import logging
from typing import Dict, Optional
from datetime import datetime
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
        
    def fetch_rates(self) -> Dict[str, float]:
        """
        Fetch current exchange rates from USD to all currencies.
        
        Returns:
            Dictionary mapping currency codes to exchange rates (USD to currency)
            
        Raises:
            requests.RequestException: If API request fails
        """
        try:
            url = self.base_url
            if self.api_key:
                url = f"{url}?api_key={self.api_key}"
                
            logger.info(f"Fetching exchange rates from {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            rates = data.get('rates', {})
            
            # Add USD to USD rate (1.0)
            rates['USD'] = 1.0
            
            # Cache the rates
            today = datetime.utcnow().strftime('%Y-%m-%d')
            self.cache[today] = rates
            self.last_fetch_date = today
            
            logger.info(f"Fetched {len(rates)} exchange rates")
            return rates
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch exchange rates: {e}")
            # Try to use cached rates if available
            if self.cache:
                latest_date = max(self.cache.keys())
                logger.warning(f"Using cached rates from {latest_date}")
                return self.cache[latest_date]
            raise
    
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
            rates = self.fetch_rates()
            
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
            rates: Optional pre-fetched rates dictionary
            
        Returns:
            Amount in target currency
        """
        rate = self.get_rate(currency, rates)
        return usd_amount * rate
    
    def convert_currency_to_usd(self, amount: float, currency: str, rates: Optional[Dict[str, float]] = None) -> float:
        """
        Convert currency amount back to USD.
        
        Args:
            amount: Amount in target currency
            currency: Source currency code
            rates: Optional pre-fetched rates dictionary
            
        Returns:
            Amount in USD
        """
        rate = self.get_rate(currency, rates)
        if rate == 0:
            return 0.0
        return amount / rate

