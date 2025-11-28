#!/bin/bash

# Local setup script for Currency Conversion System
# This helps set up the environment and test locally before deploying

set -e

echo "=== Currency Conversion System - Local Setup ==="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

echo "✓ Python found: $(python3 --version)"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "✓ Virtual environment ready"

# Activate and install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r cloud-function/requirements.txt -q

echo "✓ Dependencies installed"
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Create a Google Sheet following docs/GOOGLE_SHEETS_TEMPLATE.md"
echo "2. Set up service account (see docs/API_KEYS.md)"
echo "3. Set environment variables:"
echo "   export GOOGLE_APPLICATION_CREDENTIALS='path/to/service-account-key.json'"
echo "   export GOOGLE_SHEETS_ID='your-sheet-id'"
echo "4. Test locally:"
echo "   source venv/bin/activate"
echo "   cd cloud-function && python main.py"
echo ""
echo "Or deploy to GCP:"
echo "   ./deployment/deploy.sh"

