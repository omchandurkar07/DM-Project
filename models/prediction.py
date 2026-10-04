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
import sklearn

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

MODEL_VERSION = 3


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
        if symbol not in STOCKS:
            raise ValueError(f"Unknown stock symbol: {symbol}")

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
        y_return = (y_price / df['close'].values) - 1.0
        y_dir   = df['target_direction'].values

        # Keep a final chronological holdout untouched during model selection.
        test_start = int(len(X) * TRAIN_TEST_SPLIT)
        validation_start = int(test_start * TRAIN_TEST_SPLIT)
        if validation_start < 2 or validation_start >= test_start or test_start >= len(X):
            raise ValueError(f"Not enough feature rows to evaluate {symbol}")

        # ── Select a regressor using a validation window ───────────────
        selection_scaler = StandardScaler().fit(X[:validation_start])
        X_select_train = selection_scaler.transform(X[:validation_start])
        X_validation = selection_scaler.transform(X[validation_start:test_start])
        rf_reg = RandomForestRegressor(
            n_estimators=150, max_depth=12, min_samples_leaf=3,
            random_state=RANDOM_STATE, n_jobs=-1)
        rf_reg.fit(X_select_train, y_return[:validation_start])

        lr = LinearRegression()
        lr.fit(X_select_train, y_return[:validation_start])

        regressors = {
            'random_forest': rf_reg,
            'linear_regression': lr,
        }
        if XGB_AVAILABLE:
            xgb_reg = xgb.XGBRegressor(
                n_estimators=100, max_depth=6, learning_rate=0.05,
                random_state=RANDOM_STATE, verbosity=0, n_jobs=-1)
            xgb_reg.fit(X_select_train, y_return[:validation_start])
            regressors['xgboost'] = xgb_reg

        close_index = avail_cols.index('close')
        regressor_rmse = {
            name: float(np.sqrt(mean_squared_error(
                y_price[validation_start:test_start],
                X[validation_start:test_start, close_index]
                * (1.0 + model.predict(X_validation))
            )))
            for name, model in regressors.items()
        }
        best_regressor_name = min(regressor_rmse, key=regressor_rmse.get)
        best_regressor_rmse = regressor_rmse[best_regressor_name]
        validation_baseline_rmse = float(np.sqrt(mean_squared_error(
            y_price[validation_start:test_start],
            X[validation_start:test_start, close_index]
        )))
        selected_regressor_name = best_regressor_name

        # ── Evaluate the selected regressor on the untouched holdout ───
        test_scaler = StandardScaler().fit(X[:test_start])
        X_test_train = test_scaler.transform(X[:test_start])
        X_te = test_scaler.transform(X[test_start:])
        y_pr_te = y_price[test_start:]
        baseline_rmse = float(np.sqrt(mean_squared_error(
            y_pr_te, X[test_start:, close_index]
        )))
        if selected_regressor_name == 'persistence':
            rmse = baseline_rmse
        else:
            selected_regressor = regressors[selected_regressor_name]
            selected_regressor.fit(X_test_train, y_return[:test_start])
            predicted_test_prices = (
                X[test_start:, close_index]
                * (1.0 + selected_regressor.predict(X_te))
            )
            rmse = float(np.sqrt(mean_squared_error(
                y_pr_te, predicted_test_prices
            )))

        # ── Classifier holdout score and majority baseline ─────────────
        rf_cls = RandomForestClassifier(
            n_estimators=150, max_depth=10, min_samples_leaf=3,
            random_state=RANDOM_STATE, n_jobs=-1)
        rf_cls.fit(X_test_train, y_dir[:test_start])
        y_cls_pred = rf_cls.predict(X_te)
        accuracy = float(accuracy_score(y_dir[test_start:], y_cls_pred))
        baseline_direction = int(np.mean(y_dir[:test_start]) >= 0.5)
        baseline_accuracy = float(accuracy_score(
            y_dir[test_start:],
            np.full(len(y_dir[test_start:]), baseline_direction)
        ))

        # Refit the deployable models on all labeled rows after holdout evaluation.
        scaler = StandardScaler()
        scaler.fit(X)
        X_all_scaled = scaler.transform(X)
        for regressor in regressors.values():
            regressor.fit(X_all_scaled, y_return)
        rf_cls.fit(X_all_scaled, y_dir)

        # ── Store & Save ───────────────────────────────────────────────
        entry = {
            'model_version': MODEL_VERSION,
            'sklearn_version': sklearn.__version__,
            'reg':    regressors.get(selected_regressor_name),
            'regressor_name': selected_regressor_name,
            'rf_reg': rf_reg,
            'cls':    rf_cls,
            'lr':     lr,
            'scaler': scaler,
            'features': avail_cols,
            'data_as_of': data_as_of,
            'database_backend': DATABASE_BACKEND,
            'metrics': {'rmse': rmse, 'accuracy': accuracy,
                        'candidate_rmse': best_regressor_rmse,
                        'candidate_model': best_regressor_name,
                        'regression_model': selected_regressor_name,
                        'validation_baseline_rmse': validation_baseline_rmse,
                        'baseline_rmse': baseline_rmse,
                        'baseline_accuracy': baseline_accuracy,
                        'train_size': test_start, 'test_size': len(X_te)},
        }
        self._models[symbol] = entry
        self._save_model(symbol, entry)

        return entry['metrics']

    def predict(self, symbol: str) -> dict:
        """
        Return next-day price prediction and direction for a stock.
        Auto-trains if model not found.
        """
        if symbol not in STOCKS:
            raise ValueError(f"Unknown stock symbol: {symbol}")

        raw_df = self._load_data(symbol)
        if raw_df is None or raw_df.empty:
            raise ValueError(f"No historical stock data available for {symbol}")

        latest_history_date = str(raw_df['date'].iloc[-1])
        latest_quote = fetch_one(
            "SELECT date FROM market_quotes WHERE company=?", (symbol,)
        )
        if latest_quote and str(latest_quote['date']) > latest_history_date:
            from models.data_collector import DataCollector

            refresh = DataCollector().refresh_stock_history(symbol)
            raw_df = self._load_data(symbol)
            if raw_df is None or raw_df.empty:
                raise RuntimeError(f"History refresh returned no data for {symbol}")

            latest_history_date = str(raw_df['date'].iloc[-1])
            latest_quote = fetch_one(
                "SELECT date FROM market_quotes WHERE company=?", (symbol,)
            )
            if latest_quote and str(latest_quote['date']) > latest_history_date:
                raise RuntimeError(
                    f"Refreshed history for {symbol} ends on {latest_history_date}, "
                    f"but the latest market quote is {latest_quote['date']}"
                )
            print(
                f"[ML] Refreshed {refresh['rows']} historical rows for {symbol} "
                f"through {refresh['latest_date']}"
            )

        entry = self._models.get(symbol)
        if entry is None or self._model_is_stale(symbol, entry):
            self.train(symbol)

        entry = self._models[symbol]
        pagerank = self._get_pagerank(symbol)
        df = build_features(raw_df, pagerank, include_latest=True)
        if df.empty:
            raise ValueError(f"Unable to build prediction features for {symbol}")

        avail_cols = [c for c in entry['features'] if c in df.columns]
        last_row = df[avail_cols].iloc[-1:].values
        X_scaled = entry['scaler'].transform(last_row)

        # Price prediction
        if entry['reg'] is None:
            pred_price = float(df['close'].iloc[-1])
        else:
            predicted_return = float(entry['reg'].predict(X_scaled)[0])
            pred_price = float(df['close'].iloc[-1]) * (1.0 + predicted_return)
        current_price = float(df['close'].iloc[-1])
        displayed_price = round(pred_price, 2)
        displayed_current = round(current_price, 2)
        change = round(displayed_price - displayed_current, 2)
        change_pct = round((change / displayed_current) * 100, 2)

        if change > 0:
            direction = 'UP'
        elif change < 0:
            direction = 'DOWN'
        else:
            direction = 'HOLD'

        proba = entry['cls'].predict_proba(X_scaled)[0]
        classes = list(entry['cls'].classes_)
        prob_up = round(float(proba[classes.index(1)]), 4) if 1 in classes else 0.0
        prob_down = round(float(proba[classes.index(0)]), 4) if 0 in classes else 0.0
        confidence = (
            prob_up if direction == 'UP'
            else prob_down if direction == 'DOWN'
            else 0.5
        )

        history = raw_df.copy()
        history['date'] = pd.to_datetime(history['date'], errors='coerce')
        history['close'] = pd.to_numeric(history['close'], errors='coerce')
        history = history.dropna(subset=['date', 'close'])
        history = history[history['close'] > 0]
        latest_date = history['date'].max()
        period_start = latest_date - pd.Timedelta(days=365 * 2)
        period = history[history['date'] >= period_start]
        if period.empty:
            period = history.tail(1)

        period_closes = period['close']
        start_price = float(period_closes.iloc[0])
        end_price = float(period_closes.iloc[-1])
        period_return = ((end_price / start_price) - 1.0) * 100
        daily_returns = period_closes.pct_change().dropna()
        drawdowns = (period_closes / period_closes.cummax()) - 1.0

        performance = {
            'period_start': period['date'].iloc[0].date().isoformat(),
            'period_end': period['date'].iloc[-1].date().isoformat(),
            'observations': int(len(period)),
            'start_price': round(start_price, 2),
            'end_price': round(end_price, 2),
            'total_return_pct': round(float(period_return), 2),
            'highest_price': round(float(period['high'].max()), 2),
            'lowest_price': round(float(period['low'].min()), 2),
            'max_drawdown_pct': round(float(drawdowns.min() * 100), 2),
            'annualized_volatility_pct': (
                round(float(daily_returns.std(ddof=1) * np.sqrt(252) * 100), 2)
                if len(daily_returns) > 1 else None
            ),
            'outlook_price': displayed_price,
            'outlook_change_pct': change_pct,
            'outlook_direction': direction,
            'outlook_confidence_pct': round(confidence * 100, 1),
        }

        # Feature importances (top 5)
        try:
            fi = entry['rf_reg'].feature_importances_
            feat_imp = sorted(zip(avail_cols, fi), key=lambda x: x[1], reverse=True)[:5]
        except Exception:
            feat_imp = []

        # ── Indicators from the latest row ─────────────────────────────
        last = df.iloc[-1]

        def _safe_float(val, decimals=2):
            """Return rounded float or None; handles NaN safely."""
            try:
                v = float(val)
                return None if (v != v) else round(v, decimals)
            except Exception:
                return None

        # Volatility: 20-day rolling std of prices → convert to return-based std
        vol_raw = _safe_float(last.get('vol_20', None), 6)
        if vol_raw is not None and current_price > 0:
            volatility = round(vol_raw / current_price, 6)   # proportion (e.g. 0.021)
        else:
            volatility = None

        # Daily price change % from previous close
        ret_lag1 = _safe_float(last.get('return_lag_1', None), 6)
        price_change = round(ret_lag1 * 100, 4) if ret_lag1 is not None else None

        indicators = {
            'ma20':         _safe_float(last['ma20'],   2) if 'ma20'  in df.columns else None,
            'ma50':         _safe_float(last['ma50'],   2) if 'ma50'  in df.columns else None,
            'rsi':          _safe_float(last['rsi'],    2) if 'rsi'   in df.columns else None,
            'macd':         _safe_float(last['macd'],   4) if 'macd'  in df.columns else None,
            'volatility':   volatility,
            'price_change': price_change,
        }

        return {
            'symbol':          symbol,
            'name':            STOCKS.get(symbol, {}).get('name', symbol),
            'data_date':       str(df['date'].iloc[-1]),
            'current_price':   displayed_current,
            'predicted_price': displayed_price,
            'change':          change,
            'change_pct':      change_pct,
            'direction':       direction,
            'performance':     performance,
            'confidence':      round(confidence, 4),           # 0.0–1.0 float
            'confidence_pct':  round(confidence * 100, 1),    # for display (e.g. 73.0)
            'classifier_direction': 'UP' if prob_up >= prob_down else 'DOWN',
            'probability': {
                'up':   prob_up,
                'down': prob_down,
            },
            'indicators':      indicators,
            'algorithm_used':  (
                f"{entry['regressor_name'].replace('_', ' ').title()} "
                "+ Random Forest classifier"
            ),
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
        if (
            entry.get('model_version') != MODEL_VERSION
            or entry.get('sklearn_version') != sklearn.__version__
            or entry.get('database_backend') != DATABASE_BACKEND
            or not entry.get('data_as_of')
        ):
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
