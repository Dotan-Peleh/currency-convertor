# API Keys and Credentials Setup

This document explains how to set up all required API keys and credentials for the Currency Conversion System.

## Required Credentials

1. **Google Service Account** - For Google Sheets API access
2. **Exchange Rate API Key** (Optional) - For exchangerate-api.com (free tier doesn't require it)

## Google Service Account Setup

### Step 1: Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **IAM & Admin** > **Service Accounts**
4. Click **Create Service Account**
5. Enter a name (e.g., "currency-conversion-service")
6. Click **Create and Continue**
7. Grant role: **Editor** (or more specific roles if preferred)
8. Click **Done**

### Step 2: Create and Download Key

1. Click on the newly created service account
2. Go to the **Keys** tab
3. Click **Add Key** > **Create new key**
4. Select **JSON** format
5. Click **Create** - the JSON file will download automatically
6. Save this file securely (you'll need it for deployment)

### Step 3: Enable Google Sheets API

1. In Google Cloud Console, go to **APIs & Services** > **Library**
2. Search for "Google Sheets API"
3. Click on it and click **Enable**

### Step 4: Share Google Sheet with Service Account

1. Open your Google Sheet
2. Click **Share** button
3. Add the service account email (found in the JSON file as `client_email`)
4. Give it **Editor** permissions
5. Click **Send**

### Step 5: Set Up Credentials in Cloud Function

**Option A: Using Secret Manager (Recommended)**

```bash
# Create secret
gcloud secrets create google-service-account-key \
    --data-file=path/to/service-account-key.json \
    --project=YOUR_PROJECT_ID

# Grant Cloud Function access
gcloud secrets add-iam-policy-binding google-service-account-key \
    --member="serviceAccount:YOUR_PROJECT_ID@appspot.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

Then update your Cloud Function to read from Secret Manager.

**Option B: Using Environment Variable**

Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to the JSON file path (for local testing) or upload the file to Cloud Storage and reference it.

**Option C: Embed in Cloud Function (Not Recommended for Production)**

Upload the JSON file to your Cloud Function source and reference it directly.

## Exchange Rate API Setup

### exchangerate-api.com (Free Tier)

The free tier doesn't require an API key, but you can sign up for better rate limits:

1. Go to [exchangerate-api.com](https://www.exchangerate-api.com/)
2. Sign up for a free account
3. Get your API key from the dashboard
4. (Optional) Set it in Cloud Function environment variables:
   ```bash
   gcloud functions deploy currency-conversion \
       --set-env-vars="EXCHANGE_RATE_API_KEY=your-api-key-here"
   ```

### Alternative: openexchangerates.org

If you prefer to use openexchangerates.org:

1. Sign up at [openexchangerates.org](https://openexchangerates.org/)
2. Get your API key
3. Update `config.py` to use their endpoint:
   ```python
   EXCHANGE_RATE_API_BASE_URL = "https://openexchangerates.org/api/latest.json"
   ```

## Environment Variables

Set these in your Cloud Function:

- `GOOGLE_SHEETS_ID` - Your Google Sheet ID (from the URL)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON (if using file)
- `EXCHANGE_RATE_API_KEY` - (Optional) Exchange rate API key

### Setting Environment Variables in Cloud Function

```bash
gcloud functions deploy currency-conversion \
    --set-env-vars="GOOGLE_SHEETS_ID=your-sheet-id-here,EXCHANGE_RATE_API_KEY=your-key-here"
```

## Security Best Practices

1. **Never commit credentials to git** - Add `*.json` to `.gitignore`
2. **Use Secret Manager** for production deployments
3. **Rotate keys regularly** - Especially if they're exposed
4. **Limit service account permissions** - Only grant necessary roles
5. **Monitor API usage** - Set up alerts for unusual activity

## Troubleshooting

### "Permission denied" errors
- Ensure the service account has access to the Google Sheet
- Check that Google Sheets API is enabled
- Verify the service account email is correct

### "Invalid credentials" errors
- Verify the JSON file is valid
- Check that the service account hasn't been deleted
- Ensure the credentials file path is correct

### "Sheet not found" errors
- Verify the Sheet ID is correct
- Check that the sheet is shared with the service account
- Ensure the sheet names match exactly (case-sensitive)

