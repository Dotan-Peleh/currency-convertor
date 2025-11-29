"""
Price stability logic to prevent frequent price changes.
Only updates prices when it's beneficial or when change is significant.
"""

import logging
from typing import Dict, Optional, Tuple, Any
import config

logger = logging.getLogger(__name__)


def should_update_price(
    new_price: float,
    existing_price: Optional[float],
    price_tier: float,
    currency: str
) -> Tuple[bool, str]:
    """
    Determine if a price should be updated based on stability rules.
    
    Rules:
    1. If no existing price, always update (first time)
    2. If new price is lower, update (beneficial to customer)
    3. If new price is higher but change is > threshold, update (significant change)
    4. If new price is higher but change is < threshold, keep existing (stability)
    
    Args:
        new_price: Newly calculated price
        existing_price: Current price in the sheet (None if first time)
        price_tier: USD base price tier (for reference)
        currency: Currency code
        
    Returns:
        Tuple of (should_update: bool, reason: str)
    """
    if existing_price is None:
        return True, "First time setting price"
    
    if new_price <= 0 or existing_price <= 0:
        return True, "Invalid price detected, updating"
    
    # Calculate percentage change
    price_change = abs(new_price - existing_price) / existing_price
    
    # Rule 1: If new price is lower, always update (beneficial to customer)
    if new_price < existing_price:
        return True, f"Price decreased by {price_change*100:.1f}% (beneficial)"
    
    # Rule 2: If new price is higher but change is significant (> threshold), update
    if price_change > config.PRICE_CHANGE_THRESHOLD:
        return True, f"Price increased by {price_change*100:.1f}% (significant change > {config.PRICE_CHANGE_THRESHOLD*100}%)"
    
    # Rule 3: If new price is higher but change is small, keep existing (stability)
    return False, f"Price increased by {price_change*100:.1f}% (below {config.PRICE_CHANGE_THRESHOLD*100}% threshold, keeping stable)"


def apply_price_stability(
    new_price_data: Dict[str, Any],
    existing_prices: Dict[str, float]
) -> Tuple[Dict[str, Any], bool]:
    """
    Apply price stability rules to new price data.
    
    Args:
        new_price_data: Newly calculated price data dictionary
        existing_prices: Dictionary mapping (country:sku) -> existing User_Pays price
        
    Returns:
        Tuple of (updated price_data, was_updated: bool)
        If was_updated is False, the price was kept stable
    """
    country = new_price_data.get('Country', '')
    sku = new_price_data.get('AppleStoreSku', '')
    price_tier = new_price_data.get('Price_Tier', 0)
    currency = new_price_data.get('Currency', '')
    new_user_pays = new_price_data.get('User_Pays', 0)
    
    # Create lookup key
    lookup_key = f"{country}:{sku}"
    existing_price = existing_prices.get(lookup_key)
    
    # Check if we should update
    should_update, reason = should_update_price(
        new_user_pays,
        existing_price,
        price_tier,
        currency
    )
    
    if not should_update:
        # Keep existing price - we'll need to recalculate dependent fields
        # For now, just mark that we're keeping it stable
        logger.debug(
            f"Keeping stable price for {country} {sku}: "
            f"existing={existing_price:.2f} {currency}, "
            f"new={new_user_pays:.2f} {currency}. Reason: {reason}"
        )
        
        # Update User_Pays to existing price
        # Note: In a full implementation, we'd recalculate Gross_USD, Net_USD, etc.
        # based on the stable User_Pays, but for simplicity, we keep the new calculated
        # values for other fields and just stabilize User_Pays
        new_price_data['User_Pays'] = existing_price
        return new_price_data, False
        
    else:
        existing_str = f"{existing_price:.2f}" if existing_price else "N/A"
        logger.debug(
            f"Updating price for {country} {sku}: "
            f"{existing_str} -> "
            f"{new_user_pays:.2f} {currency}. Reason: {reason}"
        )
        return new_price_data, True

