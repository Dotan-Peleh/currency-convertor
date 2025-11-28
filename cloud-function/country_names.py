"""
Country code to country name mapping.
"""

COUNTRY_NAMES = {
    'US': 'United States',
    'GB': 'United Kingdom',
    'DE': 'Germany',
    'FR': 'France',
    'IT': 'Italy',
    'ES': 'Spain',
    'NL': 'Netherlands',
    'BE': 'Belgium',
    'AT': 'Austria',
    'CH': 'Switzerland',
    'SE': 'Sweden',
    'NO': 'Norway',
    'DK': 'Denmark',
    'PL': 'Poland',
    'CZ': 'Czech Republic',
    'IE': 'Ireland',
    'PT': 'Portugal',
    'GR': 'Greece',
    'FI': 'Finland',
    'HU': 'Hungary',
    'RO': 'Romania',
    'SK': 'Slovakia',
    'BG': 'Bulgaria',
    'HR': 'Croatia',
    'JP': 'Japan',
    'CN': 'China',
    'KR': 'South Korea',
    'IN': 'India',
    'AU': 'Australia',
    'NZ': 'New Zealand',
    'CA': 'Canada',
    'MX': 'Mexico',
    'BR': 'Brazil',
    'AR': 'Argentina',
    'CL': 'Chile',
    'CO': 'Colombia',
    'PE': 'Peru',
    'ZA': 'South Africa',
    'AE': 'United Arab Emirates',
    'SA': 'Saudi Arabia',
    'IL': 'Israel',
    'TR': 'Turkey',
    'RU': 'Russia',
    'SG': 'Singapore',
    'HK': 'Hong Kong',
    'TW': 'Taiwan',
    'TH': 'Thailand',
    'MY': 'Malaysia',
    'ID': 'Indonesia',
    'PH': 'Philippines',
    'VN': 'Vietnam',
    'QA': 'Qatar',
    'KW': 'Kuwait',
    'BH': 'Bahrain',
    'OM': 'Oman',
    'EG': 'Egypt',
    'NG': 'Nigeria',
    'KE': 'Kenya',
    'GH': 'Ghana',
    'MA': 'Morocco',
}

def get_country_name(country_code: str) -> str:
    """
    Get country name from country code.
    
    Args:
        country_code: ISO country code (e.g., 'US', 'GB')
        
    Returns:
        Country name or country code if not found
    """
    return COUNTRY_NAMES.get(country_code.upper(), country_code)

