# Complete System Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Complete Logic Flow](#complete-logic-flow)
4. [Data Flow Examples](#data-flow-examples)
5. [API Limits & Costs](#api-limits--costs)
6. [Configuration](#configuration)
7. [Column Definitions](#column-definitions)
8. [Calculation Formulas](#calculation-formulas)
9. [Error Handling](#error-handling)
10. [Troubleshooting](#troubleshooting)

---

## System Overview

The Currency Conversion System is a GCP-hosted automated pricing engine that:

- Converts USD base prices to local currencies for 60+ countries
- Applies country-specific price tier snapping
- Calculates VAT/GST based on country tax rules
- Applies Stash processing fees (currently 0% for first year)
- Calculates net revenue and compares it to Apple/Google platform fees
- Outputs complete price matrix to Google Sheets
- Runs automatically twice daily via Cloud Scheduler (12:00 and 24:00 UTC)
- Implements price stability to prevent frequent changes
- Prioritizes .99 endings for better price presentation

**Key Benefits:**
- Automated daily updates with latest exchange rates
- Complete price transparency across all markets
- Revenue comparison vs Apple/Google platforms
- Zero cost operation (within GCP free tiers)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloud Scheduler                           │
│         (Twice Daily: 12:00 & 24:00 UTC)                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Cloud Function (Python)                    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Config     │  │   Exchange   │  │   Price     │       │
│  │   Loader     │  │   Rates API  │  │   Converter │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘       │
│         │                 │                 │              │
│         └─────────────────┴─────────────────┘              │
│                            │                                │
│                            ▼                                │
│  ┌──────────────────────────────────────────┐             │
│  │  For each SKU × Country:                  │             │
│  │  1. Convert USD → Local Currency          │             │
│  │  2. Snap to Price Tier                     │             │
│  │  3. Calculate VAT/GST                       │             │
│  │  4. Apply Stash Fees                        │             │
│  │  5. Convert Net → USD                      │             │
│  │  6. Calculate Apple Comparison              │             │
│  └──────────────────────────────────────────┘             │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Google Sheets                             │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Config    │  │ Price Matrix │  │ Exchange    │      │
│  │  (Input)     │  │  (Output)    │  │ Rates Log    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Complete Logic Flow

### Step 1: Trigger

**Automated:**
- Cloud Scheduler triggers twice daily at 00:00 UTC (midnight) and 12:00 UTC (noon)
- Sends HTTP GET request to Cloud Function
- Price stability logic prevents frequent price changes (< 5% threshold)

**Manual:**
- Can be triggered anytime via HTTP call:
  ```bash
  gcloud functions call currency-conversion --gen2 --region=us-central1
  ```

### Step 2: Initialize Components

```python
# Create clients
exchange_client = ExchangeRateClient()  # For fetching exchange rates
sheets = SheetsClient()                # For Google Sheets operations
converter = PriceConverter(sheets, exchange_client)  # Main conversion logic
```

### Step 3: Load Configuration

**Source:** Google Sheets "Config" tab

**Process:**
1. Read rows from "Config" sheet (columns A, B, C)
2. Filter SKUs matching pattern: `com.peerplay.mergecruise.credit*`
3. Extract: AppleStoreSku, GooglePlaySku, Cost (USD)

**Example Data:**
```
AppleStoreSku                              GooglePlaySku                             Cost
com.peerplay.mergecruise.credits199        com.peerplay.mergecruise.credits199        1.99
com.peerplay.mergecruise.credits499        com.peerplay.mergecruise.credits499        4.99
```

**Output:** List of 61 SKU dictionaries

### Step 4: Fetch Exchange Rates

**API:** exchangerate-api.com (free tier)

**Process:**
1. Call: `https://api.exchangerate-api.com/v4/latest/USD`
2. Receive: JSON with rates for all currencies
3. Cache: Rates cached for the day (prevents re-fetching)
4. Add: USD → USD rate = 1.0

**Example Response:**
```json
{
  "rates": {
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.50,
    "CAD": 1.35,
    ...
  }
}
```

**Output:** Dictionary mapping currency codes to exchange rates

### Step 5: Process Each SKU × Country Combination

For each of the 3,660 combinations (61 SKUs × 60 countries):

#### 5a. Convert USD to Local Currency

```python
local_price_raw = usd_price × exchange_rate
```

**Example:**
- USD Price: $4.99
- Exchange Rate (EUR): 0.92
- Raw Local Price: $4.99 × 0.92 = €4.59

#### 5b. Determine User_Pays Price

**Purpose:** Calculate what the user will actually pay using Apple's official pricing tiers

**Process:**
1. **Calculate Local_Price** (raw conversion):
   ```
   Local_Price = USD_Price × Current_Exchange_Rate
   ```

2. **Get Apple's Price** (if available):
   - Check `apple_pricing_map.json` for USD tier → currency price mapping
   - Example: $1.99 USD → 8.00 ILS (from Apple's CSV)

3. **Determine User_Pays**:
   - If Apple price >= Local_Price: Use Apple price (matches Apple's stores)
   - If Apple price < Local_Price: Snap Local_Price to next tier (ensures User_Pays >= Local_Price)
   - **Critical**: User_Pays is ALWAYS >= Local_Price (never charges less than raw conversion)

**Why This Matters:**
- Apple's CSV prices are based on historical exchange rates
- Current exchange rates may be higher, making Apple prices lower
- We ensure we never charge less than the current exchange rate

**Example (Israel, $1.99 USD tier):**
- Local_Price: 1.99 × 3.26 = 6.49 ILS (raw conversion)
- Apple Price: 8.00 ILS (from CSV)
- User_Pays: 8.00 ILS (Apple price is higher, so use it)

**Example (Japan, $9.99 USD tier):**
- Local_Price: 9.99 × 156.17 = 1,560.14 JPY (raw conversion)
- Apple Price: 1,310 JPY (from CSV, but lower than Local_Price)
- User_Pays: 1,570 JPY (snapped to next tier, ensures >= Local_Price)

**Tier Definitions:**
- Uses Apple's official pricing tiers from `apple_tiers.json` (44 currencies, 600-800 tiers each)
- Falls back to tier snapping for currencies not in Apple's CSV

#### 5c. Calculate VAT/GST

**Two Tax Systems:**

**1. VAT-Inclusive Countries (EU, UK, AU, etc.)**
- Display price **includes** VAT
- Customer sees: €4.99 (VAT already included)
- You receive: €4.99 / (1 + 0.19) = €4.19 (after VAT)

**Formula:**
```
net_before_fees = local_price / (1 + vat_rate)
vat_amount = local_price - net_before_fees
```

**Example (Germany, 19% VAT):**
- Display Price: €4.99
- VAT Rate: 19%
- Net Before Fees: €4.99 / 1.19 = €4.19
- VAT Amount: €4.99 - €4.19 = €0.80

**2. VAT-Exclusive Countries (US, CA)**
- Display price is **before** tax
- Customer pays: $4.99 + tax (collected separately)
- You receive: $4.99 (full amount)

**Formula:**
```
net_before_fees = local_price
vat_amount = local_price × vat_rate  (usually 0% for digital goods)
```

**Example (United States):**
- Display Price: $4.99
- VAT Rate: 0% (varies by state, but digital goods often exempt)
- Net Before Fees: $4.99
- VAT Amount: $0.00

**3. No VAT Countries (HK, Qatar, etc.)**
- No tax applied
- You receive full display price

#### 5d. Calculate Stash Fees

**Current Configuration:**
- Percentage Fee: 0% (first year)
- Fixed Fee: $0.00

**Formula:**
```
stash_fee = (net_before_fees × STASH_FEE_PERCENT) + STASH_FIXED_FEE
net_revenue_local = net_before_fees - stash_fee
```

**Example (Current - 0% fees):**
- Net Before Fees: €4.19
- Stash Fee: €4.19 × 0% + €0.00 = €0.00
- Net Revenue: €4.19 - €0.00 = €4.19

**Future (When fees apply - e.g., 5% + $0.10):**
- Net Before Fees: €4.19
- Stash Fee: (€4.19 × 5%) + €0.10 = €0.31
- Net Revenue: €4.19 - €0.31 = €3.88

#### 5e. Convert Net Revenue Back to USD

**Purpose:** Standardize all revenue to USD for comparison

**Formula:**
```
gross_usd = local_price / exchange_rate
stash_fee_usd = stash_fee_local / exchange_rate
net_usd = net_revenue_local / exchange_rate
```

**Example:**
- Local Price: €4.99
- Exchange Rate: 0.92
- Gross USD: €4.99 / 0.92 = $5.42

- Net Revenue Local: €4.19
- Net USD: €4.19 / 0.92 = $4.55

#### 5f. Calculate Apple Comparison

**Purpose:** Show revenue advantage vs selling through Apple

**Apple Fee Structure:**
- Standard: 30% commission
- Small Business Program: 15% commission (first $1M/year)

**Formula:**
```
apple_net = gross_usd × (1 - apple_fee_percent)
net_vs_apple = ((net_usd - apple_net) / apple_net) × 100
```

**Example:**
- Gross USD: $5.42
- Apple Net (30% fee): $5.42 × 0.70 = $3.79
- Your D2C Net: $4.55
- Advantage: (($4.55 - $3.79) / $3.79) × 100 = +20.1%

**Result:** "+20.1%" means you keep 20.1% MORE revenue than Apple

#### 5g. Get Country Name

**Purpose:** Human-readable country names instead of codes

**Mapping:**
- "US" → "United States"
- "GB" → "United Kingdom"
- "DE" → "Germany"
- etc.

#### 5h. Calculate User Pays and Stash Price

**Purpose:** Final price the customer will see/pay, and price to send to Stash

**User_Pays Formula:**
```
If VAT-inclusive:
  user_pays = visibility_price  (VAT already included in Apple price or tier)

If VAT-exclusive:
  user_pays = visibility_price + vat_amount  (price + tax)
```

**Stash_Price Formula:**
```
If country in STASH_PRE_TAX_COUNTRIES (US, CA, BR):
  If BR: stash_price = user_pays / (1 + vat_rate)  # Remove VAT
  Else: stash_price = user_pays  # Already pre-tax

If country in STASH_VAT_INCLUSIVE_COUNTRIES (Europe):
  stash_price = user_pays  # Send VAT-inclusive price
```

**Example (Germany - VAT-inclusive):**
- Local_Price: €1.83 (raw: $1.99 × 0.92)
- User_Pays: €1.99 (Apple price, includes 19% VAT)
- Stash_Price: €1.99 (VAT-inclusive for Europe)

**Example (US - VAT-exclusive):**
- Local_Price: $1.99 (raw: $1.99 × 1.0)
- User_Pays: $1.99 (Apple price, no VAT)
- Stash_Price: $1.99 (pre-tax for US)

**Example (Brazil - VAT-inclusive, pre-tax for Stash):**
- Local_Price: 10.65 BRL (raw: $1.99 × 5.35)
- User_Pays: 6.00 BRL (Apple price, includes 17% VAT)
- Stash_Price: 5.13 BRL (pre-tax: 6.00 / 1.17)

### Step 6: Write Results to Google Sheets

**Target:** "Price Matrix" sheet

**Process:**
1. Clear existing data in "Price Matrix" sheet
2. Write headers (13 columns)
3. Write all 3,660 rows (one per SKU×country combination)
4. Format: USER_ENTERED (Google Sheets interprets values)

**Columns Written:**
1. Country (code)
2. Country_Name (full name)
3. Currency
4. Price_Tier (USD base price: 0.99, 1.99, etc.)
5. AppleStoreSku
6. GooglePlaySku
7. Local_Price (raw conversion: USD × exchange_rate)
8. User_Pays (Apple price or snapped tier, always >= Local_Price)
9. Stash_Price (price to send to Stash, based on regional tax rules)
10. VAT_Rate
11. VAT_Amount
12. Gross_USD
13. Stash_Fee_USD
14. Net_USD
15. Net_vs_Apple

### Step 7: Log Exchange Rates

**Target:** "Exchange Rates Log" sheet

**Process:**
1. Append (don't overwrite) to "Exchange Rates Log"
2. One row per currency
3. Columns: Date, Currency, Rate, Source

**Purpose:** Historical tracking of exchange rate changes

---

## Data Flow Examples

### Example 1: United States (No VAT, No Fees)

**Input:**
- SKU: `credits7999`
- USD Price: $79.99
- Country: US
- Currency: USD

**Processing:**
```
1. Convert: $79.99 × 1.0 = $79.99
2. Snap: $79.99 (exact match)
3. Tax: 0% → Net = $79.99, VAT = $0.00
4. Stash Fee: 0% → Fee = $0.00, Net = $79.99
5. Convert: Gross = $79.99, Net = $79.99
6. Apple: $79.99 × 0.70 = $55.99
   Advantage: (($79.99 - $55.99) / $55.99) × 100 = +42.9%
7. User Pays: $79.99
```

**Output Row:**
```
US | United States | USD | credits7999 | credits7999 | 79.99 | 79.99 | 0.0 | 0.00 | 79.99 | 0.00 | 79.99 | +42.9%
```

### Example 2: Germany (VAT-Inclusive, 19%)

**Input:**
- SKU: `credits499`
- USD Price: $4.99
- Country: DE
- Currency: EUR
- Exchange Rate: 0.92

**Processing:**
```
1. Convert: $4.99 × 0.92 = €4.59
2. Snap: €4.59 → €4.99 (nearest tier)
3. Tax (VAT-inclusive): 
   Net = €4.99 / 1.19 = €4.19
   VAT = €4.99 - €4.19 = €0.80
4. Stash Fee: 0% → Fee = €0.00, Net = €4.19
5. Convert: 
   Gross = €4.99 / 0.92 = $5.42
   Net = €4.19 / 0.92 = $4.55
6. Apple: $5.42 × 0.70 = $3.79
   Advantage: (($4.55 - $3.79) / $3.79) × 100 = +20.1%
7. User Pays: €4.99 (VAT included)
```

**Output Row:**
```
DE | Germany | EUR | credits499 | credits499 | 4.99 | 4.99 | 19.0 | 0.80 | 5.42 | 0.00 | 4.55 | +20.1%
```

### Example 3: Japan (Consumption Tax, 10%)

**Input:**
- SKU: `credits999`
- USD Price: $9.99
- Country: JP
- Currency: JPY
- Exchange Rate: 149.50

**Processing:**
```
1. Convert: $9.99 × 149.50 = ¥1,494.01
2. Snap: ¥1,494.01 → ¥1,400 (nearest tier)
3. Tax (VAT-inclusive): 
   Net = ¥1,400 / 1.10 = ¥1,272.73
   VAT = ¥1,400 - ¥1,272.73 = ¥127.27
4. Stash Fee: 0% → Fee = ¥0.00, Net = ¥1,272.73
5. Convert: 
   Gross = ¥1,400 / 149.50 = $9.36
   Net = ¥1,272.73 / 149.50 = $8.51
6. Apple: $9.36 × 0.70 = $6.55
   Advantage: (($8.51 - $6.55) / $6.55) × 100 = +29.9%
7. User Pays: ¥1,400 (tax included)
```

**Output Row:**
```
JP | Japan | JPY | credits999 | credits999 | 1400 | 1400 | 10.0 | 127.27 | 9.36 | 0.00 | 8.51 | +29.9%
```

---

## API Limits & Costs

### Exchange Rate API (exchangerate-api.com)

**Free Tier:**
- Limit: 1,500 requests/month
- Current Usage: ~30 requests/month (1 per day)
- Status: ✅ Well within limits (2% of quota)
- Cost: $0/month

**Rate Updates:**
- API updates rates once per day
- Our system fetches once per day (optimal)
- Caching prevents unnecessary requests

### Google Sheets API

**Free Tier:**
- Read Limit: 500 requests per 100 seconds
- Write Limit: 100 requests per 100 seconds
- Daily Quota: 1,000,000 requests/day
- Current Usage: ~3 requests/day
- Status: ✅ Well within limits (0.0003% of quota)
- Cost: $0/month

**Request Breakdown:**
- 1 read: Config sheet
- 1 write: Price Matrix (batch write, all rows at once)
- 1 write: Exchange Rates Log (batch write, all rates at once)

### Google Cloud Functions (Gen 2)

**Free Tier:**
- Invocations: 2,000,000/month
- Compute: 400,000 GB-seconds/month
- Networking: 5 GB egress/month
- Current Usage: ~30 invocations/month
- Execution Time: ~30-60 seconds
- Memory: 512MB
- Status: ✅ Well within limits
- Cost: $0/month

**Calculation:**
- Invocations: 30/month = 0.0015% of quota
- Compute: 30 × 60s × 0.5GB = 900 GB-seconds = 0.225% of quota
- Networking: ~1MB per run = negligible

### Cloud Scheduler

**Free Tier:**
- Jobs: 3 jobs free
- Current Usage: 1 job
- Status: ✅ Well within limits
- Cost: $0/month

### Total Cost

**Current Monthly Cost: $0.00**

All services are within free tier limits. Even if usage increases 10x, you'd still be within free tiers.

---

## Configuration

### File: `cloud-function/config.py`

**Stash Fees:**
```python
STASH_FEE_PERCENT = 0.0  # 0% for first year
STASH_FIXED_FEE = 0.0    # No fixed fee
```

**Tier Snapping:**
```python
TIER_SNAPPING_MODE = "up"  # Options: "nearest", "up", "down"
```

**Apple Pricing Files:**
- `apple_tiers.json` - Apple's official pricing tiers (44 currencies, 600-800 tiers each)
- `apple_pricing_map.json` - USD tier → currency price mappings (657 USD tiers × 44 currencies)
- These files are generated from Apple's pricing matrix CSV

**Exchange Rate API:**
```python
EXCHANGE_RATE_API_BASE_URL = "https://api.exchangerate-api.com/v4/latest/USD"
```

**Google Sheets:**
```python
GOOGLE_SHEETS_CONFIG_SHEET = "Config"
GOOGLE_SHEETS_PRICE_MATRIX_SHEET = "Price Matrix"
GOOGLE_SHEETS_EXCHANGE_RATES_SHEET = "Exchange Rates Log"
```

**Apple/Google Fees:**
```python
APPLE_FEE_PERCENT = 0.30  # 30% standard, 15% for small business
GOOGLE_FEE_PERCENT = 0.30
```

**Country Exclusion:**
```python
EXCLUDED_COUNTRIES = [
    # Add country codes to exclude, e.g., "RU", "IR"
]
```

**SKU Filtering:**
```python
SKU_PATTERN = r"com\.peerplay\.mergecruise\.credit"
```

---

## Column Definitions

### Price Matrix Sheet Columns

| Column | Description | Example | Notes |
|--------|-------------|---------|-------|
| **Country** | ISO country code | `US`, `GB`, `DE` | 2-letter code |
| **Country_Name** | Full country name | `United States` | Human-readable |
| **Currency** | Currency code | `USD`, `EUR`, `GBP` | 3-letter code |
| **AppleStoreSku** | Apple SKU identifier | `com.peerplay.mergecruise.credits199` | From Config |
| **GooglePlaySku** | Google Play SKU | `com.peerplay.mergecruise.credits199` | From Config |
| **Local_Price** | Raw conversion price (USD × exchange_rate) | `6.49` | Pure mathematical conversion |
| **User_Pays** | Final price user will pay (Apple price or snapped tier) | `8.00` | Always >= Local_Price, includes VAT if applicable |
| **Stash_Price** | Price to send to Stash payment processor | `8.00` | Pre-tax for US/CA/BR, VAT-inclusive for Europe |
| **VAT_Rate** | VAT/GST rate as percentage | `19.0` | 0% for no-tax countries |
| **VAT_Amount** | VAT/GST amount in local currency | `0.80` | Tax portion of price |
| **Gross_USD** | Gross revenue in USD | `5.42` | Before any deductions |
| **Stash_Fee_USD** | Stash processing fee in USD | `0.00` | Currently 0% |
| **Net_USD** | Your net revenue in USD | `4.55` | After all fees and taxes |
| **Net_vs_Apple** | Revenue advantage vs Apple | `+20.1%` | Percentage more than Apple |

### Config Sheet Columns

| Column | Description | Example |
|--------|-------------|---------|
| **AppleStoreSku** | Apple App Store SKU | `com.peerplay.mergecruise.credits199` |
| **GooglePlaySku** | Google Play Store SKU | `com.peerplay.mergecruise.credits199` |
| **Cost** | USD base price | `1.99` |

### Exchange Rates Log Columns

| Column | Description | Example |
|--------|-------------|---------|
| **Date** | Date in YYYY-MM-DD format | `2025-11-28` |
| **Currency** | Currency code | `EUR` |
| **Rate** | Exchange rate from USD | `0.92` |
| **Source** | API source | `exchangerate-api.com` |

---

## Calculation Formulas

### 1. Currency Conversion

```
local_price_raw = usd_price × exchange_rate
```

### 2. Tier Snapping

```
Find tiers where: tier[i] ≤ price ≤ tier[i+1]

If mode = "nearest":
  snapped_price = closer of tier[i] or tier[i+1]

If mode = "up":
  snapped_price = tier[i+1]

If mode = "down":
  snapped_price = tier[i]
```

### 3. VAT Calculation (VAT-Inclusive)

```
net_before_fees = local_price / (1 + vat_rate)
vat_amount = local_price - net_before_fees
```

### 4. VAT Calculation (VAT-Exclusive)

```
net_before_fees = local_price
vat_amount = local_price × vat_rate
```

### 5. Stash Fees

```
stash_fee = (net_before_fees × STASH_FEE_PERCENT) + STASH_FIXED_FEE
net_revenue_local = net_before_fees - stash_fee
```

### 6. USD Conversion

```
gross_usd = local_price / exchange_rate
stash_fee_usd = stash_fee_local / exchange_rate
net_usd = net_revenue_local / exchange_rate
```

### 7. Apple Comparison

```
apple_net = gross_usd × (1 - APPLE_FEE_PERCENT)
net_vs_apple = ((net_usd - apple_net) / apple_net) × 100
```

### 8. User Pays

```
If VAT-inclusive:
  user_pays = local_price

If VAT-exclusive:
  user_pays = local_price + vat_amount
```

---

## Error Handling

### Exchange Rate API Failure

**Scenario:** API is down or rate limit exceeded

**Handling:**
1. Try to fetch rates
2. If fails, check for cached rates
3. Use most recent cached rates
4. Log warning but continue execution
5. System continues with cached data

**Code:**
```python
try:
    rates = fetch_rates()
except:
    if cache:
        rates = cache[latest_date]  # Use cached
        logger.warning("Using cached rates")
```

### Google Sheets API Failure

**Scenario:** Permission denied, sheet not found, API quota exceeded

**Handling:**
1. Google API client automatically retries (built-in)
2. If still fails, log error
3. Return 500 status code
4. Cloud Scheduler will retry (3 attempts)

**Retry Policy:**
- 3 automatic retries
- Exponential backoff: 5s → 3600s
- Max duration: 600 seconds

### Invalid SKU Data

**Scenario:** SKU doesn't match pattern or has invalid price

**Handling:**
1. Filter SKUs by pattern during load
2. Skip invalid rows
3. Log warning
4. Continue with valid SKUs

### Missing Exchange Rate

**Scenario:** Currency not found in exchange rate API response

**Handling:**
1. Use rate = 1.0 (assume same as USD)
2. Log warning
3. Continue processing

---

## Troubleshooting

### Issue: "Permission denied" error

**Cause:** Service account doesn't have access to Google Sheet

**Solution:**
1. Open Google Sheet
2. Click "Share"
3. Add: `currency-conversion-service@yotam-395120.iam.gserviceaccount.com`
4. Give "Editor" permissions
5. Click "Send"

### Issue: "Sheet not found" error

**Cause:** Sheet names don't match exactly

**Solution:**
- Verify sheet names are exactly:
  - "Config" (not "config" or "Config ")
  - "Price Matrix" (not "PriceMatrix")
  - "Exchange Rates Log" (not "ExchangeRatesLog")

### Issue: No data in Price Matrix

**Causes:**
1. Config sheet is empty
2. SKUs don't match pattern `com.peerplay.mergecruise.credit*`
3. All countries excluded

**Solution:**
1. Check Config sheet has data
2. Verify SKU format matches pattern
3. Check `EXCLUDED_COUNTRIES` in config.py

### Issue: Exchange rates not updating

**Causes:**
1. API is down
2. Network issues
3. Rate limit exceeded

**Solution:**
1. Check function logs
2. Verify API is accessible
3. Check if using cached rates (warning in logs)

### Issue: Function times out

**Cause:** Too many SKUs/countries

**Solution:**
1. Increase timeout in deploy script:
   ```bash
   --timeout=900s  # 15 minutes
   ```
2. Increase memory:
   ```bash
   --memory=1GB
   ```
3. Process in batches (future enhancement)

---

## Performance Metrics

### Current Performance

- **SKUs**: 61
- **Countries**: 60
- **Total Combinations**: 3,660
- **Execution Time**: 30-60 seconds
- **Memory Usage**: 512MB
- **API Calls per Run**: ~3 (1 read + 2 writes)

### Scalability

**Can Handle:**
- 100 SKUs × 100 countries = 10,000 rows
- Estimated time: 2-3 minutes
- Still within free tiers

**Optimization Options:**
1. Batch processing for very large datasets
2. Parallel processing using Cloud Tasks
3. Incremental updates (only changed SKUs)
4. Caching strategies

---

## Monitoring & Logs

### View Logs

```bash
gcloud functions logs read currency-conversion \
    --gen2 \
    --region=us-central1 \
    --limit=50
```

### Check Scheduler Status

```bash
gcloud scheduler jobs describe currency-conversion-daily \
    --location=us-central1
```

### Monitor Costs

GCP Console → Billing → Reports
- Filter by: Cloud Functions, Cloud Scheduler
- Current: $0/month

---

## Summary

The Currency Conversion System is a fully automated, cost-effective solution that:

✅ Runs daily at 00:00 UTC automatically
✅ Processes 3,660+ price combinations
✅ Updates Google Sheets with complete price matrix
✅ Tracks exchange rate history
✅ Compares revenue vs Apple/Google platforms
✅ Costs $0/month (within free tiers)
✅ Handles errors gracefully with retries and caching
✅ Scales to 10,000+ rows easily

**All logic is documented and the system is production-ready!**

