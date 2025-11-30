# Quick Start Guide

Get the Currency Conversion System running in 5 steps!

## Step 1: Create Google Sheet

1. Run the template generator:
   ```bash
   python3 scripts/create_sheet_template.py
   ```

2. Go to [Google Sheets](https://sheets.google.com) and create a new sheet

3. Create 3 sheets (tabs) named exactly:
   - `Config`
   - `Price Matrix`
   - `Exchange Rates Log`

4. Import the CSV files:
   - Import `config_sheet.csv` into the `Config` sheet
   - Import `price_matrix_headers.csv` into the `Price Matrix` sheet
   - Import `exchange_rates_headers.csv` into the `Exchange Rates Log` sheet

5. Copy the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit
   ```

## Step 2: Set Up Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select or create a project
3. Go to **IAM & Admin** > **Service Accounts**
4. Click **Create Service Account**
5. Name it: `currency-conversion-service`
6. Click **Create and Continue**, then **Done**
7. Click on the service account > **Keys** tab
8. Click **Add Key** > **Create new key** > **JSON**
9. Save the downloaded JSON file (e.g., `service-account-key.json`)
10. Go to **APIs & Services** > **Library**
11. Search for "Google Sheets API" and **Enable** it
12. Go back to your Google Sheet and **Share** it with the service account email (from the JSON file, `client_email` field)
13. Give it **Editor** permissions

## Step 3: Set Up GCP Project

```bash
# Set your project ID
export GCP_PROJECT_ID="your-project-id"

# Configure gcloud
gcloud config set project $GCP_PROJECT_ID

# Enable billing (required for Cloud Functions)
# Do this in the Cloud Console: https://console.cloud.google.com/billing
```

## Step 4: Deploy to GCP

```bash
# Set environment variables
export GOOGLE_SHEETS_ID="your-sheet-id-from-step-1"
export GCP_REGION="us-central1"  # or your preferred region

# Deploy
./deployment/deploy.sh
```

The script will:
- Enable required APIs
- Deploy the Cloud Function
- Create the Cloud Scheduler job

## Step 5: Test It!

```bash
# Manually trigger the function
gcloud functions call currency-conversion --gen2 --region=us-central1

# Or check the logs
gcloud functions logs read currency-conversion --gen2 --region=us-central1 --limit=50

# Check your Google Sheet - the Price Matrix should be populated!
```

## Troubleshooting

### "Permission denied" error
- Make sure the service account email has Editor access to the Google Sheet
- Verify Google Sheets API is enabled

### "Sheet not found" error
- Check that the Sheet ID is correct
- Verify sheet names are exactly: "Config", "Price Matrix", "Exchange Rates Log"

### Function deployment fails
- Ensure billing is enabled
- Check that all required APIs are enabled
- Verify you have the necessary permissions

## What's Next?

- The system runs automatically twice daily at 12:00 and 24:00 UTC
- Uses Apple's official pricing tiers from their CSV (44 currencies, 600-800 tiers each)
- Prices are kept stable (only update if change > 5% or beneficial)
- **Local_Price**: Raw conversion (USD × exchange_rate)
- **User_Pays**: Apple's price (if >= Local_Price) or snapped tier (ensures User_Pays >= Local_Price)
- **Stash_Price**: Price to send to Stash (pre-tax for US/CA/BR, VAT-inclusive for Europe)
- Edit the Config sheet to add/remove SKUs
- View results in the Price Matrix sheet
- Check exchange rate history in Exchange Rates Log

For detailed documentation, see:
- [SETUP.md](docs/SETUP.md) - Complete setup guide
- [API_KEYS.md](docs/API_KEYS.md) - Credentials setup
- [GOOGLE_SHEETS_TEMPLATE.md](docs/GOOGLE_SHEETS_TEMPLATE.md) - Sheet structure

