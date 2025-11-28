"""
Tax (VAT/GST) calculation logic for different countries.
"""

import logging
from typing import Dict, Tuple
import config

logger = logging.getLogger(__name__)


# Country to tax rate mapping (VAT/GST rates as decimals, e.g., 0.19 for 19%)
TAX_RATES: Dict[str, float] = {
    # EU countries (VAT-inclusive)
    'AT': 0.20,  # Austria
    'BE': 0.21,  # Belgium
    'BG': 0.20,  # Bulgaria
    'HR': 0.25,  # Croatia
    'CY': 0.19,  # Cyprus
    'CZ': 0.21,  # Czech Republic
    'DK': 0.25,  # Denmark
    'EE': 0.20,  # Estonia
    'FI': 0.24,  # Finland
    'FR': 0.20,  # France
    'DE': 0.19,  # Germany
    'GR': 0.24,  # Greece
    'HU': 0.27,  # Hungary
    'IE': 0.23,  # Ireland
    'IT': 0.22,  # Italy
    'LV': 0.21,  # Latvia
    'LT': 0.21,  # Lithuania
    'LU': 0.17,  # Luxembourg
    'MT': 0.18,  # Malta
    'NL': 0.21,  # Netherlands
    'PL': 0.23,  # Poland
    'PT': 0.23,  # Portugal
    'RO': 0.19,  # Romania
    'SK': 0.20,  # Slovakia
    'SI': 0.22,  # Slovenia
    'ES': 0.21,  # Spain
    'SE': 0.25,  # Sweden
    
    # UK (VAT-inclusive)
    'GB': 0.20,
    
    # Other VAT-inclusive countries
    'AU': 0.10,  # Australia (GST)
    'NZ': 0.15,  # New Zealand (GST)
    'ZA': 0.15,  # South Africa (VAT)
    'BR': 0.17,  # Brazil (approximate average)
    'AR': 0.21,  # Argentina (VAT)
    'CL': 0.19,  # Chile (VAT)
    'CO': 0.19,  # Colombia (VAT)
    'MX': 0.16,  # Mexico (VAT)
    'PE': 0.18,  # Peru (VAT)
    
    # VAT-exclusive countries (tax collected separately)
    'US': 0.0,   # US - varies by state, handled separately
    'CA': 0.0,   # Canada - varies by province, handled separately
    
    # No VAT countries
    'HK': 0.0,   # Hong Kong
    'SG': 0.0,   # Singapore (GST but typically not on digital goods)
    'AE': 0.0,   # UAE
    'QA': 0.0,   # Qatar
    'KW': 0.0,   # Kuwait
    'BH': 0.0,   # Bahrain
    'OM': 0.0,   # Oman
    'SA': 0.0,   # Saudi Arabia (VAT introduced but may not apply to digital)
    
    # Japan (consumption tax - VAT-inclusive)
    'JP': 0.10,
    
    # South Korea (VAT-inclusive)
    'KR': 0.10,
    
    # India (GST - VAT-inclusive)
    'IN': 0.18,
    
    # China (VAT-inclusive)
    'CN': 0.13,
    
    # Add more as needed
}

# Countries where VAT is included in the display price
VAT_INCLUSIVE_COUNTRIES = {
    'AT', 'BE', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IE', 'IT',
    'LV', 'LT', 'LU', 'MT', 'NL', 'PL', 'PT', 'RO', 'SK', 'SI', 'ES', 'SE', 'GB', 'AU', 'NZ',
    'ZA', 'BR', 'AR', 'CL', 'CO', 'MX', 'PE', 'JP', 'KR', 'IN', 'CN'
}

# Countries where VAT is excluded from display price (tax collected separately)
VAT_EXCLUSIVE_COUNTRIES = {'US', 'CA'}


def get_tax_rate(country_code: str) -> float:
    """
    Get tax rate for a country.
    
    Args:
        country_code: ISO country code (e.g., 'DE', 'US')
        
    Returns:
        Tax rate as decimal (e.g., 0.19 for 19%)
    """
    country_code = country_code.upper()
    return TAX_RATES.get(country_code, 0.0)


def is_vat_inclusive(country_code: str) -> bool:
    """
    Check if country uses VAT-inclusive pricing.
    
    Args:
        country_code: ISO country code
        
    Returns:
        True if VAT is included in display price
    """
    country_code = country_code.upper()
    return country_code in VAT_INCLUSIVE_COUNTRIES


def calculate_tax(price: float, country_code: str) -> Tuple[float, float]:
    """
    Calculate tax amount and net price before tax.
    
    Args:
        price: Display price (may include or exclude tax depending on country)
        country_code: ISO country code
        
    Returns:
        Tuple of (tax_amount, net_price_before_tax)
    """
    country_code = country_code.upper()
    tax_rate = get_tax_rate(country_code)
    
    if is_vat_inclusive(country_code):
        # VAT is included in the price
        # net = price / (1 + tax_rate)
        # tax = price - net
        if tax_rate == 0:
            return 0.0, price
        net_price = price / (1 + tax_rate)
        tax_amount = price - net_price
        return tax_amount, net_price
    else:
        # VAT is excluded (or no VAT)
        # net = price
        # tax = price * tax_rate (if applicable)
        tax_amount = price * tax_rate
        net_price = price
        return tax_amount, net_price

