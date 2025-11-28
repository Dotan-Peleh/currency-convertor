#!/bin/bash

# Interactive setup wizard for Currency Conversion System

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Currency Conversion System - Setup Wizard                ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Check prerequisites
echo "Step 1: Checking prerequisites..."
echo ""

if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Please install it first:"
    echo "   https://cloud.google.com/sdk/docs/install"
    exit 1
fi
echo "✓ gcloud CLI found"

if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install it first."
    exit 1
fi
echo "✓ Python 3 found: $(python3 --version)"

# Check GCP project
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo ""
    echo "⚠️  No GCP project configured"
    read -p "Enter your GCP Project ID: " PROJECT_ID
    gcloud config set project "$PROJECT_ID"
else
    echo "✓ GCP Project: $PROJECT_ID"
fi

echo ""
echo "Step 2: Setting up local environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r cloud-function/requirements.txt -q
echo "✓ Local environment ready"
echo ""

# Step 3: Generate Google Sheet templates
echo "Step 3: Generating Google Sheet templates..."
python3 scripts/create_sheet_template.py
echo ""

# Step 4: Google Sheet setup
echo "Step 4: Google Sheet Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Please complete these steps:"
echo ""
echo "1. Go to: https://sheets.google.com"
echo "2. Create a NEW Google Sheet"
echo "3. Create 3 sheets (tabs) named exactly:"
echo "   - 'Config'"
echo "   - 'Price Matrix'"
echo "   - 'Exchange Rates Log'"
echo ""
echo "4. Import the CSV files:"
echo "   - File > Import > Upload > Select 'config_sheet.csv'"
echo "   - Import into 'Config' sheet"
echo "   - Repeat for 'price_matrix_headers.csv' → 'Price Matrix'"
echo "   - Repeat for 'exchange_rates_headers.csv' → 'Exchange Rates Log'"
echo ""
echo "5. Copy the Sheet ID from the URL:"
echo "   https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit"
echo ""
read -p "Enter your Google Sheet ID: " SHEET_ID

if [ -z "$SHEET_ID" ]; then
    echo "❌ Sheet ID is required"
    exit 1
fi

echo ""
echo "Step 5: Service Account Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Setting up service account..."
echo ""

# Check if service account exists
SERVICE_ACCOUNT_NAME="currency-conversion-service"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$SERVICE_ACCOUNT_EMAIL" &>/dev/null; then
    echo "✓ Service account already exists: $SERVICE_ACCOUNT_EMAIL"
else
    echo "Creating service account..."
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" \
        --display-name="Currency Conversion Service" \
        --description="Service account for currency conversion Cloud Function"
    echo "✓ Service account created"
fi

# Create and download key
KEY_FILE="service-account-key.json"
if [ -f "$KEY_FILE" ]; then
    echo "⚠️  Key file already exists: $KEY_FILE"
    read -p "Create new key? (y/n): " CREATE_NEW
    if [ "$CREATE_NEW" = "y" ]; then
        rm -f "$KEY_FILE"
    else
        echo "Using existing key file"
    fi
fi

if [ ! -f "$KEY_FILE" ]; then
    echo "Creating service account key..."
    gcloud iam service-accounts keys create "$KEY_FILE" \
        --iam-account="$SERVICE_ACCOUNT_EMAIL"
    echo "✓ Key file created: $KEY_FILE"
fi

# Enable APIs
echo ""
echo "Enabling required APIs..."
gcloud services enable cloudfunctions.googleapis.com --quiet
gcloud services enable cloudscheduler.googleapis.com --quiet
gcloud services enable secretmanager.googleapis.com --quiet
gcloud services enable sheets.googleapis.com --quiet
echo "✓ APIs enabled"

# Share Google Sheet with service account
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 IMPORTANT: Share your Google Sheet with the service account"
echo ""
echo "1. Open your Google Sheet"
echo "2. Click 'Share' button"
echo "3. Add this email: $SERVICE_ACCOUNT_EMAIL"
echo "4. Give it 'Editor' permissions"
echo "5. Click 'Send'"
echo ""
read -p "Press Enter after you've shared the sheet..."

# Step 6: Deploy to GCP
echo ""
echo "Step 6: Deploying to GCP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

export GCP_PROJECT_ID="$PROJECT_ID"
export GOOGLE_SHEETS_ID="$SHEET_ID"
export GCP_REGION="us-central1"

echo "Deploying Cloud Function..."
cd cloud-function

gcloud functions deploy currency-conversion \
    --gen2 \
    --runtime=python311 \
    --region="$GCP_REGION" \
    --source=. \
    --entry-point=main \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars="GOOGLE_SHEETS_ID=$SHEET_ID,LOG_LEVEL=INFO" \
    --service-account="$SERVICE_ACCOUNT_EMAIL" \
    --memory=512MB \
    --timeout=540s \
    --max-instances=10 \
    --quiet

cd ..

FUNCTION_URL=$(gcloud functions describe currency-conversion \
    --gen2 \
    --region="$GCP_REGION" \
    --format="value(serviceConfig.uri)")

echo "✓ Cloud Function deployed: $FUNCTION_URL"

# Create scheduler
echo ""
echo "Creating Cloud Scheduler job..."
JOB_NAME="currency-conversion-daily"

if gcloud scheduler jobs describe "$JOB_NAME" --location="$GCP_REGION" &>/dev/null; then
    echo "Updating existing scheduler job..."
    gcloud scheduler jobs update http "$JOB_NAME" \
        --location="$GCP_REGION" \
        --schedule="0 0 * * *" \
        --uri="$FUNCTION_URL" \
        --http-method=GET \
        --time-zone="UTC" \
        --quiet
else
    gcloud scheduler jobs create http "$JOB_NAME" \
        --location="$GCP_REGION" \
        --schedule="0 0 * * *" \
        --uri="$FUNCTION_URL" \
        --http-method=GET \
        --time-zone="UTC" \
        --quiet
fi

echo "✓ Cloud Scheduler job created"
echo ""

# Step 7: Test
echo "Step 7: Testing the system"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Triggering the function..."
echo ""

RESPONSE=$(gcloud functions call currency-conversion \
    --gen2 \
    --region="$GCP_REGION" \
    --format=json 2>&1)

if echo "$RESPONSE" | grep -q "error"; then
    echo "⚠️  Function returned an error. Check logs:"
    echo "   gcloud functions logs read currency-conversion --gen2 --region=$GCP_REGION"
else
    echo "✓ Function executed successfully!"
    echo ""
    echo "Check your Google Sheet - the 'Price Matrix' should be populated!"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Setup Complete!                                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📊 View your results:"
echo "   https://docs.google.com/spreadsheets/d/$SHEET_ID/edit"
echo ""
echo "📝 View logs:"
echo "   gcloud functions logs read currency-conversion --gen2 --region=$GCP_REGION"
echo ""
echo "🔄 The system will run automatically daily at 00:00 UTC"
echo ""

