"""
Price tier snapping logic for different currencies.
Uses Apple's official pricing tiers from their pricing matrix CSV.
"""

import logging
import json
import os
from typing import List, Optional, Dict
import config

logger = logging.getLogger(__name__)

# Load Apple pricing tiers from JSON file
APPLE_TIERS: Dict[str, List[float]] = {}
TIER_FILE = os.path.join(os.path.dirname(__file__), 'apple_tiers.json')

def _load_apple_tiers():
    """Load Apple pricing tiers from JSON file"""
    global APPLE_TIERS
    if APPLE_TIERS:
        return APPLE_TIERS
    
    try:
        if os.path.exists(TIER_FILE):
            with open(TIER_FILE, 'r') as f:
                APPLE_TIERS = json.load(f)
                # Convert string keys to float lists
                APPLE_TIERS = {k: [float(x) for x in v] for k, v in APPLE_TIERS.items()}
                logger.info(f"Loaded Apple pricing tiers for {len(APPLE_TIERS)} currencies")
            return APPLE_TIERS
        else:
            logger.warning(f"Apple tiers file not found: {TIER_FILE}")
            return {}
    except Exception as e:
        logger.error(f"Error loading Apple tiers: {e}")
        return {}

# Load tiers on module import
_load_apple_tiers()


def get_tiers_for_currency(currency: str, reference_price: Optional[float] = None) -> List[float]:
    """
    Get pricing tiers for a currency using Apple's official tiers.
    
    Args:
        currency: Currency code (e.g., 'USD', 'EUR', 'BRL')
        reference_price: Optional reference price (not used with Apple tiers, kept for compatibility)
        
    Returns:
        List of tier prices for the currency
    """
    currency = currency.upper()
    
    # Use Apple tiers if available
    if APPLE_TIERS and currency in APPLE_TIERS:
        return APPLE_TIERS[currency]
    
    # Fallback to USD tiers if currency not found
    if APPLE_TIERS and 'USD' in APPLE_TIERS:
        logger.warning(f"No Apple tiers found for {currency}, using USD tiers")
        return APPLE_TIERS['USD']
    
    # Last resort: return empty list (will trigger fallback logic)
    logger.warning(f"No Apple tiers available for {currency}")
    return []


def snap_to_tier(price: float, currency: str, mode: Optional[str] = None) -> float:
    """
    Snap a price to the appropriate Apple tier for the given currency.
    For "up" mode, finds the next Apple tier above the price.
    
    Args:
        price: Raw price to snap
        currency: Currency code
        mode: Snapping mode ("nearest", "up", "down"). Defaults to config setting.
              "up" mode finds the next tier above price (always >= price)
        
    Returns:
        Snapped price (always >= input price when mode is "up")
    """
    if price <= 0:
        return price
        
    mode = mode or config.TIER_SNAPPING_MODE
    # Get Apple tiers for currency
    tiers = get_tiers_for_currency(currency, reference_price=price)
    
    if not tiers:
        # Fallback: return price + small increment
        logger.warning(f"No tiers available for {currency}, returning price + 0.01")
        return round(price + 0.01, 2)
    
    # For "up" mode, find the next tier above price
    if mode == "up":
        # Find the next tier above price (must be STRICTLY greater)
        for tier in tiers:
            if tier > price:
                return round(tier, 2)
        
        # If price is above all tiers, return the highest tier
        logger.warning(f"Price {price} {currency} exceeds all tiers, using highest tier: {tiers[-1]}")
        return round(tiers[-1], 2)
    
    # For "down" mode, find the previous tier below price
    if mode == "down":
        for tier in reversed(tiers):
            if tier <= price:
                return round(tier, 2)
        return round(tiers[0], 2)
    
    # For "nearest" mode, find the closest tier
    closest_tier = min(tiers, key=lambda x: abs(x - price))
    return round(closest_tier, 2)
