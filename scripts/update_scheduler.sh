#!/bin/bash

# Script to update Cloud Scheduler to run twice daily (12:00 and 24:00 UTC)

set -e

PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-us-central1}"
JOB_NAME="currency-conversion-daily"

echo "Updating Cloud Scheduler job to run twice daily..."
echo "Schedule: 12:00 UTC (noon) and 24:00 UTC (midnight)"
echo ""

# Get the function URL
FUNCTION_URL=$(gcloud functions describe currency-conversion \
    --gen2 \
    --region="$REGION" \
    --format="value(serviceConfig.uri)" 2>/dev/null || echo "")

if [ -z "$FUNCTION_URL" ]; then
    echo "Error: Could not find Cloud Function. Make sure it's deployed."
    exit 1
fi

echo "Function URL: $FUNCTION_URL"
echo ""

# Update or create scheduler job
if gcloud scheduler jobs describe "$JOB_NAME" --location="$REGION" &>/dev/null; then
    echo "Updating existing scheduler job..."
    gcloud scheduler jobs update http "$JOB_NAME" \
        --location="$REGION" \
        --schedule="0 0,12 * * *" \
        --uri="$FUNCTION_URL" \
        --http-method=GET \
        --time-zone="UTC" \
        --quiet
    echo "✓ Scheduler job updated"
else
    echo "Creating new scheduler job..."
    gcloud scheduler jobs create http "$JOB_NAME" \
        --location="$REGION" \
        --schedule="0 0,12 * * *" \
        --uri="$FUNCTION_URL" \
        --http-method=GET \
        --time-zone="UTC" \
        --quiet
    echo "✓ Scheduler job created"
fi

echo ""
echo "Scheduler will now run twice daily:"
echo "  - 00:00 UTC (midnight)"
echo "  - 12:00 UTC (noon)"
echo ""
echo "To verify:"
echo "  gcloud scheduler jobs describe $JOB_NAME --location=$REGION"

