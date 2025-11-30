"""
Core price conversion logic.
Uses Apple's exact pricing from their CSV for accurate pricing.
"""

import logging
import math
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import exchange_rates
import tier_snapper
import tax_calculator
import sheets_client
import country_names
import config

logger = logging.getLogger(__name__)

# Load Apple pricing map (USD tier -> {currency: customerPrice})
APPLE_PRICING_MAP: Dict[float, Dict[str, float]] = {}
PRICING_MAP_FILE = os.path.join(os.path.dirname(__file__), 'apple_pricing_map.json')

def _load_apple_pricing_map():
    """Load Apple pricing map from JSON file"""
    global APPLE_PRICING_MAP
    if APPLE_PRICING_MAP:
        return APPLE_PRICING_MAP
    
    try:
        if os.path.exists(PRICING_MAP_FILE):
            with open(PRICING_MAP_FILE, 'r') as f:
                data = json.load(f)
                # Convert string keys to float
                APPLE_PRICING_MAP = {float(k): {ck: float(cv) for ck, cv in v.items()} for k, v in data.items()}
                logger.info(f"Loaded Apple pricing map for {len(APPLE_PRICING_MAP)} USD tiers")
            return APPLE_PRICING_MAP
        else:
            logger.warning(f"Apple pricing map file not found: {PRICING_MAP_FILE}")
            return {}
    except Exception as e:
        logger.error(f"Error loading Apple pricing map: {e}")
        return {}

# Load pricing map on module import
_load_apple_pricing_map()


