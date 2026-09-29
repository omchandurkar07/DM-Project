"""
models/data_collector.py
========================
Fetches historical OHLCV data from Alpha Vantage or Yahoo Finance,
computes technical indicators (MA20, MA50, RSI, MACD), and stores
everything in the SQLite database.

Fallback: generates realistic synthetic data if network is unavailable.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os
import sys
import requests
import time

# Allow running standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import STOCKS, DATA_PERIOD, BASE_DIR, ALPHA_VANTAGE_API_KEY
from database import execute_sql, get_connection, get_cursor, init_db


# ─────────────────────────────────────────────────────────────────────────────
# Technical Indicator Helpers
# ─────────────────────────────────────────────────────────────────────────────

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute Relative Strength Index."""
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(window=period).mean()
    loss  = (-delta.clip(upper=0)).rolling(window=period).mean()
    rs    = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def compute_macd(series: pd.Series,
                 fast: int = 12, slow: int = 26, signal: int = 9):
    """Return (MACD line, Signal line)."""
    ema_fast   = series.ewm(span=fast,   adjust=False).mean()
    ema_slow   = series.ewm(span=slow,   adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line


# ─────────────────────────────────────────────────────────────────────────────
# DataCollector Class
# ─────────────────────────────────────────────────────────────────────────────

class DataCollector:
    """Fetch, process, and store stock data."""

    def __init__(self):
        self.dataset_dir = os.path.join(BASE_DIR, 'dataset')
        os.makedirs(self.dataset_dir, exist_ok=True)

    # ── public API ─────────────────────────────────────────────────────────

    def fetch_and_store_all(self):
        """Main entry point: fetch all stocks and store to DB."""
        all_frames = []
        for key, info in STOCKS.items():
            print(f"[DataCollector] Fetching {key} ({info['symbol']}) ...")
            df = self._fetch_single(key, info['symbol'])
            if df is not None and not df.empty:
                self._store(key, df)
                all_frames.append(df.assign(company=key))
                print(f"  [OK] {len(df)} rows stored for {key}")
            else:
                print(f"  [WARN] No data for {key} -- using synthetic fallback")
                df = self._synthetic_data(key)
                self._store(key, df)
                all_frames.append(df.assign(company=key))

        if all_frames:
            combined = pd.concat(all_frames, ignore_index=True)
            csv_path = os.path.join(self.dataset_dir, 'stocks.csv')
            combined.to_csv(csv_path, index=False)
            print(f"[DataCollector] CSV saved -> {csv_path}")
        return True

    def fetch_single_stock(self, symbol_key: str) -> pd.DataFrame:
        """Fetch one stock; returns processed DataFrame."""
        info = STOCKS.get(symbol_key)
        if not info:
            raise ValueError(f"Unknown symbol key: {symbol_key}")
        df = self._fetch_single(symbol_key, info['symbol'])
        if df is None or df.empty:
            df = self._synthetic_data(symbol_key)
        return df

    def fetch_latest_quotes(self) -> tuple[dict[str, dict], dict[str, str]]:
        """Fetch the latest daily quote for each stock from Yahoo Finance."""
        quotes = {}
        errors = {}

        for key, info in STOCKS.items():
            try:
                history = yf.Ticker(info['symbol']).history(
                    period='5d', auto_adjust=True
                ).dropna(subset=['Close'])
                if len(history) < 2:
                    errors[key] = 'Yahoo returned fewer than two daily prices'
                    continue

                latest = history.iloc[-1]
                previous = history.iloc[-2]
                price = float(latest['Close'])
                previous_price = float(previous['Close'])
                if not np.isfinite(price) or price <= 0 or not np.isfinite(previous_price):
                    errors[key] = 'Yahoo returned an invalid price'
                    continue

                change = price - previous_price
                quotes[key] = {
                    'date': history.index[-1].date().isoformat(),
                    'price': round(price, 2),
                    'change': round(change, 2),
                    'change_pct': round(change / previous_price * 100, 2),
                    'high': round(float(latest['High']), 2),
                    'low': round(float(latest['Low']), 2),
                    'volume': int(latest['Volume']),
                }
            except Exception as exc:
                errors[key] = str(exc)[:200]

        return quotes, errors

    def get_latest_price(self, symbol_key: str) -> float:
        """Return the most recent closing price from DB."""
        conn = get_connection()
        cursor = get_cursor(conn)
        execute_sql(cursor,
            "SELECT close FROM stocks WHERE company=? ORDER BY date DESC LIMIT 1",
            (symbol_key,)
        )
        row = cursor.fetchone()
        conn.close()
        return float(row['close']) if row else 0.0

    # ── private helpers ────────────────────────────────────────────────────

    def _fetch_from_alpha_vantage(self, key: str, symbol: str) -> pd.DataFrame | None:
        """Fetch historical daily data from Alpha Vantage API."""
        if not ALPHA_VANTAGE_API_KEY or "your_alpha_vantage_api_key" in ALPHA_VANTAGE_API_KEY or ALPHA_VANTAGE_API_KEY.strip() == "":
            print(f"  [Alpha Vantage] Skipping: No API key configured in .env")
            return None

        # Map symbol. Alpha Vantage expects .BSE for Indian Stocks instead of .NS
        av_symbol = symbol
        if av_symbol.endswith('.NS'):
            av_symbol = av_symbol.replace('.NS', '.BSE')

        # Symbol overrides for Alpha Vantage (since some tickers differ from Yahoo Finance)
        symbol_overrides = {
            "TATAMOTORS.BSE": "TMCV.BSE"
        }
        if av_symbol in symbol_overrides:
            av_symbol = symbol_overrides[av_symbol]

        print(f"  [Alpha Vantage] Fetching data for {key} ({av_symbol}) ...")
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": av_symbol,
            "apikey": ALPHA_VANTAGE_API_KEY,
            "outputsize": "full"
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            # Sleep 1.5 seconds to respect the Alpha Vantage free-tier request rate limit
            time.sleep(1.5)
            if response.status_code != 200:
                print(f"  [Alpha Vantage Error] Status code: {response.status_code}")
                return None

            data = response.json()
            
            # Check for rate limit or errors
            if "Note" in data:
                print(f"  [Alpha Vantage LIMIT] Rate limit reached: {data['Note']}")
                return None
            if "Information" in data:
                print(f"  [Alpha Vantage LIMIT/INFO] Rate limit/Information: {data['Information']}")
                return None
            if "Error Message" in data:
                print(f"  [Alpha Vantage ERROR] {data['Error Message']}")
                return None
                
            time_series = data.get("Time Series (Daily)")
            if not time_series:
                print(f"  [Alpha Vantage] No daily time series data found in response. Keys: {list(data.keys())}")
                return None

            # Build DataFrame
            rows = []
            for date_str, values in time_series.items():
                try:
                    dt = pd.to_datetime(date_str).date()
                    rows.append({
                        "date": dt,
                        "open": float(values["1. open"]),
                        "high": float(values["2. high"]),
                        "low": float(values["3. low"]),
                        "close": float(values["4. close"]),
                        "volume": float(values["5. volume"])
                    })
                except (ValueError, KeyError):
                    continue

            df = pd.DataFrame(rows)
            if df.empty:
                return None

            # Sort by date ascending to match yfinance output style and compute rolling metrics correctly
            df = df.sort_values("date").reset_index(drop=True)

            # Limit to last 500 trading days (~2 years)
            if len(df) > 500:
                df = df.iloc[-500:].reset_index(drop=True)

            df = self._add_indicators(df)
            df['company'] = key
            return df

        except Exception as e:
            print(f"  [Alpha Vantage ERROR] {key}: {e}")
            return None

    def _fetch_single(self, key: str, yf_symbol: str) -> pd.DataFrame | None:
        """Download from Alpha Vantage first, fallback to yfinance, and add indicators."""
        # Try Alpha Vantage first
        df = self._fetch_from_alpha_vantage(key, yf_symbol)
        if df is not None and not df.empty:
            print(f"  [OK] Successfully fetched {key} from Alpha Vantage")
            return df
        
        # Fallback to yfinance
        print(f"  [Info] Falling back to Yahoo Finance for {key} ...")
        try:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=DATA_PERIOD, auto_adjust=True)
            if df.empty:
                return None

            df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            df.index = pd.to_datetime(df.index).date
            df.index.name = 'date'
            df = df.reset_index()

            df = self._add_indicators(df)
            df['company'] = key
            return df

        except Exception as e:
            print(f"  [yfinance ERROR] {key}: {e}")
            return None

    def _add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Append MA20, MA50, RSI, MACD, Signal columns."""
        close = df['close']
        df['ma20']   = close.rolling(window=20, min_periods=1).mean().round(4)
        df['ma50']   = close.rolling(window=50, min_periods=1).mean().round(4)
        df['rsi']    = compute_rsi(close).round(4)
        macd, signal = compute_macd(close)
        df['macd']   = macd.round(4)
        df['signal'] = signal.round(4)
        return df

    def _store(self, key: str, df: pd.DataFrame):
        """Upsert rows into the stocks table after clearing existing ones."""
        conn = get_connection()
        cursor = get_cursor(conn)
        
        # Clear existing data for this company to prevent mixing old/stale/synthetic data with new data
        execute_sql(cursor, "DELETE FROM stocks WHERE company=?", (key,))

        for _, row in df.iterrows():
            try:
                execute_sql(cursor, '''
                    INSERT INTO stocks
                        (company, date, open, high, low, close,
                         volume, ma20, ma50, rsi, macd, `signal`)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    key,
                    str(row['date']),
                    _safe(row, 'open'),  _safe(row, 'high'),
                    _safe(row, 'low'),   _safe(row, 'close'),
                    int(row.get('volume', 0) or 0),
                    _safe(row, 'ma20'),  _safe(row, 'ma50'),
                    _safe(row, 'rsi'),   _safe(row, 'macd'),
                    _safe(row, 'signal'),
                ))
            except Exception as e:
                pass   # skip bad rows silently

        conn.commit()
        conn.close()

    def _synthetic_data(self, key: str) -> pd.DataFrame:
        """
        Generate 500 days of synthetic OHLCV data with realistic
        random-walk price behaviour as a demo fallback.
        """
        np.random.seed(hash(key) % (2**31))
        base_prices = {
            'RELIANCE': 2500, 'TCS': 3600, 'INFY': 1480,
            'HDFCBANK': 1600, 'ICICIBANK': 950,
            'WIPRO': 450,    'HINDUNILVR': 2700, 'TATAMOTORS': 700,
        }
        start = base_prices.get(key, 1000)
        n     = 500
        dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n)

        returns = np.random.normal(0.0003, 0.015, n)
        closes  = start * np.exp(np.cumsum(returns))
        highs   = closes * (1 + np.abs(np.random.normal(0, 0.008, n)))
        lows    = closes * (1 - np.abs(np.random.normal(0, 0.008, n)))
        opens   = np.roll(closes, 1)
        opens[0] = start
        volumes = np.random.randint(500_000, 5_000_000, n).astype(float)

        df = pd.DataFrame({
            'date':   [d.date() for d in dates],
            'open':   opens.round(2),
            'high':   highs.round(2),
            'low':    lows.round(2),
            'close':  closes.round(2),
            'volume': volumes,
            'company': key,
        })
        return self._add_indicators(df)


def _safe(row, col):
    """Return float or None for a row column."""
    v = row.get(col)
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    return float(v)


# ── CLI quick-run ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    dc = DataCollector()
    dc.fetch_and_store_all()
    print("Done!")
