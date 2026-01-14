"""
Configuration file for Trading System
Store all settings, API keys, and constants here
"""

import os
from datetime import time

# ============================================
# STOCK SELECTION
# ============================================

# US Stocks to track (Yahoo Finance format)
US_STOCKS = [
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "GOOGL",  # Google
    "JPM",    # JP Morgan
    "XOM",    # Exxon Mobil
]

# Egyptian stocks (add when you have EGX data source)
EGX_STOCKS = [
    # "COMI.CA",  # Example - add when ready
]

# Combined list
ALL_STOCKS = US_STOCKS + EGX_STOCKS

# ============================================
# API CREDENTIALS
# ============================================

# News API (Get free key from: https://newsapi.org/)
NEWS_API_KEY = '911bd9fe0dd0497c81632ee8af966bb4'

# Add other API keys as needed
# ALPHA_VANTAGE_KEY = os.getenv('ALPHA_VANTAGE_KEY', '')

# ============================================
# DATA COLLECTION SETTINGS
# ============================================

# How many days of historical data to fetch initially
INITIAL_LOOKBACK_DAYS = 90

# How many days to fetch on daily updates
DAILY_LOOKBACK_DAYS = 5  # Fetch last 5 days to catch any gaps

# Retry settings (your B→D pattern)
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5  # Wait between retries

# Data collection time (after market close)
COLLECTION_TIME = time(16, 30)  # 4:30 PM EST (market closes 4 PM)

# ============================================
# DATABASE SETTINGS
# ============================================

DATABASE_PATH = 'stocks.db'

# ============================================
# NOTIFICATION SETTINGS
# ============================================

# Email settings
SMTP_SERVER = 'smtp.mail.yahoo.com'
SMTP_PORT = 587
EMAIL_FROM = 'moatasem_cs@yahoo.com'
EMAIL_TO = 'crassdart@gmail.com'
EMAIL_PASSWORD =  'jegihpicqgqdqkbw'

# Alert thresholds
ALERT_ON_MISSING_DATA = True
ALERT_ON_COLLECTION_FAILURE = True
ALERT_ON_PREDICTION_ERROR = True

# ============================================
# PREDICTION SETTINGS
# ============================================

# Technical indicator parameters
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

MA_SHORT_PERIOD = 10
MA_LONG_PERIOD = 30

# Prediction timeframe
PREDICTION_HORIZON_DAYS = 7  # Predict next week

# Confidence thresholds
MIN_CONFIDENCE_TO_PREDICT = 0.3  # Don't predict if confidence < 30%

# ============================================
# EVALUATION SETTINGS
# ============================================

# What counts as "correct" prediction
# If we predict UP, and price goes up by at least this %, it's correct
MIN_MOVE_THRESHOLD = 0.5  # 0.5% minimum move to count

# ============================================
# LOGGING
# ============================================

LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = 'logs/trading_system.log'

# ============================================
# FEATURE FLAGS (turn features on/off easily)
# ============================================

FEATURES = {
    'collect_news': True,
    'sentiment_analysis': True,
    'volume_analysis': True,
    'send_email_reports': True,
}

# ============================================
# VALIDATION
# ============================================

def validate_config():
    """Check that critical settings are configured"""
    issues = []
    
    if NEWS_API_KEY == 'YOUR_API_KEY_HERE':
        issues.append("⚠️  NEWS_API_KEY not set")
    
    if not ALL_STOCKS:
        issues.append("❌ No stocks configured to track")
    
    if EMAIL_PASSWORD == '' and FEATURES['send_email_reports']:
        issues.append("⚠️  EMAIL_PASSWORD not set (reports won't send)")
    
    return issues

if __name__ == "__main__":
    print("🔍 Validating configuration...")
    print(f"📊 Tracking {len(ALL_STOCKS)} stocks: {', '.join(ALL_STOCKS)}")
    print(f"📧 Reports will be sent to: {EMAIL_TO}")
    
    issues = validate_config()
    if issues:
        print("\n⚠️  Configuration issues found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ Configuration looks good!")