class PriceConverter:
    """Main price conversion orchestrator"""
    
    def __init__(self, sheets_client: sheets_client.SheetsClient, exchange_client: exchange_rates.ExchangeRateClient):
        """
        Initialize the price converter.
        
        Args:
            sheets_client: Google Sheets client
            exchange_client: Exchange rate client
        """
        self.sheets_client = sheets_client
        self.exchange_client = exchange_client
        
    def calculate_stash_fees(self, net_before_fees: float) -> float:
        """
        Calculate Stash processing fees.
        
        Args:
            net_before_fees: Net revenue before fees
            
        Returns:
            Stash fee amount
        """
        percentage_fee = net_before_fees * config.STASH_FEE_PERCENT
        fixed_fee = config.STASH_FIXED_FEE
        return percentage_fee + fixed_fee
    
    def calculate_apple_net(self, gross_usd: float, is_small_business: bool = False) -> float:
        """
        Calculate net revenue if sold through Apple.
        
        Args:
            gross_usd: Gross revenue in USD
            is_small_business: Whether Apple small business program applies (15% fee)
            
        Returns:
            Net revenue after Apple fees
        """
        fee_percent = 0.15 if is_small_business else config.APPLE_FEE_PERCENT
        return gross_usd * (1 - fee_percent)
    
    def convert_sku_for_country(
        self,
        sku: Dict[str, str],
        country_code: str,
        currency: str,
        exchange_rates_dict: Dict[str, float]
    ) -> Dict[str, any]:
        """
        Convert a single SKU price for a specific country.
        
        Args:
            sku: SKU dictionary with AppleStoreSku, GooglePlaySku, Cost
            country_code: ISO country code
            currency: Currency code
            exchange_rates_dict: Pre-fetched exchange rates
            
        Returns:
            Dictionary with all price information
        """
        try:
            usd_price = float(sku['Cost'])
            
            # Step 1: Always calculate raw conversion (Local_Price = pure USD × exchange_rate)
            # This represents the exact mathematical conversion without any rounding
            local_price_raw = self.exchange_client.convert_usd_to_currency(
                usd_price, currency, exchange_rates_dict
            )
            
            # Step 2: Get Apple's price for User_Pays (what user actually sees/pays)
            # This uses Apple's exact pricing from their CSV
            apple_price = None
            if APPLE_PRICING_MAP and usd_price in APPLE_PRICING_MAP:
                if currency in APPLE_PRICING_MAP[usd_price]:
                    apple_price = APPLE_PRICING_MAP[usd_price][currency]
                    logger.debug(f"Using Apple price for {currency}: {apple_price:.2f} (USD tier: {usd_price:.2f})")
            
            # Step 3: Determine visibility_price (what user will pay)
            # CRITICAL: User_Pays must ALWAYS be >= Local_Price (never lower)
            # This ensures we never charge less than the raw conversion
            if apple_price is not None:
                # Use Apple's price, but ensure it's not lower than raw conversion
                # Apple prices are based on historical exchange rates, which may be lower than current rates
                if apple_price >= local_price_raw:
                    # Apple price is higher or equal - use it (matches Apple's pricing)
                    visibility_price = apple_price
                else:
                    # Apple price is lower than raw conversion - snap raw price to tier instead
                    # This ensures we never charge less than the current exchange rate
                    visibility_price = tier_snapper.snap_to_tier(local_price_raw, currency, mode="up")
                    logger.debug(
                        f"Apple price {apple_price:.2f} {currency} < Local_Price {local_price_raw:.2f} {currency} "
                        f"for ${usd_price:.2f} USD tier. Using snapped tier: {visibility_price:.2f} {currency}"
                    )
            else:
                # Fallback: Snap raw price to tier with "up" mode
                visibility_price = tier_snapper.snap_to_tier(local_price_raw, currency, mode="up")
            
            # CRITICAL: Ensure visibility price is ALWAYS strictly greater than local_price_raw
            # If they're equal, round up by at least a small amount
            # (Only check if we didn't use Apple price, since Apple prices are already correct)
            if apple_price is None and visibility_price <= local_price_raw:
                # This shouldn't happen with "up" mode, but just in case
                logger.warning(
                    f"Visibility price {visibility_price} < raw price {local_price_raw} for {currency}. "
                    f"Adjusting to next tier."
                )
                # Find next tier above raw price
                tiers = tier_snapper.get_tiers_for_currency(currency, reference_price=local_price_raw)
                for tier in tiers:
                    if tier >= local_price_raw:
                        visibility_price = tier
                        break
                
                # If still not found or equal, generate a nice number above the raw price
                if visibility_price <= local_price_raw:
                    # Round up to next nice number based on magnitude
                    if local_price_raw < 1:
                        # Sub-unit: round up to next cent
                        visibility_price = math.ceil(local_price_raw * 100) / 100
                        if visibility_price <= local_price_raw:
                            visibility_price += 0.01
                    elif local_price_raw < 10:
                        # Single digits: round up to next integer
                        visibility_price = math.ceil(local_price_raw)
                        if visibility_price <= local_price_raw:
                            visibility_price += 1
                    elif local_price_raw < 100:
                        # Tens: round up to next integer
                        visibility_price = math.ceil(local_price_raw)
                        if visibility_price <= local_price_raw:
                            visibility_price += 1
                    elif local_price_raw < 1000:
                        # Hundreds: round up to next 5
                        visibility_price = math.ceil(local_price_raw / 5) * 5
                        if visibility_price <= local_price_raw:
                            visibility_price += 5
                    elif local_price_raw < 10000:
                        # Thousands: round up to next 10
                        visibility_price = math.ceil(local_price_raw / 10) * 10
                        if visibility_price <= local_price_raw:
                            visibility_price += 10
                    else:
                        # Tens of thousands+: round up to next 100
                        visibility_price = math.ceil(local_price_raw / 100) * 100
                        if visibility_price <= local_price_raw:
                            visibility_price += 100
            
            # Step 3: Calculate tax (based on visibility price - what user actually pays)
            vat_rate = tax_calculator.get_tax_rate(country_code)
            vat_amount, net_before_fees = tax_calculator.calculate_tax(visibility_price, country_code)
            
            # Step 4: Calculate Stash fees
            stash_fee_local = self.calculate_stash_fees(net_before_fees)
            net_revenue_local = net_before_fees - stash_fee_local
            
            # Step 5: Convert net revenue back to USD (based on visibility price - what user pays)
            gross_usd = self.exchange_client.convert_currency_to_usd(
                visibility_price, currency, exchange_rates_dict
            )
            stash_fee_usd = self.exchange_client.convert_currency_to_usd(
                stash_fee_local, currency, exchange_rates_dict
            )
            net_usd = self.exchange_client.convert_currency_to_usd(
                net_revenue_local, currency, exchange_rates_dict
            )
            
            # Step 6: Calculate Apple comparison
            apple_net = self.calculate_apple_net(gross_usd)
            net_vs_apple = ((net_usd - apple_net) / apple_net * 100) if apple_net > 0 else 0
            net_vs_apple_str = f"+{net_vs_apple:.1f}%" if net_vs_apple > 0 else f"{net_vs_apple:.1f}%"
            
            # Get country name
            country_name = country_names.get_country_name(country_code)
            
            # What user will pay (final price including VAT if applicable)
            # For VAT-inclusive countries, visibility_price already includes VAT
            # For VAT-exclusive countries, visibility_price is before tax, but user pays visibility_price + tax
            if tax_calculator.is_vat_inclusive(country_code):
                user_pays = visibility_price  # Price already includes VAT
            else:
                user_pays = visibility_price + vat_amount  # Price + tax
            
            # Calculate Stash_Price based on Stash tax handling rules
            # US, CA, BR: Send pre-tax price (Stash adds tax on top)
            # Europe: Send price with VAT included
            stash_price = tax_calculator.get_stash_price(user_pays, country_code)
            
            return {
                'Country': country_code,
                'Country_Name': country_name,
                'Currency': currency,
                'Price_Tier': round(usd_price, 2),  # USD base price tier (0.99, 1.99, etc.)
                'AppleStoreSku': sku['AppleStoreSku'],
                'GooglePlaySku': sku['GooglePlaySku'],
                'Local_Price': round(local_price_raw, 2),  # Raw conversion: USD * exchange_rate (pure conversion)
                'User_Pays': round(user_pays, 2),  # What user will pay (rounded up from Local_Price, including VAT)
                'Stash_Price': round(stash_price, 2),  # Price to send to Stash (pre-tax for US/CA/BR, VAT-inclusive for Europe)
                'VAT_Rate': round(vat_rate * 100, 1),  # As percentage
                'VAT_Amount': round(vat_amount, 2),
                'Gross_USD': round(gross_usd, 2),
                'Stash_Fee_USD': round(stash_fee_usd, 2),
                'Net_USD': round(net_usd, 2),  # What I will be left with
                'Net_vs_Apple': net_vs_apple_str
            }
            
        except Exception as e:
            logger.error(f"Error converting {sku['AppleStoreSku']} for {country_code}: {e}")
            return None
    
    def process_all_skus(self, country_currency_map: Dict[str, str]) -> List[Dict[str, any]]:
        """
        Process all SKUs for all countries.
        Fetches exchange rates from API.
        
        Args:
            country_currency_map: Dictionary mapping country codes to currency codes
            
        Returns:
            List of price data dictionaries
        """
        # Fetch exchange rates from API
        exchange_rates_dict, _ = self.exchange_client.fetch_rates()
        return self.process_all_skus_with_rates(country_currency_map, exchange_rates_dict)
    
    def process_all_skus_with_rates(self, country_currency_map: Dict[str, str], exchange_rates_dict: Dict[str, float]) -> List[Dict[str, any]]:
        """
        Process all SKUs for all countries using provided exchange rates.
        
        Args:
            country_currency_map: Dictionary mapping country codes to currency codes
            exchange_rates_dict: Pre-fetched exchange rates dictionary
            
        Returns:
            List of price data dictionaries
        """
        # Load SKUs from config
        skus = self.sheets_client.read_config_sheet()
        if not skus:
            logger.warning("No SKUs found in config sheet")
            return []
        
        # Process each SKU for each country
        price_data = []
        total_combinations = len(skus) * len(country_currency_map)
        processed = 0
        
        for sku in skus:
            for country_code, currency in country_currency_map.items():
                # Skip excluded countries
                if country_code in config.EXCLUDED_COUNTRIES:
                    continue
                
                result = self.convert_sku_for_country(
                    sku, country_code, currency, exchange_rates_dict
                )
                
                if result:
                    price_data.append(result)
                
                processed += 1
                if processed % 100 == 0:
                    logger.info(f"Processed {processed}/{total_combinations} combinations")
        
        logger.info(f"Completed processing {len(price_data)} price combinations")
        return price_data

