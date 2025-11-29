"""
Price tier snapping logic for different currencies.
"""

import logging
import math
from typing import List, Optional
import config

logger = logging.getLogger(__name__)


# Base tier multipliers (for generating tiers dynamically)
# These represent the USD tier structure: [0.99, 1.99, 2.99, ...]
BASE_TIER_MULTIPLIERS = [0.99, 1.99, 2.99, 3.99, 4.99, 5.99, 6.99, 7.99, 9.99, 10.99, 12.99, 14.99, 
                         19.99, 24.99, 29.99, 39.99, 49.99, 54.99, 59.99, 64.99, 69.99, 74.99, 79.99, 
                         84.99, 89.99, 94.99, 99.99, 199.99]

# Currency-specific tier definitions for currencies that need custom tiers
# For currencies not listed, tiers are generated dynamically based on exchange rate
TIER_DEFINITIONS = {
    'USD': BASE_TIER_MULTIPLIERS,
    'EUR': BASE_TIER_MULTIPLIERS,
    'GBP': [0.79, 1.49, 1.99, 2.99, 3.99, 4.99, 5.99, 7.99, 9.99, 10.99, 12.99, 14.99, 19.99, 24.99, 29.99, 39.99, 49.99, 54.99, 59.99, 64.99, 69.99, 74.99, 79.99, 84.99, 89.99, 94.99, 99.99, 199.99],
    'JPY': [120, 160, 250, 370, 490, 610, 730, 860, 980, 1100, 1200, 1400, 1900, 2400, 2900, 3900, 4900, 5400, 5900, 6400, 6900, 7400, 7900, 8400, 8900, 9400, 9900, 19900],
    'ILS': [3.99, 7.99, 11.99, 15.99, 19.99, 23.99, 27.99, 31.99, 35.99, 39.99, 43.99, 47.99, 59.99, 74.99, 89.99, 119.99, 149.99, 164.99, 179.99, 194.99, 209.99, 224.99, 239.99, 254.99, 269.99, 284.99, 299.99, 599.99],
    # High-value currencies (thousands) - use thousands-based tiers
    'IDR': [9900, 19900, 29900, 39900, 49900, 59900, 69900, 79900, 99900, 109900, 129900, 149900, 199900, 249900, 299900, 399900, 499900, 549900, 599900, 649900, 699900, 749900, 799900, 849900, 899900, 949900, 999900, 1999900, 2999900, 3999900, 4999900],
    'VND': [24000, 49000, 74000, 99000, 124000, 149000, 174000, 199000, 249000, 274000, 324000, 374000, 499000, 624000, 749000, 999000, 1249000, 1374000, 1499000, 1624000, 1749000, 1874000, 1999000, 2124000, 2249000, 2374000, 2499000, 4999000],
    'KRW': [1200, 2400, 3600, 4800, 6000, 7200, 8400, 9600, 12000, 13200, 15600, 18000, 24000, 30000, 36000, 48000, 60000, 66000, 72000, 78000, 84000, 90000, 96000, 102000, 108000, 114000, 120000, 240000],
    # Medium-value currencies (hundreds)
    'PHP': [49, 99, 149, 199, 249, 299, 349, 399, 499, 549, 649, 749, 999, 1249, 1499, 1999, 2499, 2749, 2999, 3249, 3499, 3749, 3999, 4249, 4499, 4749, 4999, 9999],
    'INR': [79, 149, 199, 249, 299, 349, 399, 499, 599, 649, 799, 899, 1199, 1499, 1799, 2399, 2999, 3299, 3599, 3899, 4199, 4499, 4799, 5099, 5399, 5699, 5999, 11999],
    'THB': [35, 69, 99, 139, 169, 199, 229, 269, 339, 369, 439, 509, 679, 849, 1019, 1359, 1699, 1869, 2039, 2209, 2379, 2549, 2719, 2889, 3059, 3229, 3399, 6799],
    'MYR': [3.99, 7.99, 11.99, 15.99, 19.99, 23.99, 27.99, 31.99, 39.99, 43.99, 51.99, 59.99, 79.99, 99.99, 119.99, 159.99, 199.99, 219.99, 239.99, 259.99, 279.99, 299.99, 319.99, 339.99, 359.99, 379.99, 399.99, 799.99],
    'CNY': [6, 12, 18, 25, 31, 37, 43, 50, 62, 68, 81, 93, 124, 155, 186, 248, 310, 341, 372, 403, 434, 465, 496, 527, 558, 589, 620, 1240],
    'TWD': [30, 60, 90, 120, 150, 180, 210, 240, 300, 330, 390, 450, 600, 750, 900, 1200, 1500, 1650, 1800, 1950, 2100, 2250, 2400, 2550, 2700, 2850, 3000, 6000],
    # Other currencies will use dynamic generation
}


