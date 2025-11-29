"""
Configuration constants for the currency conversion system.
"""

# Stash fee configuration (0% for first year)
STASH_FEE_PERCENT = 0.0  # 0% for first year
STASH_FIXED_FEE = 0.0  # No fixed fee

# Tier snapping configuration
# "up" ensures visibility price is always higher than raw price (looks better to users)
TIER_SNAPPING_MODE = "up"  # Options: "nearest", "up", "down"

# Exchange Rate API configuration
EXCHANGE_RATE_API_BASE_URL = "https://api.exchangerate-api.com/v4/latest/USD"
EXCHANGE_RATE_API_KEY = None  # Set via environment variable or Secret Manager

# Google Sheets configuration
GOOGLE_SHEETS_ID = None  # Set via environment variable
GOOGLE_SHEETS_CONFIG_SHEET = "Config"
GOOGLE_SHEETS_PRICE_MATRIX_SHEET = "Price Matrix"
GOOGLE_SHEETS_EXCHANGE_RATES_SHEET = "Exchange Rates Log"

# Apple/Google platform fees
APPLE_FEE_PERCENT = 0.30  # 30% standard, 15% for small business (configurable)
GOOGLE_FEE_PERCENT = 0.30  # 30% standard, 15% for small business (configurable)

# Country exclusion list (add country codes to exclude)
EXCLUDED_COUNTRIES = [
    # Add country codes here if needed, e.g., "RU", "IR"
]

# SKU filtering pattern
SKU_PATTERN = r"com\.peerplay\.mergecruise\.credit"

# Logging configuration
LOG_LEVEL = "INFO"

# Price stability configuration
PRICE_CHANGE_THRESHOLD = 0.05  # 5% - only update prices if change is more than this

