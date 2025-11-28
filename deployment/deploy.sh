#!/bin/bash

# Deployment script for Currency Conversion Cloud Function
# This script sets up GCP resources and deploys the Cloud Function

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
FUNCTION_NAME="currency-conversion"
REGION="${GCP_REGION:-us-central1}"
RUNTIME="python311"
ENTRY_POINT="main"
SCHEDULE="0 0 * * *"  # Daily at 00:00 UTC

echo "Deploying Currency Conversion System to GCP..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Set the project
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "Enabling required GCP APIs..."
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable sheets.googleapis.com

# Create Cloud Function
echo "Deploying Cloud Function..."
cd cloud-function

gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=$RUNTIME \
    --region=$REGION \
    --source=. \
    --entry-point=$ENTRY_POINT \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars="LOG_LEVEL=INFO" \
    --memory=512MB \
    --timeout=540s \
    --max-instances=10

# Get the function URL
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME \
    --gen2 \
    --region=$REGION \
    --format="value(serviceConfig.uri)")

echo "Cloud Function deployed at: $FUNCTION_URL"

# Create Cloud Scheduler job
echo "Creating Cloud Scheduler job..."
JOB_NAME="${FUNCTION_NAME}-daily"

# Check if job already exists
if gcloud scheduler jobs describe $JOB_NAME --location=$REGION &> /dev/null; then
    echo "Updating existing scheduler job..."
    gcloud scheduler jobs update http $JOB_NAME \
        --location=$REGION \
        --schedule="$SCHEDULE" \
        --uri="$FUNCTION_URL" \
        --http-method=GET \
        --time-zone="UTC"
else
    echo "Creating new scheduler job..."
    gcloud scheduler jobs create http $JOB_NAME \
        --location=$REGION \
        --schedule="$SCHEDULE" \
        --uri="$FUNCTION_URL" \
        --http-method=GET \
        --time-zone="UTC"
fi

echo ""
echo "Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Set GOOGLE_SHEETS_ID environment variable in Cloud Function"
echo "2. Set up Google Service Account credentials (see docs/API_KEYS.md)"
echo "3. Create Google Sheets with the template structure (see docs/GOOGLE_SHEETS_TEMPLATE.md)"
echo "4. Test the function manually or wait for the scheduled run"

