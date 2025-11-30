# Google Sheets Template Structure

This document describes the structure of the Google Sheets that the Currency Conversion System uses.

## Overview

The system uses a single Google Sheet with three tabs:
1. **Config** - Manual input of SKUs and USD prices
2. **Price Matrix** - Auto-generated price matrix for all countries
3. **Exchange Rates Log** - Historical exchange rate tracking

## Sheet 1: Config

**Purpose**: Manual input of SKU information

**Columns** (Row 1 is header):
- `AppleStoreSku` (Column A) - Apple App Store SKU identifier
- `GooglePlaySku` (Column B) - Google Play Store SKU identifier  
- `Cost` (Column C) - USD base price (e.g., "1.99", "4.99")

**Important Notes**:
- Only SKUs matching the pattern `com.peerplay.mergecruise.credit*` will be processed
- SKUs not matching this pattern will be ignored
- Cost should be in USD format (e.g., "1.99" not "$1.99")
- Do not include header row in the data

**Example Data**:
```
AppleStoreSku	GooglePlaySku	Cost
com.peerplay.mergecruise.credits99	com.peerplay.mergecruise.credits99	0.99
com.peerplay.mergecruise.credits199	com.peerplay.mergecruise.credits199	1.99
com.peerplay.mergecruise.credits299	com.peerplay.mergecruise.credits299	2.99
com.peerplay.mergecruise.credits499	com.peerplay.mergecruise.credits499	4.99
com.peerplay.mergecruise.credits999	com.peerplay.mergecruise.credits999	9.99
com.peerplay.mergecruise.credits1999	com.peerplay.mergecruise.credits1999	19.99
com.peerplay.mergecruise.credits4999	com.peerplay.mergecruise.credits4999	49.99
com.peerplay.mergecruise.credits9999	com.peerplay.mergecruise.credits9999	99.99
com.peerplay.mergecruise.credits200000	com.peerplay.mergecruise.credits200000	199.99
```

## Sheet 2: Price Matrix

**Purpose**: Auto-generated price matrix (DO NOT EDIT MANUALLY)

**Columns** (Row 1 is header):
- `Country` (Column A) - ISO country code (e.g., "US", "GB", "DE")
- `Country_Name` (Column B) - Full country name (e.g., "United States", "Germany")
- `Currency` (Column C) - Currency code (e.g., "USD", "GBP", "EUR")
- `Price_Tier` (Column D) - Original USD base price tier (e.g., 0.99, 1.99, 4.99)
- `AppleStoreSku` (Column E) - Apple App Store SKU
- `GooglePlaySku` (Column F) - Google Play Store SKU
- `Local_Price` (Column G) - Raw conversion price in local currency (USD × current exchange_rate)
- `User_Pays` (Column H) - Final price user will pay (Apple's price from CSV, or snapped tier if Apple price < Local_Price)
- `Stash_Price` (Column I) - Price to send to Stash (pre-tax for US/CA/BR, VAT-inclusive for Europe)
- `VAT_Rate` (Column J) - VAT/GST rate as percentage (e.g., "19.0" for 19%)
- `VAT_Amount` (Column J) - VAT/GST amount in local currency
- `Gross_USD` (Column L) - Gross revenue in USD (formatted as currency)
- `Stash_Fee_USD` (Column M) - Stash processing fee in USD (0% for first year, formatted as currency)
- `Net_USD` (Column N) - Net revenue in USD after taxes and fees (formatted as currency)
- `Net_vs_Apple` (Column O) - Percentage difference vs Apple's net revenue (e.g., "+15.2%")

**Notes**:
- This sheet is completely overwritten on each run
- Data is sorted by Country, then by SKU Cost
- One row per country-SKU combination
- **Price Stability**: Prices only update if change > 5% or beneficial (prevents frequent changes)
- **Apple Pricing**: Uses Apple's official pricing tiers from their CSV (ensures prices match Apple's stores)
- **User_Pays >= Local_Price**: Always ensures User_Pays is never lower than raw conversion
- **Price_Tier**: Shows the original USD base price for reference
- **Stash_Price**: Calculated based on Stash's regional tax rules (see STASH_PRICE_VERIFICATION.md)

## Sheet 3: Exchange Rates Log

**Purpose**: Historical tracking of exchange rates

**Columns** (Row 1 is header):
- `Date` (Column A) - Date in YYYY-MM-DD format
- `Currency` (Column B) - Currency code (e.g., "USD", "EUR", "GBP")
- `Country` (Column C) - Country name associated with the currency
- `Rate` (Column D) - Exchange rate from USD to currency
- `Source` (Column E) - Source of the rate (e.g., "exchangerate-api.com")

**Notes**:
- Latest rates overwrite the fixed range A1:E1661 (keeps only current rates)
- Useful for auditing and tracking current exchange rates
- Previous rates are not kept (only latest snapshot)

## Setup Instructions

1. Create a new Google Sheet
2. Rename the first sheet to "Config"
3. Add the header row: `AppleStoreSku`, `GooglePlaySku`, `Cost`
4. Add your SKU data starting from row 2
5. Create two additional sheets: "Price Matrix" and "Exchange Rates Log"
6. Add headers to "Price Matrix" sheet (see columns above)
7. Add headers to "Exchange Rates Log" sheet: `Date`, `Currency`, `Country`, `Rate`, `Source`
8. Share the sheet with your Google Service Account email (see API_KEYS.md)
9. Copy the Sheet ID from the URL (the long string between `/d/` and `/edit`)
10. Set the `GOOGLE_SHEETS_ID` environment variable in your Cloud Function

## Sheet ID Location

The Sheet ID is found in the Google Sheets URL:
```
https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
```

Copy the `SHEET_ID_HERE` part and use it as your `GOOGLE_SHEETS_ID`.

