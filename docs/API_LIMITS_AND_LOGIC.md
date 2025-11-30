# API Limits, Update Frequency & System Logic

## Update Frequency

### Current Configuration
- **Schedule**: Twice daily at 00:00 UTC (midnight) and 12:00 UTC (noon)
- **Trigger**: Cloud Scheduler (automated)
- **Manual Trigger**: Available anytime via HTTP call
- **Price Stability**: Prices only update if change > 5% or beneficial (prevents frequent changes)

### How to Change Update Frequency

Edit `deployment/scheduler.yaml`:
```yaml
schedule: "0 0,12 * * *"  # Cron expression (twice daily)
```

**Common Schedule Examples:**
- `"0 0,12 * * *"` - Twice daily at midnight and noon UTC (current)
- `"0 0 * * *"` - Daily at midnight UTC
- `"0 */6 * * *"` - Every 6 hours
- `"0 0 * * 1"` - Every Monday at midnight
- `"*/30 * * * *"` - Every 30 minutes
- `"0 9 * * *"` - Daily at 9:00 AM UTC

To update the schedule:
```bash
gcloud scheduler jobs update http currency-conversion-daily \
    --location=us-central1 \
    --schedule="YOUR_CRON_EXPRESSION"
```

## API Limits & Costs

### 1. Exchange Rate API (exchangerate-api.com)

**Free Tier:**
- **Rate Limit**: 1,500 requests/month
- **Update Frequency**: Rates update once per day
- **Cost**: $0/month

**Current Usage:**
- 2 requests per day = ~60 requests/month
- **Well within free tier limits**

**If you exceed limits:**
- The function will use cached rates from the last successful fetch
- Error will be logged but won't break the system

### 2. Google Sheets API

**Free Tier:**
- **Rate Limit**: 
  - Read requests: 500 requests per 100 seconds per user
  - Write requests: 100 requests per 100 seconds per user
- **Quota**: 1,000,000 requests/day (free tier)
- **Cost**: $0/month

**Current Usage:**
- 1 read (Config sheet): ~1 request
- 1 read (Price Matrix for stability check): ~1 request
- 1 write (Price Matrix): ~1 request (batch write)
- 1 write (Exchange Rates Log): ~1 request (batch write)
- **Total per run: ~4 requests**
- **Daily: 8 requests/day (2 runs) = ~240 requests/month**

**Well within free tier limits**

### 3. Google Cloud Functions

**Free Tier (Gen 2):**
- **Invocations**: 2 million/month (free)
- **Compute Time**: 400,000 GB-seconds/month (free)
- **Networking**: 5 GB egress/month (free)
- **Cost**: $0/month (within free tier)

**Current Usage:**
- 2 invocations per day = ~60 invocations/month
- Average execution: ~30-60 seconds
- Memory: 512MB
- **Estimated cost: $0/month**

### 4. Cloud Scheduler

**Free Tier:**
- **Jobs**: 3 jobs (free)
- **Cost**: $0/month

**Current Usage:**
- 1 job (currency-conversion-daily)
- **Cost: $0/month**

## Complete System Logic Flow

### Step-by-Step Execution

