# Currency Conversion System

A GCP-hosted system that converts USD base prices to all countries, applies tier snapping, calculates taxes, and outputs net revenue to Google Sheets.

## Overview

This system automatically:
- Converts USD base prices to local currencies using real-time exchange rates
- Snaps prices to appropriate tiers for each currency
- Calculates VAT/GST based on country-specific rules
- Applies Stash processing fees (0% for first year)
- Calculates net revenue and compares it to Apple/Google platform fees
- Outputs a complete price matrix to Google Sheets
- Runs daily via Cloud Scheduler

## Features

- **Multi-currency support**: Handles 50+ countries and currencies
- **Apple pricing tiers**: Uses Apple's official pricing tiers from their CSV (44 currencies, 600-800 tiers each)
- **Tax calculation**: VAT-inclusive/exclusive logic for different countries
- **Stash integration**: Calculates Stash_Price based on regional tax rules (pre-tax for US/CA/BR, VAT-inclusive for Europe)
- **Price stability**: Prevents frequent price changes (< 5% threshold)
- **Apple comparison**: Shows revenue advantage vs Apple's 30% fee
- **Automated**: Runs twice daily at 12:00 and 24:00 UTC
- **Cost-effective**: $0/month (within GCP free tiers)

## Architecture

```
Cloud Scheduler (Twice Daily: 12:00 & 24:00 UTC)
    ↓
Cloud Function (Python)
    ↓
    ├─→ Exchange Rate API (exchangerate-api.com)
    ├─→ Google Sheets (Read Config & Existing Prices)
    ├─→ Price Stability Check (Prevent Frequent Changes)
    └─→ Google Sheets (Write Results)
```

## Quick Start

1. **Set up Google Sheet** - Follow [docs/GOOGLE_SHEETS_TEMPLATE.md](docs/GOOGLE_SHEETS_TEMPLATE.md)
2. **Configure credentials** - Follow [docs/API_KEYS.md](docs/API_KEYS.md)
3. **Deploy to GCP** - Follow [docs/SETUP.md](docs/SETUP.md)

## Repository Structure

```
currency-convertor/
├── cloud-function/          # Cloud Function source code
│   ├── main.py             # Entry point
│   ├── config.py           # Configuration
│   ├── exchange_rates.py   # Exchange rate client
│   ├── price_converter.py  # Core conversion logic
│   ├── tier_snapper.py     # Price tier snapping
│   ├── tax_calculator.py   # VAT/GST calculation
│   ├── sheets_client.py    # Google Sheets API client
│   └── requirements.txt    # Python dependencies
├── deployment/              # Deployment scripts
│   ├── deploy.sh           # Deployment automation
│   └── scheduler.yaml      # Cloud Scheduler config
└── docs/                    # Documentation
    ├── SETUP.md            # Setup instructions
    ├── GOOGLE_SHEETS_TEMPLATE.md  # Sheet structure
    └── API_KEYS.md         # Credentials setup
```

## Configuration

### SKU Format

Only SKUs matching the pattern `com.peerplay.mergecruise.credit*` are processed.

Example SKUs:
- `com.peerplay.mergecruise.credits99` ($0.99)
- `com.peerplay.mergecruise.credits199` ($1.99)
- `com.peerplay.mergecruise.credits499` ($4.99)
- `com.peerplay.mergecruise.credits999` ($9.99)

### Stash Fees

Currently set to 0% for the first year. Update `cloud-function/config.py` to change:
```python
STASH_FEE_PERCENT = 0.0  # Change this when fees apply
STASH_FIXED_FEE = 0.0
```

### Pricing Logic

The system uses **Apple's official pricing tiers** from their pricing matrix CSV:

1. **Local_Price**: Raw conversion (USD × current exchange rate)
   - Example: $1.99 USD × 3.26 ILS/USD = 6.49 ILS

2. **User_Pays**: What the user actually pays
   - Uses Apple's exact price from CSV when available (e.g., 8.00 ILS for $1.99 USD)
   - If Apple price < Local_Price, snaps Local_Price to next tier (ensures User_Pays >= Local_Price)
   - Always >= Local_Price (never charges less than raw conversion)

3. **Stash_Price**: Price sent to Stash payment processor
   - US/Canada/Brazil: Pre-tax price (Stash adds tax on top)
   - Europe: VAT-inclusive price (same as User_Pays)

**Tier Snapping:**
- Uses Apple's official pricing tiers (44 currencies, 600-800 tiers each)
- Falls back to tier snapping for currencies not in Apple's CSV
- Configurable in `cloud-function/config.py`:
  ```python
  TIER_SNAPPING_MODE = "up"  # Options: "nearest", "up", "down"
  ```

### Price Stability

The system prevents frequent price changes to maintain customer trust:
- Prices only update if change is > 5% or beneficial (price decrease)
- Small fluctuations (< 5%) keep existing prices stable
- Configurable threshold in `cloud-function/config.py`:
  ```python
  PRICE_CHANGE_THRESHOLD = 0.05  # 5%
  ```

## Google Sheets Structure

### Sheet 1: Config (Manual Input)
- `AppleStoreSku` - Apple SKU identifier
- `GooglePlaySku` - Google Play SKU identifier
- `Cost` - USD base price

### Sheet 2: Price Matrix (Auto-generated)
- Country, Country_Name, Currency, Price_Tier, SKUs, Local_Price, User_Pays, Stash_Price, VAT, Fees, Net Revenue, vs Apple comparison

### Sheet 3: Exchange Rates Log (Auto-generated)
- Historical exchange rate tracking

See [docs/GOOGLE_SHEETS_TEMPLATE.md](docs/GOOGLE_SHEETS_TEMPLATE.md) for details.

## Deployment

```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GOOGLE_SHEETS_ID="your-sheet-id"

# Deploy
./deployment/deploy.sh
```

See [docs/SETUP.md](docs/SETUP.md) for complete instructions.

## Testing

### Local Testing
```bash
cd cloud-function
pip install -r requirements.txt
export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"
export GOOGLE_SHEETS_ID="your-sheet-id"
python main.py
```

### Cloud Testing
```bash
gcloud functions call currency-conversion --gen2 --region=us-central1
```

## Cost Estimate

- **Cloud Functions**: Free tier (2M invocations/month)
- **Cloud Scheduler**: Free tier (3 jobs)
- **Google Sheets API**: Free
- **Exchange Rate API**: Free tier available

**Total: $0/month** (within free tiers)

## Documentation

Complete documentation is available in the `docs/` directory:

- **[COMPLETE_SYSTEM_DOCUMENTATION.md](docs/COMPLETE_SYSTEM_DOCUMENTATION.md)** - Full system logic, formulas, and examples
- **[PRICE_STABILITY.md](docs/PRICE_STABILITY.md)** - Price stability and twice-daily updates
- **[API_LIMITS_AND_LOGIC.md](docs/API_LIMITS_AND_LOGIC.md)** - API limits, costs, and update frequency
- **[SETUP.md](docs/SETUP.md)** - Step-by-step setup instructions
- **[GOOGLE_SHEETS_TEMPLATE.md](docs/GOOGLE_SHEETS_TEMPLATE.md)** - Google Sheets structure guide
- **[API_KEYS.md](docs/API_KEYS.md)** - Credentials setup guide
- **[QUICK_START.md](QUICK_START.md)** - Quick start guide

## Support

For issues or questions:
1. Check the [docs/](docs/) directory
2. Review Cloud Function logs: `gcloud functions logs read currency-conversion --gen2 --region=us-central1`
3. Verify Google Sheet structure matches the template

## License

[Add your license here]

