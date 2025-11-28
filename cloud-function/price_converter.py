"""
Core price conversion logic.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import exchange_rates
import tier_snapper
import tax_calculator
import sheets_client
import country_names
import config

logger = logging.getLogger(__name__)


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
            
            # Step 1: Convert USD to local currency
            local_price_raw = self.exchange_client.convert_usd_to_currency(
                usd_price, currency, exchange_rates_dict
            )
            
            # Step 2: Snap to nearest tier
            local_price = tier_snapper.snap_to_tier(local_price_raw, currency)
            
            # Step 3: Calculate tax
            vat_rate = tax_calculator.get_tax_rate(country_code)
            vat_amount, net_before_fees = tax_calculator.calculate_tax(local_price, country_code)
            
            # Step 4: Calculate Stash fees
            stash_fee_local = self.calculate_stash_fees(net_before_fees)
            net_revenue_local = net_before_fees - stash_fee_local
            
            # Step 5: Convert net revenue back to USD
            gross_usd = self.exchange_client.convert_currency_to_usd(
                local_price, currency, exchange_rates_dict
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
            # For VAT-inclusive countries, local_price already includes VAT
            # For VAT-exclusive countries, local_price is before tax, but user pays local_price + tax
            if tax_calculator.is_vat_inclusive(country_code):
                user_pays = local_price  # Price already includes VAT
            else:
                user_pays = local_price + vat_amount  # Price + tax
            
            return {
                'Country': country_code,
                'Country_Name': country_name,
                'Currency': currency,
                'AppleStoreSku': sku['AppleStoreSku'],
                'GooglePlaySku': sku['GooglePlaySku'],
                'Local_Price': round(local_price, 2),
                'User_Pays': round(user_pays, 2),  # What user will pay (final price)
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
        
        Args:
            country_currency_map: Dictionary mapping country codes to currency codes
            
        Returns:
            List of price data dictionaries
        """
        # Load SKUs from config
        skus = self.sheets_client.read_config_sheet()
        if not skus:
            logger.warning("No SKUs found in config sheet")
            return []
        
        # Fetch exchange rates
        exchange_rates_dict = self.exchange_client.fetch_rates()
        
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