def generate_tiers_for_price_range(min_price: float, max_price: float) -> List[float]:
    """
    Generate appropriate tier list for a price range.
    Creates nice round numbers that look good to users.
    
    Args:
        min_price: Minimum price in the range
        max_price: Maximum price in the range
        
    Returns:
        List of tier prices
    """
    tiers = []
    
    # Determine the scale (ones, tens, hundreds, thousands, etc.)
    if max_price < 1:
        # Sub-unit currency (very rare)
        scale = 0.01
        base_tiers = [0.99, 1.99, 2.99, 3.99, 4.99, 5.99, 6.99, 7.99, 9.99]
        tiers = [t * scale for t in base_tiers if t * scale <= max_price * 1.5]
    elif max_price < 10:
        # Single digits - use .99 endings
        tiers = [0.99, 1.99, 2.99, 3.99, 4.99, 5.99, 6.99, 7.99, 9.99]
    elif max_price < 100:
        # Tens - use .99 endings
        for base in [9.99, 19.99, 29.99, 39.99, 49.99, 59.99, 69.99, 79.99, 89.99, 99.99]:
            if base <= max_price * 1.5:
                tiers.append(base)
    elif max_price < 1000:
        # Hundreds - use .99 endings or round numbers
        for base in [99, 199, 299, 399, 499, 599, 699, 799, 899, 999]:
            if base <= max_price * 1.5:
                tiers.append(float(base))
    elif max_price < 10000:
        # Thousands - use round numbers ending in 00 or 900
        for base in [900, 1900, 2900, 3900, 4900, 5900, 6900, 7900, 8900, 9900]:
            if base <= max_price * 1.5:
                tiers.append(float(base))
    else:
        # Tens of thousands - use round numbers
        step = max(100, int(max_price / 50))  # Dynamic step based on range
        for i in range(1, 30):
            tier = round(i * step / 100) * 100
            if tier <= max_price * 1.5:
                tiers.append(float(tier))
            else:
                break
    
    # Ensure we have at least a few tiers
    if len(tiers) < 3:
        # Fallback: create simple tiers
        step = max(1, int(max_price / 10))
        tiers = [float(step * i) for i in range(1, 11) if step * i <= max_price * 1.5]
    
    return sorted(tiers)


def get_tiers_for_currency(currency: str, reference_price: Optional[float] = None) -> List[float]:
    """
    Get tier list for a specific currency.
    If currency not in definitions and reference_price provided, generates tiers dynamically.
    
    Args:
        currency: Currency code
        reference_price: Optional reference price to generate tiers if currency not defined
        
    Returns:
        List of tier prices for the currency
    """
    currency = currency.upper()
    
    # Check if we have predefined tiers
    if currency in TIER_DEFINITIONS:
        return TIER_DEFINITIONS[currency]
    
    # If reference price provided, generate tiers dynamically
    if reference_price is not None and reference_price > 0:
        # Generate tiers based on price range
        # Estimate max price as 200x the reference (for $0.99 to $199.99 range)
        max_price = reference_price * 200
        min_price = reference_price * 0.5
        return generate_tiers_for_price_range(min_price, max_price)
    
    # Default to USD tiers (will be scaled if needed)
    return TIER_DEFINITIONS['USD']


