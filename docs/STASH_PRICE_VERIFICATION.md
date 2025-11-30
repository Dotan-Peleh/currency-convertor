# Stash Price Verification Guide

This document explains how `User_Pays` and `Stash_Price` are calculated to ensure accuracy based on Stash guidelines.

## Stash Tax Handling Rules

According to Stash guidelines:

1. **US, Canada, Brazil**: Stash adds tax on top (pre-tax pricing)
   - We send: **PRE-TAX** price
   - Stash adds tax on top
   - User pays: Stash_Price + tax (added by Stash)

2. **Europe**: Prices are VAT inclusive
   - We send: **VAT-INCLUSIVE** price
   - Stash uses the price as-is
   - User pays: Stash_Price (VAT already included)

## Calculation Flow

### Step 1: Calculate Local_Price
```
Local_Price = USD_Price × Exchange_Rate
```
- Pure conversion from USD to local currency
- Based on latest exchange rates from Exchange Rates Log sheet

### Step 2: Calculate Visibility_Price (User_Pays base)
```
Visibility_Price = snap_to_tier(Local_Price, currency, mode="up")
```
- Always rounds UP to a "nice" number
- Ensures Visibility_Price > Local_Price

### Step 3: Calculate User_Pays (What User Actually Pays)

**For VAT-Inclusive Countries (EU, BR, etc.):**
```
User_Pays = Visibility_Price
```
- Price already includes VAT
- User sees and pays this exact amount

**For VAT-Exclusive Countries (US, CA):**
```
User_Pays = Visibility_Price + VAT_Amount
```
- Since VAT is 0% for digital goods in US/CA, User_Pays = Visibility_Price
- Tax is collected separately (if applicable)

### Step 4: Calculate Stash_Price (What We Send to Stash)

**For US, Canada, Brazil (Pre-tax):**
```
If country == 'BR':
    Stash_Price = User_Pays / (1 + VAT_Rate)
    # Example: 10.00 BRL / 1.17 = 8.55 BRL (removes 17% VAT)
Else:
    Stash_Price = User_Pays
    # US/CA: User_Pays is already pre-tax
```

**For Europe (VAT-inclusive):**
```
Stash_Price = User_Pays
# User_Pays already includes VAT, send as-is
```

## Examples

### Example 1: United States (US)
- **Price Tier**: $4.99 USD
- **Exchange Rate**: 1.0 (USD)
- **Local_Price**: $4.99 USD
- **Visibility_Price**: $4.99 USD (snapped)
- **VAT Rate**: 0%
- **VAT Amount**: $0.00
- **User_Pays**: $4.99 USD (no tax)
- **Stash_Price**: $4.99 USD (pre-tax, Stash adds tax on top)

### Example 2: Brazil (BR)
- **Price Tier**: $4.99 USD
- **Exchange Rate**: 5.0 (BRL per USD)
- **Local_Price**: 24.95 BRL
- **Visibility_Price**: 25.00 BRL (snapped up)
- **VAT Rate**: 17%
- **VAT Amount**: 3.63 BRL (included in price)
- **User_Pays**: 25.00 BRL (includes 17% VAT)
- **Stash_Price**: 21.37 BRL (pre-tax: 25.00 / 1.17)

### Example 3: Germany (DE)
- **Price Tier**: $4.99 USD
- **Exchange Rate**: 0.92 (EUR per USD)
- **Local_Price**: 4.59 EUR
- **Visibility_Price**: 4.99 EUR (snapped up)
- **VAT Rate**: 19%
- **VAT Amount**: 0.80 EUR (included in price)
- **User_Pays**: 4.99 EUR (includes 19% VAT)
- **Stash_Price**: 4.99 EUR (VAT-inclusive, Stash uses as-is)

### Example 4: United Kingdom (GB)
- **Price Tier**: $4.99 USD
- **Exchange Rate**: 0.79 (GBP per USD)
- **Local_Price**: 3.94 GBP
- **Visibility_Price**: 3.99 GBP (snapped up)
- **VAT Rate**: 20%
- **VAT Amount**: 0.67 GBP (included in price)
- **User_Pays**: 3.99 GBP (includes 20% VAT)
- **Stash_Price**: 3.99 GBP (VAT-inclusive, Stash uses as-is)

## Verification Checklist

✅ **User_Pays is always > Local_Price** (rounded up)
✅ **US/CA**: Stash_Price = User_Pays (pre-tax)
✅ **Brazil**: Stash_Price = User_Pays / 1.17 (removes VAT)
✅ **Europe**: Stash_Price = User_Pays (VAT-inclusive)
✅ **All calculations use latest exchange rates from Exchange Rates Log sheet**

## Column Definitions in Google Sheet

| Column | Description |
|--------|-------------|
| **Local_Price** | Pure conversion: USD × Exchange_Rate |
| **User_Pays** | What user actually pays (rounded up, includes VAT if applicable) |
| **Stash_Price** | Price to send to Stash (pre-tax for US/CA/BR, VAT-inclusive for Europe) |
| **VAT_Rate** | Tax rate as percentage |
| **VAT_Amount** | Tax amount in local currency |

## Running Verification

To verify prices are accurate, run:

```bash
python3 scripts/verify_stash_prices.py
```

This will:
1. Read sample prices from the Google Sheet
2. Verify Stash_Price calculations match expected values
3. Show breakdown for each country type

## Important Notes

1. **Exchange Rates**: Always uses the **latest** rates from the Exchange Rates Log sheet
2. **Price Stability**: Prices are kept stable to avoid frequent changes (5% threshold)
3. **Brazil Special Case**: Brazil is VAT-inclusive in our system, but Stash wants pre-tax, so we remove VAT
4. **US/Canada**: No VAT on digital goods, so User_Pays = Stash_Price

