"""
models/prediction.py
====================
Machine Learning pipeline for stock price prediction.

Features used:
  Open, High, Low, Close, Volume,
  MA20, MA50, RSI, MACD,
  Lag features (Close_t-1, Close_t-2, Close_t-3),
  PageRank score,
  Rolling volatility

Models:
  • Linear Regression (baseline)
  • Random Forest Regressor (price prediction)
  • Random Forest Classifier (UP / DOWN direction)
  • XGBoost Regressor (advanced)

Output:
  predicted_price (float)
  direction       ('UP' | 'DOWN')
  confidence      (0.0 – 1.0)
  rmse            (model evaluation metric)
"""

import os
import sys
import numpy as np
import pandas as pd
import joblib

from sklearn.ensemble        import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model    import LinearRegression
from sklearn.preprocessing   import StandardScaler
from sklearn.metrics         import mean_squared_error, accuracy_score

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATABASE_BACKEND, STOCKS, RANDOM_STATE, TRAIN_TEST_SPLIT, MODEL_DIR
from database import fetch_all, fetch_one

os.makedirs(MODEL_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Feature Engineering
# ─────────────────────────────────────────────────────────────────────────────

def build_features(df: pd.DataFrame, pagerank_score: float = 0.125,
                   include_latest: bool = False) -> pd.DataFrame:
    """
    Build the feature matrix from raw OHLCV + indicators.
    Adds lag features and rolling statistics.
    """
    df = df.copy().sort_values('date').reset_index(drop=True)

    # Lag features
    for lag in [1, 2, 3, 5]:
        df[f'close_lag_{lag}'] = df['close'].shift(lag)
        df[f'return_lag_{lag}'] = df['close'].pct_change(lag)

    # Rolling stats
    df['vol_5']   = df['close'].rolling(5,  min_periods=1).std()
    df['vol_20']  = df['close'].rolling(20, min_periods=1).std()
    df['hl_range'] = df['high'] - df['low']

    # Target: next day close
    df['target_price']  = df['close'].shift(-1)
    df['target_direction'] = (df['target_price'] > df['close']).astype(int)

    df['pagerank'] = pagerank_score
    df['open_close_ratio'] = df['open'] / (df['close'] + 1e-9)

    if include_latest:
        df = df.dropna(subset=[col for col in FEATURE_COLS if col in df.columns])
    else:
        df = df.dropna()
    return df


FEATURE_COLS = [
    'open', 'high', 'low', 'close', 'volume',
    'ma20', 'ma50', 'rsi', 'macd', 'signal',
    'close_lag_1', 'close_lag_2', 'close_lag_3', 'close_lag_5',
    'return_lag_1', 'return_lag_2', 'return_lag_3', 'return_lag_5',
    'vol_5', 'vol_20', 'hl_range', 'pagerank', 'open_close_ratio',
]


# ─────────────────────────────────────────────────────────────────────────────
# PredictionModel Class
# ─────────────────────────────────────────────────────────────────────────────

class PredictionModel:
    """
    Trains and stores ML models per stock.
    Supports price regression and direction classification.
    """

    def __init__(self):
        self._models:  dict = {}   # symbol → {'reg': ..., 'cls': ..., 'scaler': ..., 'metrics': ...}
        self._load_all_models()

    # ── Public API ────────────────────────────────────────────────────────────

    def train_all(self) -> dict:
        """Train models for all stocks in the universe."""
        results = {}
        for key in STOCKS:
            try:
                metrics = self.train(key)
                results[key] = metrics
                print(f"[ML] {key}: RMSE={metrics.get('rmse', 'N/A'):.2f}  "
                      f"Acc={metrics.get('accuracy', 0)*100:.1f}%")
            except Exception as e:
                print(f"[ML] Error training {key}: {e}")
                results[key] = {'error': str(e)}
        return results

    def train(self, symbol: str) -> dict:
        """Train regressor + classifier for a single stock."""
        raw_df = self._load_data(symbol)
        if raw_df is None or len(raw_df) < 60:
            raise ValueError(f"Not enough data for {symbol} (need ≥60 rows)")

        data_as_of = str(raw_df['date'].iloc[-1])
        pagerank = self._get_pagerank(symbol)
        df = build_features(raw_df, pagerank)

        # Keep only available feature columns
        avail_cols = [c for c in FEATURE_COLS if c in df.columns]
        X = df[avail_cols].values
        y_price = df['target_price'].values
        y_dir   = df['target_direction'].values

        # Train / test split (time-aware — no shuffle)
        split = int(len(X) * TRAIN_TEST_SPLIT)
        scaler = StandardScaler()
        X_tr = scaler.fit_transform(X[:split])
        X_te = scaler.transform(X[split:])
        y_pr_tr, y_pr_te = y_price[:split], y_price[split:]
        y_di_tr, y_di_te = y_dir[:split],   y_dir[split:]

        # ── Regressor ─────────────────────────────────────────────────
        rf_reg = RandomForestRegressor(
            n_estimators=150, max_depth=12, min_samples_leaf=3,
            random_state=RANDOM_STATE, n_jobs=-1)
        rf_reg.fit(X_tr, y_pr_tr)

        lr = LinearRegression()
        lr.fit(X_tr, y_pr_tr)

        if XGB_AVAILABLE:
            xgb_reg = xgb.XGBRegressor(
                n_estimators=100, max_depth=6, learning_rate=0.05,
                random_state=RANDOM_STATE, verbosity=0, n_jobs=-1)
            xgb_reg.fit(X_tr, y_pr_tr)
            y_pred_test = xgb_reg.predict(X_te)
        else:
            xgb_reg = None
            y_pred_test = rf_reg.predict(X_te)

        rmse = float(np.sqrt(mean_squared_error(y_pr_te, y_pred_test)))

        # ── Classifier ────────────────────────────────────────────────
        rf_cls = RandomForestClassifier(
            n_estimators=150, max_depth=10, min_samples_leaf=3,
            random_state=RANDOM_STATE, n_jobs=-1)
        rf_cls.fit(X_tr, y_di_tr)
        y_cls_pred = rf_cls.predict(X_te)
        accuracy = float(accuracy_score(y_di_te, y_cls_pred))
        baseline_direction = int(np.mean(y_di_tr) >= 0.5)
        baseline_accuracy = float(accuracy_score(
            y_di_te, np.full(len(y_di_te), baseline_direction)
        ))
        close_index = avail_cols.index('close')
        baseline_rmse = float(np.sqrt(mean_squared_error(
            y_pr_te, X[split:, close_index]
        )))

        # Refit the deployable models on all labeled rows after holdout evaluation.
        scaler.fit(X)
        X_all_scaled = scaler.transform(X)
        rf_reg.fit(X_all_scaled, y_price)
        lr.fit(X_all_scaled, y_price)
        rf_cls.fit(X_all_scaled, y_dir)
        if xgb_reg is not None:
            xgb_reg.fit(X_all_scaled, y_price)

        # ── Store & Save ───────────────────────────────────────────────
        entry = {
            'reg':    xgb_reg if XGB_AVAILABLE else rf_reg,
            'rf_reg': rf_reg,
            'cls':    rf_cls,
            'lr':     lr,
            'scaler': scaler,
            'features': avail_cols,
            'data_as_of': data_as_of,
            'database_backend': DATABASE_BACKEND,
            'metrics': {'rmse': rmse, 'accuracy': accuracy,
                        'baseline_rmse': baseline_rmse,
                        'baseline_accuracy': baseline_accuracy,
                        'train_size': split, 'test_size': len(X_te)},
        }
        self._models[symbol] = entry
        self._save_model(symbol, entry)

        return entry['metrics']

    def predict(self, symbol: str) -> dict:
        """
        Return next-day price prediction and direction for a stock.
        Auto-trains if model not found.
        """
        entry = self._models.get(symbol)
        if entry is None or self._model_is_stale(symbol, entry):
            try:
                self.train(symbol)
            except Exception as e:
                return self._fallback_prediction(symbol, str(e))

        entry = self._models[symbol]
        df = self._load_data(symbol)
        if df is None or df.empty:
            return self._fallback_prediction(symbol, "No data in database")

        pagerank = self._get_pagerank(symbol)
        df = build_features(df, pagerank, include_latest=True)
        if df.empty:
            return self._fallback_prediction(symbol, "Feature build failed")

        avail_cols = [c for c in entry['features'] if c in df.columns]
        last_row = df[avail_cols].iloc[-1:].values
        X_scaled = entry['scaler'].transform(last_row)

        # Price prediction
        pred_price = float(entry['reg'].predict(X_scaled)[0])

        # Direction + confidence
        direction_encoded = int(entry['cls'].predict(X_scaled)[0])
        direction = 'UP' if direction_encoded == 1 else 'DOWN'
        proba = entry['cls'].predict_proba(X_scaled)[0]
        confidence = float(proba[direction_encoded])

        current_price = float(df['close'].iloc[-1])
        change        = pred_price - current_price
        change_pct    = (change / current_price) * 100

        # Feature importances (top 5)
        try:
            fi = entry['rf_reg'].feature_importances_
            feat_imp = sorted(zip(avail_cols, fi), key=lambda x: x[1], reverse=True)[:5]
        except Exception:
            feat_imp = []

        return {
            'symbol':          symbol,
            'name':            STOCKS.get(symbol, {}).get('name', symbol),
            'data_date':       str(df['date'].iloc[-1]),
            'current_price':   round(current_price, 2),
            'predicted_price': round(pred_price, 2),
            'change':          round(change, 2),
            'change_pct':      round(change_pct, 2),
            'direction':       direction,
            'confidence':      round(confidence * 100, 1),
            'algorithm_used':  'XGBoost + Random Forest' if XGB_AVAILABLE else 'Random Forest',
            'metrics':         entry.get('metrics', {}),
            'top_features':    [{'feature': f, 'importance': round(i, 4)}
                                for f, i in feat_imp],
        }

    # ── Model Persistence ─────────────────────────────────────────────────────

    def _save_model(self, symbol: str, entry: dict):
        path = os.path.join(MODEL_DIR, f'{symbol}_model.pkl')
        joblib.dump(entry, path)

    def _load_all_models(self):
        if not os.path.isdir(MODEL_DIR):
            return
        for fname in os.listdir(MODEL_DIR):
            if fname.endswith('_model.pkl'):
                symbol = fname.replace('_model.pkl', '')
                path = os.path.join(MODEL_DIR, fname)
                try:
                    self._models[symbol] = joblib.load(path)
                    print(f"[ML] Loaded model: {symbol}")
                except Exception:
                    pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _model_is_stale(self, symbol: str, entry: dict) -> bool:
        """Detect artifacts trained from older data or a different database."""
        if entry.get('database_backend') != DATABASE_BACKEND or not entry.get('data_as_of'):
            return True
        latest = fetch_one(
            "SELECT MAX(date) AS date FROM stocks WHERE company=?", (symbol,)
        )
        return not latest or str(latest['date']) != entry['data_as_of']

    def _load_data(self, symbol: str) -> pd.DataFrame | None:
        rows = fetch_all(
            "SELECT date,open,high,low,close,volume,ma20,ma50,rsi,macd,signal "
            "FROM stocks WHERE company=? ORDER BY date ASC",
            (symbol,)
        )
        if not rows:
            return None
        df = pd.DataFrame(rows)
        for col in ['open','high','low','close','volume','ma20','ma50','rsi','macd','signal']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def _get_pagerank(self, symbol: str) -> float:
        """Retrieve PageRank score for a symbol (with fallback)."""
        try:
            from models.graph import StockGraph
            sg = StockGraph()
            scores = sg.get_pagerank_scores()
            return scores.get(symbol, 1.0 / len(STOCKS))
        except Exception:
            return 1.0 / len(STOCKS)

    def _fallback_prediction(self, symbol: str, reason: str) -> dict:
        """Return a simple moving-average-based prediction when ML fails."""
        rows = fetch_all(
            "SELECT date,close FROM stocks WHERE company=? ORDER BY date DESC LIMIT 20",
            (symbol,)
        )
        closes = [r['close'] for r in rows]
        current = closes[0] if closes else 0
        avg = sum(closes[:5]) / max(len(closes[:5]), 1)
        pred = avg * 1.002 if avg > current else avg * 0.998
        return {
            'symbol':          symbol,
            'name':            STOCKS.get(symbol, {}).get('name', symbol),
            'data_date':       rows[0]['date'] if rows else None,
            'current_price':   round(current, 2),
            'predicted_price': round(pred, 2),
            'change':          round(pred - current, 2),
            'change_pct':      round(((pred - current) / max(current, 1)) * 100, 2),
            'direction':       'UP' if pred > current else 'DOWN',
            'confidence':      50.0,
            'algorithm_used':  'Moving Average Fallback',
            'fallback_reason': reason,
            'metrics':         {},
            'top_features':    [],
        }


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    pm = PredictionModel()
    print("Training all models …")
    metrics = pm.train_all()
    print("\n=== Predictions ===")
    for key in STOCKS:
        try:
            r = pm.predict(key)
            print(f"{key:12s}  ₹{r['current_price']:>8.2f} → ₹{r['predicted_price']:>8.2f}"
                  f"  [{r['direction']:4s}]  Conf: {r['confidence']:.1f}%")
        except Exception as e:
            print(f"{key:12s}  ERROR: {e}")