```
1. TRIGGER
   └─> Cloud Scheduler (00:00 UTC and 12:00 UTC daily)
       OR Manual HTTP call

2. CLOUD FUNCTION STARTS
   └─> main.py: currency_conversion_handler()
       ├─> Initialize clients
       │   ├─> ExchangeRateClient
       │   └─> SheetsClient
       └─> PriceConverter

3. LOAD CONFIGURATION
   └─> sheets_client.read_config_sheet()
       ├─> Reads "Config" sheet from Google Sheets
       ├─> Filters SKUs matching: com.peerplay.mergecruise.credit*
       └─> Returns: List of SKUs with AppleStoreSku, GooglePlaySku, Cost

4. FETCH EXCHANGE RATES
   └─> exchange_client.fetch_rates()
       ├─> Calls: https://api.exchangerate-api.com/v4/latest/USD
       ├─> Gets rates for all currencies
       ├─> Caches rates for the day
       └─> Returns: Dictionary of currency → rate

5. PROCESS EACH SKU FOR EACH COUNTRY
   └─> For each SKU:
       └─> For each country:
           └─> price_converter.convert_sku_for_country()
               
               Step 5a: CONVERT USD TO LOCAL CURRENCY
               ├─> usd_price × exchange_rate = local_price_raw
               
               Step 5b: SNAP TO PRICE TIER
               ├─> tier_snapper.snap_to_tier(local_price_raw, currency)
               ├─> Finds nearest tier (or up/down based on config)
               └─> Returns: local_price (snapped)
               
               Step 5c: CALCULATE TAX (VAT/GST)
               ├─> tax_calculator.get_tax_rate(country_code)
               ├─> tax_calculator.calculate_tax(local_price, country_code)
               │   ├─> If VAT-inclusive: net = price / (1 + vat_rate)
               │   └─> If VAT-exclusive: net = price
               └─> Returns: vat_amount, net_before_fees
               
               Step 5d: CALCULATE STASH FEES
               ├─> stash_fee = net_before_fees × STASH_FEE_PERCENT + STASH_FIXED_FEE
               ├─> Currently: 0% (first year)
               └─> net_revenue_local = net_before_fees - stash_fee
               
               Step 5e: CONVERT BACK TO USD
               ├─> gross_usd = local_price / exchange_rate
               ├─> stash_fee_usd = stash_fee_local / exchange_rate
               └─> net_usd = net_revenue_local / exchange_rate
               
               Step 5f: CALCULATE APPLE COMPARISON
               ├─> apple_net = gross_usd × (1 - 0.30)  # 30% Apple fee
               ├─> net_vs_apple = ((net_usd - apple_net) / apple_net) × 100
               └─> Format: "+42.9%" or "-5.2%"
               
               Step 5g: GET COUNTRY NAME
               └─> country_names.get_country_name(country_code)
               
               Step 5h: CALCULATE USER PAYS
               ├─> If VAT-inclusive: user_pays = local_price
               └─> If VAT-exclusive: user_pays = local_price + vat_amount
               
               Returns: Complete price data dictionary

6. APPLY PRICE STABILITY
   └─> price_stability.apply_price_stability(price_data, existing_prices)
       ├─> Reads existing User_Pays prices from sheet
       ├─> Compares new prices with existing
       ├─> Keeps prices stable if change < 5% (unless beneficial decrease)
       └─> Updates prices if change > 5% or price decreased

7. WRITE RESULTS TO GOOGLE SHEETS
   └─> sheets_client.write_price_matrix(stable_price_data)
       ├─> Clears existing "Price Matrix" sheet
       ├─> Writes headers + all price data
       └─> One row per country-SKU combination

8. LOG EXCHANGE RATES
   └─> sheets_client.log_exchange_rates(rates, date)
       ├─> Overwrites fixed range A1:E1661 with latest rates
       └─> Historical tracking (latest rates only)

9. RETURN SUCCESS
   └─> Returns JSON response with count, date, and stability stats
```

## Data Flow Example

### Example: SKU `credits7999` ($79.99) for United States

```
Input:
  SKU: com.peerplay.mergecruise.credits7999
  USD Price: $79.99
  Country: US
  Currency: USD

Step 1: Convert USD → USD
  local_price_raw = $79.99 × 1.0 = $79.99

Step 2: Snap to Tier (with .99 preference)
  Tiers: [0.99, 1.99, ..., 79.99, ...]
  local_price_raw = $79.99
  visibility_price = $79.99 (exact match, prefers .99 endings)

Step 3: Calculate Tax
  VAT Rate: 0% (US)
  VAT Amount: $0.00
  net_before_fees = $79.99

Step 4: Calculate Stash Fees
  Stash Fee: 0% (first year)
  stash_fee = $0.00
  net_revenue_local = $79.99

Step 5: Convert to USD
  gross_usd = $79.99
  stash_fee_usd = $0.00
  net_usd = $79.99

Step 6: Apple Comparison
  apple_net = $79.99 × 0.70 = $55.99
  net_vs_apple = (($79.99 - $55.99) / $55.99) × 100 = +42.9%

Step 7: User Pays
  user_pays = $79.99 (no VAT in US)

Output Row:
  Country: US
  Country_Name: United States
  Currency: USD
  Price_Tier: 79.99
  AppleStoreSku: com.peerplay.mergecruise.credits7999
  GooglePlaySku: com.peerplay.mergecruise.credits7999
  Local_Price: 79.99
  User_Pays: 79.99
  VAT_Rate: 0.0
  VAT_Amount: 0.00
  Gross_USD: 79.99
  Stash_Fee_USD: 0.00
  Net_USD: 79.99
  Net_vs_Apple: +42.9%
```

