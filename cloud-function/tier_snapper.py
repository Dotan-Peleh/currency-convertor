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
    'ILS': [3.99, 7.99, 11.99, 15.99, 19.99, 23.99, 27.99, 31.99, 35.99, 39.99, 43.99, 47.99, 59.99, 74.99, 89.99, 119.99, 149.99, 164.99, 179.99, 194.99, 209.99, 224.99, 239.99, 254.99, 269.99, 284.99, 299.99, 599.99],
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
    Snap a price to the appropriate tier for the given currency.
    For visibility prices, always rounds UP to ensure it's higher than raw price.
    
    Args:
        price: Raw price to snap
        currency: Currency code
        mode: Snapping mode ("nearest", "up", "down"). Defaults to config setting.
        
    Returns:
        Snapped price (always >= input price when mode is "up")
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
        if tiers[i] < price < tiers[i + 1]:
            lower_tier = tiers[i]
            upper_tier = tiers[i + 1]
            break
        elif price == tiers[i]:
            # If price exactly matches a tier, use that tier (don't round up)
            return tiers[i]
        elif price == tiers[i + 1]:
            # If price exactly matches upper tier, use that tier
            return tiers[i + 1]
    
    if lower_tier is None or upper_tier is None:
        # Fallback: find closest tier, but if mode is "up", round up
        if mode == "up":
            # Find the first tier that's >= price
            for tier in tiers:
                if tier >= price:
                    return tier
            return tiers[-1]
        else:
            closest_tier = min(tiers, key=lambda x: abs(x - price))
            logger.warning(f"Could not find tier range for {price} {currency}, using closest: {closest_tier}")
            return closest_tier
    
    # Apply snapping mode
    if mode == "up":
        # Always round up to ensure visibility price is higher
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