def make_nice_number(price: float, max_increase: float = 2.0) -> float:
    """
    Create a nice-looking number that's slightly higher than the price.
    Rounds up by at most max_increase units to make it look good.
    
    Args:
        price: Raw price
        max_increase: Maximum amount to increase (in same units as price)
        
    Returns:
        Nice number slightly higher than price (within max_increase)
    """
    if price <= 0:
        return price
    
    # Always start with just adding a small amount, then make it "nice"
    base_increase = min(max_increase, price * 0.001)  # At most 0.1% or max_increase, whichever is smaller
    nice = price + base_increase
    
    # Now make it a "nice" number based on magnitude
    if price < 1:
        # Sub-unit: round to 2 decimal places
        nice = math.ceil(nice * 100) / 100
    elif price < 10:
        # Single digits: round to nearest integer or .99
        nice = math.ceil(nice)
        # If we can make it .99 without exceeding max_increase, do it
        if nice - price <= max_increase and nice - int(nice) < 0.5:
            nice = int(nice) + 0.99
    elif price < 100:
        # Tens: round to nearest integer or .99
        nice = math.ceil(nice)
        # If we can make it .99 without exceeding max_increase, do it
        if nice - price <= max_increase:
            nice = int(nice) + 0.99
    elif price < 1000:
        # Hundreds: round to nearest 10 or 5
        nice = math.ceil(nice / 5) * 5
    elif price < 10000:
        # Thousands: round to nearest 10 or 50
        nice = math.ceil(nice / 10) * 10
    elif price < 100000:
        # Tens of thousands: round to nearest 100
        nice = math.ceil(nice / 100) * 100
    else:
        # Hundreds of thousands+: round to nearest 1000
        nice = math.ceil(nice / 1000) * 1000
    
    # Final check: ensure we don't exceed max_increase
    if nice - price > max_increase:
        # Just add max_increase and round to reasonable precision
        nice = price + max_increase
        if price < 1:
            nice = round(nice, 2)
        elif price < 100:
            nice = round(nice, 0)
        else:
            nice = round(nice, 0)
    
    return round(nice, 2)


def snap_to_tier(price: float, currency: str, mode: Optional[str] = None) -> float:
    """
    Snap a price to the appropriate tier for the given currency.
    For visibility prices, rounds up slightly (1-2 units max) to ensure it's higher than raw price.
    
    Args:
        price: Raw price to snap
        currency: Currency code
        mode: Snapping mode ("nearest", "up", "down"). Defaults to config setting.
        
    Returns:
        Snapped price (always >= input price when mode is "up", but only slightly higher)
    """
    if price <= 0:
        return price
        
    mode = mode or config.TIER_SNAPPING_MODE
    # Get tiers, using price as reference if currency not predefined
    tiers = get_tiers_for_currency(currency, reference_price=price)
    
    # For "up" mode, we want to round up but only slightly (1-2 units max)
    if mode == "up":
        # Determine max acceptable increase: always 1-2 units max, regardless of currency
        # Use percentage-based for very large numbers to keep it reasonable
        if price < 1:
            max_increase = 0.02  # 2 cents max
        elif price < 10:
            max_increase = 1.0  # 1 unit max
        elif price < 100:
            max_increase = 2.0  # 2 units max
        elif price < 1000:
            max_increase = 2.0  # Still 2 units max for hundreds
        elif price < 10000:
            max_increase = 2.0  # Still 2 units max for thousands
        else:
            # For very large numbers, use 0.01% or 2 units, whichever is smaller
            max_increase = min(2.0, price * 0.0001)
        
        # Find the next tier above price
        for tier in tiers:
            if tier >= price:
                increase = tier - price
                # If tier is close enough (within max_increase), use it
                if increase <= max_increase:
                    return tier
                # Otherwise, create a nice number just slightly above
                break
        
        # Create a nice number just slightly above (within max_increase)
        return make_nice_number(price, max_increase)
    
    # Find the appropriate tier for other modes
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
            return tiers[i]
        elif price == tiers[i + 1]:
            return tiers[i + 1]
    
    if lower_tier is None or upper_tier is None:
        # Fallback: find closest tier
        closest_tier = min(tiers, key=lambda x: abs(x - price))
        logger.warning(f"Could not find tier range for {price} {currency}, using closest: {closest_tier}")
        return closest_tier
    
    # Apply snapping mode
    if mode == "down":
        return lower_tier
    else:  # nearest
        # Snap to the closer tier
        distance_to_lower = abs(price - lower_tier)
        distance_to_upper = abs(price - upper_tier)
        
        if distance_to_lower <= distance_to_upper:
            return lower_tier
        else:
            return upper_tier