### Example: Same SKU for Germany (VAT-inclusive)

```
Input:
  SKU: com.peerplay.mergecruise.credits7999
  USD Price: $79.99
  Country: DE
  Currency: EUR
  Exchange Rate: 0.92 (example)

Step 1: Convert USD → EUR
  local_price_raw = $79.99 × 0.92 = €73.59

Step 2: Snap to Tier (with .99 preference)
  Tiers: [0.99, 1.99, ..., 79.99, ...]
  local_price_raw = €73.59
  visibility_price = €73.99 (snapped to .99 ending, within 2-unit limit)

Step 3: Calculate Tax (VAT-inclusive)
  VAT Rate: 19% (Germany)
  net_before_fees = €79.99 / 1.19 = €67.22
  VAT Amount = €79.99 - €67.22 = €12.77

Step 4: Calculate Stash Fees
  stash_fee = €67.22 × 0% = €0.00
  net_revenue_local = €67.22

Step 5: Convert to USD
  gross_usd = €79.99 / 0.92 = $86.95
  stash_fee_usd = $0.00
  net_usd = €67.22 / 0.92 = $73.07

Step 6: Apple Comparison
  apple_net = $86.95 × 0.70 = $60.87
  net_vs_apple = (($73.07 - $60.87) / $60.87) × 100 = +20.0%

Step 7: User Pays
  user_pays = €79.99 (VAT included in price)

Output Row:
  Country: DE
  Country_Name: Germany
  Currency: EUR
  Price_Tier: 79.99
  Local_Price: 73.59
  User_Pays: 73.99
  VAT_Rate: 19.0
  VAT_Amount: 12.77
  Gross_USD: 86.95
  Stash_Fee_USD: 0.00
  Net_USD: 73.07
  Net_vs_Apple: +20.0%
```

## Performance & Scalability

### Current Scale
- **SKUs**: 61 unique SKUs
- **Countries**: ~60 countries
- **Total Combinations**: 61 × 60 = 3,660 rows
- **Execution Time**: ~30-60 seconds
- **Memory Usage**: 512MB

### If You Add More SKUs/Countries
- **100 SKUs × 100 countries** = 10,000 rows
- **Estimated time**: ~2-3 minutes
- **Still within free tiers**

### Optimization Options
1. **Batch Processing**: Process in chunks if needed
2. **Parallel Processing**: Use Cloud Tasks for parallel execution
3. **Caching**: Cache exchange rates (already implemented)
4. **Incremental Updates**: Only update changed SKUs (future enhancement)

## Error Handling

### Exchange Rate API Failure
- Uses cached rates from last successful fetch
- Logs warning but continues execution
- Won't break the system

### Google Sheets API Failure
- Retries automatically (built into Google API client)
- Logs error and returns 500 status
- Cloud Scheduler will retry (3 attempts by default)

### Missing SKU Data
- Skips invalid SKUs
- Logs warning
- Continues with valid SKUs

## Monitoring

### View Logs
```bash
gcloud functions logs read currency-conversion \
    --gen2 \
    --region=us-central1 \
    --limit=50
```

### Check Execution History
```bash
gcloud scheduler jobs describe currency-conversion-daily \
    --location=us-central1
```

### Monitor Costs
- GCP Console → Billing → Reports
- Filter by service: Cloud Functions, Cloud Scheduler
- Current estimate: $0/month (within free tiers)

## Summary

**Update Frequency**: Daily at 00:00 UTC (configurable)

**API Limits** (all well within free tiers):
- Exchange Rate API: 1,500/month (using ~30/month)
- Google Sheets API: 1M/day (using ~3/day)
- Cloud Functions: 2M invocations/month (using ~30/month)
- Cloud Scheduler: 3 jobs free (using 1)

**Total Cost**: $0/month (within free tiers)

**System Logic**: 
1. Load SKUs → 2. Fetch rates → 3. Convert → 4. Snap → 5. Tax → 6. Fees → 7. Compare → 8. Write results

**Scalability**: Can handle 10,000+ rows easily within free tiers

