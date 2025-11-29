"""
Price tier snapping logic for different currencies.
"""

import logging
import math
from typing import List, Optional
import config

logger = logging.getLogger(__name__)


def generate_granular_tiers(max_price: float) -> List[float]:
    """
    Generate granular tier list similar to app store pricing patterns.
    Creates many small increments to allow minimal markup (1-2 units).
    
    Based on patterns observed in pricing matrices:
    - Low prices (< 10): 0.29, 0.39, 0.49, 0.59, 0.69, 0.79, 0.89, 0.9, 0.95, 0.99, 1.0, 1.09...
    - Medium prices (10-100): 9, 10, 15, 19, 20, 25, 29, 30, 35, 39, 40, 45, 49, 50...
    - High prices (100+): similar patterns scaled
    
    Args:
        max_price: Maximum price to generate tiers for
        
    Returns:
        List of granular tier prices
    """
    tiers = []
    limit = max_price * 1.5
    max_iterations = 10000  # Safety limit
    
    # Always start from low prices for currencies that use decimal pricing
    # For currencies with whole number pricing (like IDR, JPY), start from appropriate base
    if max_price < 1:
        # Low prices: 0.29, 0.39, 0.49, 0.59, 0.69, 0.79, 0.89, 0.9, 0.95, 0.99, 1.0, 1.09...
        current = 0.29
        iterations = 0
        while current <= limit and current <= 10 and iterations < max_iterations:
            tiers.append(round(current, 2))
            iterations += 1
            
            # Handle special cases first
            if abs(current - 0.9) < 0.001:
                current = 0.95
            elif abs(current - 0.95) < 0.001:
                current = 0.99
            elif abs(current - 0.99) < 0.001:
                current = 1.0
            elif current < 0.9:
                current += 0.10
            elif current < 2.0:
                # 1.0, 1.09, 1.19, 1.29...
                if abs(current - round(current)) < 0.001:  # Is whole number
                    current += 0.09
                else:
                    current += 0.10
            else:
                current += 0.10
                
    elif max_price < 100:
        # For prices 10-100, continue decimal pattern from 0.29 up to limit
        # This covers: 0.29, 0.39, ..., 9.9, 10.0, 10.9, 11.9, ..., 99.9
        current = 0.29
        iterations = 0
        while current <= limit and current <= 100 and iterations < max_iterations:
            tiers.append(round(current, 2))
            iterations += 1
            
            # Handle special cases
            if abs(current - 0.89) < 0.001:
                current = 0.9
            elif abs(current - 0.9) < 0.001:
                current = 0.95
            elif abs(current - 0.95) < 0.001:
                current = 0.99
            elif abs(current - 0.99) < 0.001:
                current = 1.0
            elif current < 0.89:
                current += 0.10
            elif current < 10:
                # 1.0, 1.09, 1.19, ..., 9.9
                if abs(current - round(current)) < 0.001:  # Is whole number
                    current += 0.09
                else:
                    current += 0.10
            else:
                # 10.0, 10.9, 11.9, ..., 99.9
                if abs(current - round(current)) < 0.001:  # Is whole number
                    current += 0.9
                else:
                    current = round(current) + 0.9
                
    elif max_price < 1000:
        # For prices 100-1000, use whole number pattern: 9, 10, 15, 19, 20, ..., 99, 100, 150, 199, 200...
        # Start from 9.0 for whole number pattern
        current = 9.0
        iterations = 0
        while current <= limit and current <= 1000 and iterations < max_iterations:
            tiers.append(round(current, 2))
            iterations += 1
            if current < 100:
                # 9, 10, 15, 19, 20, 25, 29, 30, ...
                last_digit = int(current) % 10
                if last_digit == 9:
                    current += 1
                elif last_digit == 0:
                    current += 5
                elif last_digit == 5:
                    current += 4
                else:
                    current += 1
            else:
                # 100, 150, 199, 200, 250, 299, 300, ...
                last_two = int(current) % 100
                if last_two == 99:
                    current += 1
                elif last_two == 0:
                    current += 50
                elif last_two == 50:
                    current += 49
                else:
                    current += 1
                
    elif max_price < 10000:
        # For prices 1000-10000, use whole number pattern: 9, 10, 15, ..., 900, 1000, 1500, 1900, 2000...
        current = 9.0
        iterations = 0
        while current <= limit and current <= 10000 and iterations < max_iterations:
            tiers.append(round(current, 2))
            iterations += 1
            if current < 100:
                last_digit = int(current) % 10
                if last_digit == 9:
                    current += 1
                elif last_digit == 0:
                    current += 5
                elif last_digit == 5:
                    current += 4
                else:
                    current += 1
            elif current < 1000:
                last_two = int(current) % 100
                if last_two == 99:
                    current += 1
                elif last_two == 0:
                    current += 50
                elif last_two == 50:
                    current += 49
                else:
                    current += 1
            else:
                # 1000, 1500, 1900, 2000, 2500, 2900, 3000, ...
                last_three = int(current) % 1000
                if last_three == 900:
                    current += 100
                elif last_three == 0:
                    current += 500
                elif last_three == 500:
                    current += 400
                else:
                    current += 10
                
    else:
        # For prices 10000+, use whole number pattern: 9, 10, 15, ..., 9000, 10000, 15000, 19000, 20000...
        current = 9.0
        iterations = 0
        while current <= limit and current <= 100000 and iterations < max_iterations:
            tiers.append(round(current, 2))
            iterations += 1
            if current < 100:
                last_digit = int(current) % 10
                if last_digit == 9:
                    current += 1
                elif last_digit == 0:
                    current += 5
                elif last_digit == 5:
                    current += 4
                else:
                    current += 1
            elif current < 1000:
                last_two = int(current) % 100
                if last_two == 99:
                    current += 1
                elif last_two == 0:
                    current += 50
                elif last_two == 50:
                    current += 49
                else:
                    current += 1
            elif current < 10000:
                last_three = int(current) % 1000
                if last_three == 900:
                    current += 100
                elif last_three == 0:
                    current += 500
                elif last_three == 500:
                    current += 400
                else:
                    current += 10
            else:
                # 10000, 15000, 19000, 20000, 25000, 29000, 30000, ...
                last_four = int(current) % 10000
                if last_four == 9000:
                    current += 1000
                elif last_four == 0:
                    current += 5000
                elif last_four == 5000:
                    current += 4000
                else:
                    current += 100
    
    return sorted(list(set(tiers)))  # Remove duplicates and sort


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
    'JPY': generate_granular_tiers(230000),  # Generate granular tiers up to ~230k JPY
    'ILS': generate_granular_tiers(450),  # Generate granular tiers up to ~450 ILS
    # High-value currencies (thousands) - use granular tiers
    'IDR': generate_granular_tiers(40000),  # Generate granular tiers up to ~40k IDR
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
        # Generate granular tiers based on price range
        # Estimate max price as 200x the reference (for $0.99 to $199.99 range)
        max_price = reference_price * 200
        return generate_granular_tiers(max_price)
    
    # Default to USD tiers (will be scaled if needed)
    return TIER_DEFINITIONS['USD']


