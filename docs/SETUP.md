# Setup Instructions

Complete setup guide for the Currency Conversion System.

## Prerequisites

- Google Cloud Platform (GCP) account with billing enabled
- Google Cloud SDK (gcloud) installed
- Python 3.11+ (for local testing)
- A Google Sheet (will be created during setup)

## Step 1: Clone Repository

```bash
git clone https://github.com/Dotan-Peleh/currency-convertor.git
cd currency-convertor
```

## Step 2: Set Up Google Cloud Project

1. Create a new GCP project or select an existing one
2. Enable billing (required for Cloud Functions)
3. Note your Project ID

```bash
export GCP_PROJECT_ID="your-project-id"
gcloud config set project $GCP_PROJECT_ID
```

## Step 3: Create Google Sheet

1. Create a new Google Sheet
2. Follow the structure in [GOOGLE_SHEETS_TEMPLATE.md](GOOGLE_SHEETS_TEMPLATE.md)
3. Add your SKU data to the Config sheet
4. Copy the Sheet ID from the URL
5. Set it as an environment variable:
   ```bash
   export GOOGLE_SHEETS_ID="your-sheet-id"
   ```

## Step 4: Set Up Service Account

1. Follow instructions in [API_KEYS.md](API_KEYS.md) to create a service account
2. Download the JSON key file
3. Share your Google Sheet with the service account email
4. Save the JSON file path for deployment

## Step 5: Configure Exchange Rate API (Optional)

The system works with the free tier of exchangerate-api.com without an API key. If you want better rate limits:

1. Sign up at [exchangerate-api.com](https://www.exchangerate-api.com/)
2. Get your API key
3. Set it as an environment variable:
   ```bash
   export EXCHANGE_RATE_API_KEY="your-api-key"
   ```

## Step 6: Deploy to GCP

1. Make the deployment script executable:
   ```bash
   chmod +x deployment/deploy.sh
   ```

2. Set required environment variables:
   ```bash
   export GCP_PROJECT_ID="your-project-id"
   export GCP_REGION="us-central1"  # or your preferred region
   export GOOGLE_SHEETS_ID="your-sheet-id"
   ```

3. Run the deployment script:
   ```bash
   ./deployment/deploy.sh
   ```

   Or deploy manually:
   ```bash
   cd cloud-function
   gcloud functions deploy currency-conversion \
       --gen2 \
       --runtime=python311 \
       --region=us-central1 \
       --source=. \
       --entry-point=main \
       --trigger-http \
       --allow-unauthenticated \
       --set-env-vars="GOOGLE_SHEETS_ID=$GOOGLE_SHEETS_ID"
   ```

## Step 7: Set Up Cloud Scheduler

The deployment script should create the scheduler job automatically. If not, create it manually:

```bash
FUNCTION_URL=$(gcloud functions describe currency-conversion \
    --gen2 \
    --region=us-central1 \
    --format="value(serviceConfig.uri)")

gcloud scheduler jobs create http currency-conversion-daily \
    --location=us-central1 \
    --schedule="0 0,12 * * *" \
    --uri="$FUNCTION_URL" \
    --http-method=GET \
    --time-zone="UTC"
```

## Step 8: Test the System

### Test Locally (Optional)

1. Install dependencies:
   ```bash
   cd cloud-function
   pip install -r requirements.txt
   ```

2. Set environment variables:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"
   export GOOGLE_SHEETS_ID="your-sheet-id"
   ```

3. Run the function:
   ```bash
   python main.py
   ```

### Test in Cloud

1. Manually trigger the Cloud Function:
   ```bash
   gcloud functions call currency-conversion \
       --gen2 \
       --region=us-central1
   ```

2. Or trigger via HTTP:
   ```bash
   FUNCTION_URL=$(gcloud functions describe currency-conversion \
       --gen2 \
       --region=us-central1 \
       --format="value(serviceConfig.uri)")
   curl $FUNCTION_URL
   ```

3. Check the logs:
   ```bash
   gcloud functions logs read currency-conversion \
       --gen2 \
       --region=us-central1 \
       --limit=50
   ```

## Step 9: Verify Results

1. Open your Google Sheet
2. Check the "Price Matrix" sheet - it should be populated with data
3. Check the "Exchange Rates Log" sheet - it should have today's rates
4. Verify the calculations make sense

## Troubleshooting

### Function fails to deploy
- Check that all required APIs are enabled
- Verify your billing is enabled
- Check the logs for specific errors

### "Permission denied" errors
- Ensure the service account has access to the Google Sheet
- Verify Google Sheets API is enabled
- Check the service account email matches

### No data in Price Matrix
- Verify SKUs in Config sheet match the pattern `com.peerplay.mergecruise.credit*`
- Check that the sheet names are exactly "Config", "Price Matrix", "Exchange Rates Log"
- Review Cloud Function logs for errors

### Exchange rates not updating
- Check that exchangerate-api.com is accessible
- Verify the API endpoint is correct
- Check network/firewall settings

## Maintenance

### Update SKUs
Simply edit the Config sheet in Google Sheets - the next run will pick up changes.

### Update Configuration
Edit `cloud-function/config.py` and redeploy:
```bash
cd cloud-function
gcloud functions deploy currency-conversion --gen2 --region=us-central1 --source=.
```

### Price Stability Configuration
The system includes price stability logic to prevent frequent price changes:
- **Threshold**: 5% (configurable in `config.py` as `PRICE_CHANGE_THRESHOLD`)
- **Behavior**: Prices only update if change > 5% or if price decreases (beneficial)
- **.99 Preference**: Prices prefer .99 endings for better presentation (e.g., 110.49 → 110.99)

See [PRICE_STABILITY.md](PRICE_STABILITY.md) for detailed information.

### View Logs
```bash
gcloud functions logs read currency-conversion --gen2 --region=us-central1
```

### Monitor Costs
- Cloud Functions: Free tier includes 2M invocations/month
- Cloud Scheduler: Free tier includes 3 jobs
- Google Sheets API: Free
- Exchange Rate API: Free tier available

Total estimated cost: **$0/month** (within free tiers)

## Next Steps

- Review the generated Price Matrix
- Adjust tier snapping preferences in `config.py` if needed
- Add excluded countries to `config.EXCLUDED_COUNTRIES` if needed
- Set up monitoring/alerts for the Cloud Function

