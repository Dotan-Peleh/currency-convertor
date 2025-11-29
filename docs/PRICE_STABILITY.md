# Price Stability & Twice-Daily Updates

## Overview

The system now updates prices **twice per day** (at 12:00 UTC and 24:00 UTC) and includes **price stability logic** to prevent frequent price changes that could confuse customers.

## Update Schedule

### Current Configuration
- **Schedule**: Twice daily at **00:00 UTC** (midnight) and **12:00 UTC** (noon)
- **Cron Expression**: `0 0,12 * * *`
- **Time Zone**: UTC

### How to Update the Scheduler

**Option 1: Using the script**
```bash
cd scripts
./update_scheduler.sh
```

**Option 2: Manual update**
```bash
gcloud scheduler jobs update http currency-conversion-daily \
    --location=us-central1 \
    --schedule="0 0,12 * * *" \
    --time-zone="UTC"
```

## Price Stability Logic

### Purpose
Prevents frequent price changes that could confuse customers or make pricing appear unstable.

### Rules

1. **First Time**: Always set the price (no existing price to compare)

2. **Price Decreases**: Always update (beneficial to customer)
   - Example: €4.99 → €4.79 ✅ Update

3. **Price Increases (Small)**: Keep existing price (stability)
   - Example: €4.99 → €5.02 (0.6% increase) ❌ Keep €4.99
   - Threshold: Changes < 5% are considered "small"

4. **Price Increases (Significant)**: Update (necessary change)
   - Example: €4.99 → €5.25 (5.2% increase) ✅ Update
   - Threshold: Changes > 5% are considered "significant"

### Configuration

The threshold is configurable in `cloud-function/config.py`:
```python
PRICE_CHANGE_THRESHOLD = 0.05  # 5% - only update prices if change is more than this
```

### How It Works

1. **Before updating prices**: System reads existing `User_Pays` prices from the Price Matrix sheet
2. **For each new price**: Compares with existing price
3. **Decision**: 
   - If price should be stable → Keeps existing `User_Pays` price
   - If price should update → Uses new calculated `User_Pays` price
4. **Logging**: Reports how many prices were kept stable vs updated

### Example Scenarios

**Scenario 1: Small Exchange Rate Fluctuation**
- Existing: €4.99
- New (exchange rate up 1%): €5.02
- Result: Keep €4.99 (change is only 0.6%, below 5% threshold)

**Scenario 2: Significant Exchange Rate Change**
- Existing: €4.99
- New (exchange rate up 6%): €5.29
- Result: Update to €5.29 (change is 6%, above 5% threshold)

**Scenario 3: Exchange Rate Decreases**
- Existing: €4.99
- New (exchange rate down 2%): €4.89
- Result: Update to €4.89 (always update when price decreases - beneficial)

## Benefits

1. **Customer Experience**: Prices don't change every few hours due to minor exchange rate fluctuations
2. **Stability**: Customers see consistent pricing throughout the day
3. **Flexibility**: Prices still update when changes are significant or beneficial
4. **Transparency**: System logs which prices were kept stable and why

## Monitoring

Check the Cloud Function logs to see price stability in action:
```
Price stability: 3200 prices kept stable, 460 prices updated
```

This shows:
- How many prices remained stable (small changes ignored)
- How many prices were updated (significant changes or decreases)

## Technical Details

### Files Modified
- `cloud-function/main.py` - Added price stability check before writing
- `cloud-function/price_stability.py` - New module with stability logic
- `cloud-function/sheets_client.py` - Added `read_price_matrix()` method
- `cloud-function/config.py` - Added `PRICE_CHANGE_THRESHOLD` configuration
- `deployment/scheduler.yaml` - Updated cron schedule

### Price Stability Module

The `price_stability.py` module contains:
- `should_update_price()` - Determines if a price should be updated
- `apply_price_stability()` - Applies stability rules to price data

### Reading Existing Prices

The system reads existing `User_Pays` prices from the Price Matrix sheet before calculating new prices. This allows comparison and stability decisions.

## Future Enhancements

Potential improvements:
- Configurable threshold per currency
- Time-based stability (e.g., lock prices for 24 hours)
- Price change history tracking
- Alert when many prices change significantly