def make_nice_number(price: float, max_increase: float = 2.0) -> float:
    """
    Create a nice-looking number that's slightly higher than the price.
    Prioritizes .99 endings when possible (within max_increase limit).
    
    Args:
        price: Raw price
        max_increase: Maximum amount to increase (in same units as price)
        
    Returns:
        Nice number slightly higher than price (within max_increase)
        Prefers .99 endings (e.g., 110.49 -> 110.99)
    """
    if price <= 0:
        return price
    
    # Strategy: Try .99 endings first, then other nice numbers
    
    # For prices >= 1, try to make it end in .99
    if price >= 1:
        # Get the integer part
        int_part = int(price)
        decimal_part = price - int_part
        
        # Try .99 ending first
        candidate_99 = int_part + 0.99
        if candidate_99 > price and candidate_99 - price <= max_increase:
            return round(candidate_99, 2)
        
        # If we're close to the next integer, try next integer + .99
        if decimal_part > 0.5:  # Already past .50, might be able to go to next .99
            next_99 = int_part + 1 + 0.99
            if next_99 > price and next_99 - price <= max_increase:
                return round(next_99, 2)
        
        # Try .9 ending (less preferred but still nice)
        candidate_9 = int_part + 0.9
        if candidate_9 > price and candidate_9 - price <= max_increase:
            return round(candidate_9, 1)
        
        # If close to next integer, try next integer + .9
        if decimal_part > 0.5:
            next_9 = int_part + 1 + 0.9
            if next_9 > price and next_9 - price <= max_increase:
                return round(next_9, 1)
    
    # For prices < 1, prioritize .99 ending
    if price < 1:
        # Always try 0.99 first if price is below 0.99
        if price < 0.99:
            distance_to_99 = 0.99 - price
            # If price is >= 0.50, always go to .99 (within max_increase which is set to allow this)
            if price >= 0.50:
                return 0.99
            # If price is < 0.50 but close to .99 (within 0.10), still try to get there
            elif distance_to_99 <= 0.10:
                return 0.99
            # Otherwise check if within max_increase
            elif distance_to_99 <= max_increase:
                return 0.99
        # Otherwise round up to nearest cent
        nice = math.ceil(price * 100) / 100
        if nice - price <= max_increase:
            return round(nice, 2)
        else:
            return round(price + max_increase, 2)
    
    # Fallback: Round up to next integer or nice number
    # For prices 1-10: round to next integer
    if price < 10:
        nice = math.ceil(price)
        if nice - price <= max_increase:
            return round(nice, 2)
    
    # For prices 10-100: try next integer, or .99 if possible
    elif price < 100:
        int_part = int(price)
        # Try next integer
        next_int = int_part + 1
        if next_int - price <= max_increase:
            # Check if we can make it .99
            candidate_99 = next_int + 0.99
            if candidate_99 - price <= max_increase:
                return round(candidate_99, 2)
            return round(next_int, 2)
    
    # For prices 100-1000: try .99 ending on current or next integer
    elif price < 1000:
        int_part = int(price)
        # Try current integer + .99
        candidate_99 = int_part + 0.99
        if candidate_99 > price and candidate_99 - price <= max_increase:
            return round(candidate_99, 2)
        # Try next integer + .99
        next_99 = int_part + 1 + 0.99
        if next_99 - price <= max_increase:
            return round(next_99, 2)
        # Fallback: round to next 5
        nice = math.ceil(price / 5) * 5
        if nice - price <= max_increase:
            return round(nice, 2)
    
    # For prices 1000+: try .99 ending
    elif price < 10000:
        int_part = int(price)
        # Try current integer + .99
        candidate_99 = int_part + 0.99
        if candidate_99 > price and candidate_99 - price <= max_increase:
            return round(candidate_99, 2)
        # Try next integer + .99
        next_99 = int_part + 1 + 0.99
        if next_99 - price <= max_increase:
            return round(next_99, 2)
        # Fallback: round to next 10
        nice = math.ceil(price / 10) * 10
        if nice - price <= max_increase:
            return round(nice, 2)
    
    # For very large prices: try .99 ending
    else:
        int_part = int(price)
        # Try current integer + .99
        candidate_99 = int_part + 0.99
        if candidate_99 > price and candidate_99 - price <= max_increase:
            return round(candidate_99, 2)
        # Try next integer + .99
        next_99 = int_part + 1 + 0.99
        if next_99 - price <= max_increase:
            return round(next_99, 2)
        # Fallback: round to next 100
        nice = math.ceil(price / 100) * 100
        if nice - price <= max_increase:
            return round(nice, 2)
    
    # Final fallback: just add max_increase and round appropriately
    nice = price + max_increase
    if price < 1:
        return round(nice, 2)
    elif price < 100:
        # Try to make it .99 if possible
        int_part = int(nice)
        if nice - int_part < 0.5:  # Close to integer
            return round(int_part + 0.99, 2)
        return round(nice, 2)
    else:
        # For larger numbers, try .99 ending
        int_part = int(nice)
        if nice - int_part < 0.5:
            return round(int_part + 0.99, 2)
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
            # For sub-unit prices, prioritize .99 endings
            # If price is between 0.50 and 0.98, allow up to 0.50 to reach .99
            if 0.50 <= price < 0.99:
                distance_to_99 = 0.99 - price
                max_increase = distance_to_99 + 0.01  # Allow reaching .99
            elif price < 0.50:
                # For prices < 0.50, allow up to 0.10 to reach .99
                distance_to_99 = 0.99 - price
                if distance_to_99 <= 0.10:
                    max_increase = distance_to_99 + 0.01
                else:
                    max_increase = 0.02  # 2 cents max
            else:
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
        
        # Strategy: Prioritize .99 endings
        # First, try to create a .99 number directly (preferred)
        nice_99 = make_nice_number(price, max_increase)
        
        # Ensure it's strictly greater than price
        if nice_99 <= price:
            # If make_nice_number didn't increase, force a small increase
            nice_99 = price + min(0.01, max_increase)
            nice_99 = make_nice_number(nice_99, max_increase)
        
        # Check if the nice number ends in .99 (or .9)
        nice_99_rounded = round(nice_99, 2)
        nice_99_decimal = nice_99_rounded - int(nice_99_rounded)
        is_99_ending = abs(nice_99_decimal - 0.99) < 0.01 or abs(nice_99_decimal - 0.9) < 0.01
        
        # If we got a .99 ending and it's within limit, use it
        if is_99_ending and nice_99 > price and nice_99 - price <= max_increase:
            return nice_99
        
        # Otherwise, check tiers but prefer .99 endings in tiers
        best_99_tier = None
        best_99_increase = float('inf')
        best_regular_tier = None
        best_regular_increase = float('inf')
        
        for tier in tiers:
            if tier > price:  # Must be strictly greater
                increase = tier - price
                if increase <= max_increase:
                    # Check if tier ends in .99 or .9
                    tier_rounded = round(tier, 2)
                    tier_decimal = tier_rounded - int(tier_rounded)
                    is_tier_99 = abs(tier_decimal - 0.99) < 0.01 or abs(tier_decimal - 0.9) < 0.01
                    
                    if is_tier_99 and increase < best_99_increase:
                        best_99_tier = tier
                        best_99_increase = increase
                    elif not is_tier_99 and increase < best_regular_increase:
                        best_regular_tier = tier
                        best_regular_increase = increase
        
        # Prefer .99 tier if available
        if best_99_tier is not None:
            return round(best_99_tier, 2)
        
        # Otherwise use regular tier if available
        if best_regular_tier is not None:
            return round(best_regular_tier, 2)
        
        # Fallback: use the nice number we created (ensure it's > price)
        if nice_99 <= price:
            nice_99 = price + min(0.01, max_increase)
        return nice_99
    
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

