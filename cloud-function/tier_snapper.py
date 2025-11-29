"""
Price tier snapping logic for different currencies.
"""

import logging
from typing import List, Optional
import config

logger = logging.getLogger(__name__)


# Country-specific tier definitions
# These follow Apple and Google Play Store pricing tiers
TIER_DEFINITIONS = {
    'USD': [0.99, 1.99, 2.99, 3.99, 4.99, 5.99, 6.99, 7.99, 9.99, 10.99, 12.99, 14.99, 19.99, 24.99, 29.99, 39.99, 49.99, 54.99, 59.99, 64.99, 69.99, 74.99, 79.99, 84.99, 89.99, 94.99, 99.99, 199.99],
    'EUR': [0.99, 1.99, 2.99, 3.99, 4.99, 5.99, 6.99, 7.99, 9.99, 10.99, 12.99, 14.99, 19.99, 24.99, 29.99, 39.99, 49.99, 54.99, 59.99, 64.99, 69.99, 74.99, 79.99, 84.99, 89.99, 94.99, 99.99, 199.99],
    'GBP': [0.79, 1.49, 1.99, 2.99, 3.99, 4.99, 5.99, 7.99, 9.99, 10.99, 12.99, 14.99, 19.99, 24.99, 29.99, 39.99, 49.99, 54.99, 59.99, 64.99, 69.99, 74.99, 79.99, 84.99, 89.99, 94.99, 99.99, 199.99],
    'JPY': [120, 160, 250, 370, 490, 610, 730, 860, 980, 1100, 1200, 1400, 1900, 2400, 2900, 3900, 4900, 5400, 5900, 6400, 6900, 7400, 7900, 8400, 8900, 9400, 9900, 19900],
    'ILS': [3.9, 7.9, 11.9, 15.9, 19.9, 23.9, 27.9, 31.9, 35.9, 39.9, 43.9, 47.9, 59.9, 74.9, 89.9, 119.9, 149.9, 164.9, 179.9, 194.9, 209.9, 224.9, 239.9, 254.9, 269.9, 284.9, 299.9, 599.9],
    # Add more currencies as needed - default to USD tiers
}


def get_tiers_for_currency(currency: str) -> List[float]:
    """
    Get tier list for a specific currency.
    
    Args:
        currency: Currency code
        
    Returns:
        List of tier prices for the currency
    """
    currency = currency.upper()
    return TIER_DEFINITIONS.get(currency, TIER_DEFINITIONS['USD'])


def snap_to_tier(price: float, currency: str, mode: Optional[str] = None) -> float:
    """
    Snap a price to the nearest tier for the given currency.
    
    Args:
        price: Raw price to snap
        currency: Currency code
        mode: Snapping mode ("nearest", "up", "down"). Defaults to config setting.
        
    Returns:
        Snapped price
    """
    if price <= 0:
        return price
        
    mode = mode or config.TIER_SNAPPING_MODE
    tiers = get_tiers_for_currency(currency)
    
    # Find the appropriate tier
    if price <= tiers[0]:
        return tiers[0]
    
    if price >= tiers[-1]:
        return tiers[-1]
    
    # Find the two tiers the price falls between
    lower_tier = None
    upper_tier = None
    
    for i in range(len(tiers) - 1):
        if tiers[i] <= price <= tiers[i + 1]:
            lower_tier = tiers[i]
            upper_tier = tiers[i + 1]
            break
    
    if lower_tier is None or upper_tier is None:
        # Fallback: find closest tier
        closest_tier = min(tiers, key=lambda x: abs(x - price))
        logger.warning(f"Could not find tier range for {price} {currency}, using closest: {closest_tier}")
        return closest_tier
    
    # Apply snapping mode
    if mode == "up":
        return upper_tier
    elif mode == "down":
        return lower_tier
    else:  # nearest
        # Snap to the closer tier
        distance_to_lower = abs(price - lower_tier)
        distance_to_upper = abs(price - upper_tier)
        
        if distance_to_lower <= distance_to_upper:
            return lower_tier
        else:
            return upper_tier

