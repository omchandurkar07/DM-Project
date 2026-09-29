"""
config.py — Central configuration for Stock Market Prediction System
"""

import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Alpha Vantage API Config
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

# ─────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────
DATABASE_PATH = os.path.join(BASE_DIR, 'stockprediction.db')

# ─────────────────────────────────────────────
# Stock Universe — Indian NSE Stocks
# ─────────────────────────────────────────────
STOCKS = {
    'RELIANCE':    {'symbol': 'RELIANCE.NS',   'name': 'Reliance Industries',        'sector': 'Energy',    'color': '#FF6B35'},
    'TCS':         {'symbol': 'TCS.NS',         'name': 'Tata Consultancy Services',  'sector': 'IT',        'color': '#00D4FF'},
    'INFY':        {'symbol': 'INFY.NS',         'name': 'Infosys',                    'sector': 'IT',        'color': '#00B4D8'},
    'HDFCBANK':    {'symbol': 'HDFCBANK.NS',    'name': 'HDFC Bank',                  'sector': 'Finance',   'color': '#7B2FBE'},
    'ICICIBANK':   {'symbol': 'ICICIBANK.NS',   'name': 'ICICI Bank',                 'sector': 'Finance',   'color': '#9D4EDD'},
    'WIPRO':       {'symbol': 'WIPRO.NS',        'name': 'Wipro',                      'sector': 'IT',        'color': '#4CC9F0'},
    'HINDUNILVR':  {'symbol': 'HINDUNILVR.NS',  'name': 'Hindustan Unilever',         'sector': 'FMCG',      'color': '#F72585'},
    'TATAMOTORS':  {'symbol': 'TMPV.NS',        'name': 'Tata Motors',                'sector': 'Auto',      'color': '#4CAF50'},
}

SECTOR_COLORS = {
    'IT':      '#00D4FF',
    'Finance': '#9D4EDD',
    'Energy':  '#FF6B35',
    'FMCG':    '#F72585',
    'Auto':    '#4CAF50',
}

# ─────────────────────────────────────────────
# Data Settings
# ─────────────────────────────────────────────
DATA_PERIOD    = '2y'   # 2 years of historical data
LOOKBACK_DAYS  = 100    # For probability window

# ─────────────────────────────────────────────
# Graph Settings
# ─────────────────────────────────────────────
CORRELATION_THRESHOLD = 0.4   # Min correlation to draw an edge

# ─────────────────────────────────────────────
# ML Settings
# ─────────────────────────────────────────────
TRAIN_TEST_SPLIT = 0.80
RANDOM_STATE     = 42
MODEL_DIR        = os.path.join(BASE_DIR, 'models', 'saved')

# ─────────────────────────────────────────────
# Flask Settings
# ─────────────────────────────────────────────
SECRET_KEY   = 'graphstock_secret_key_2024_!@#'
DEBUG        = True
HOST         = '0.0.0.0'
PORT         = 5000

# Admin Credentials
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123')

