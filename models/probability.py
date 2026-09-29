"""
models/probability.py
=====================
Frequentist + Bayesian probability engine for stock price direction.

Frequentist:
    P(Up) = number of days price rose / total trading days (100-day window)

Bayesian Update:
    posterior = (likelihood × prior) / evidence
    Applied when external signals (news, market event) are provided.
"""

import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import STOCKS, LOOKBACK_DAYS
from database import fetch_all


class ProbabilityEngine:
    """
    Computes and updates stock movement probabilities using
    Frequentist and Bayesian methods.
    """

    # ── Public API ────────────────────────────────────────────────────────────

    def get_probability(self, symbol: str, event: str | None = None) -> dict:
        """
        Main entry: returns P(Up), P(Down), and optional Bayesian update.

        Parameters
        ----------
        symbol : Stock key (e.g. 'TCS')
        event  : Optional signal — 'positive', 'negative', or None
        """
        rows = fetch_all(
            "SELECT close FROM stocks WHERE company=? ORDER BY date DESC LIMIT ?",
            (symbol, LOOKBACK_DAYS)
        )

        if len(rows) < 5:
            # Not enough history — return neutral
            return self._neutral(symbol)

        closes = [r['close'] for r in reversed(rows)]  # oldest first
        p_up, p_down, n_up, n_down = self._frequentist(closes)

        result = {
            'symbol':   symbol,
            'name':     STOCKS.get(symbol, {}).get('name', symbol),
            'p_up':     round(p_up, 4),
            'p_down':   round(p_down, 4),
            'p_up_pct': round(p_up * 100, 2),
            'p_down_pct': round(p_down * 100, 2),
            'days_up':   n_up,
            'days_down': n_down,
            'total_days': n_up + n_down,
            'window':    LOOKBACK_DAYS,
            'method':    'Frequentist',
            'event':     event,
        }

        if event:
            posterior_up   = self._bayesian_update(p_up, event, direction='up')
            posterior_down = 1.0 - posterior_up
            result.update({
                'p_up_prior':   round(p_up, 4),
                'p_up_posterior': round(posterior_up, 4),
                'p_up_pct':      round(posterior_up * 100, 2),
                'p_down_pct':    round(posterior_down * 100, 2),
                'method': 'Bayesian',
            })

        result['signal'] = self._signal(result['p_up_pct'])
        result['trend']  = self._trend_analysis(closes)

        return result

    def get_all_probabilities(self) -> dict:
        """Return probability dict for all stocks."""
        return {k: self.get_probability(k) for k in STOCKS}

    def bayesian_update(self, symbol: str, event: str) -> dict:
        """Convenience: get Bayesian-updated probability for a symbol."""
        return self.get_probability(symbol, event=event)

    # ── Core Calculations ─────────────────────────────────────────────────────

    def _frequentist(self, closes: list[float]):
        """
        Count days where close[t] > close[t-1].

        Returns (p_up, p_down, n_up, n_down)
        """
        changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        n_up    = sum(1 for c in changes if c > 0)
        n_down  = sum(1 for c in changes if c <= 0)
        total   = n_up + n_down
        if total == 0:
            return 0.5, 0.5, 0, 0
        p_up   = n_up   / total
        p_down = n_down / total
        return p_up, p_down, n_up, n_down

    def _bayesian_update(self, prior: float, event: str, direction: str = 'up') -> float:
        """
        Simple Bayesian update using a Gaussian likelihood model.

        Likelihood table:
            event='positive' → P(positive | Up) = 0.80, P(positive | Down) = 0.30
            event='negative' → P(positive | Up) = 0.25, P(positive | Down) = 0.75
            event='neutral'  → 0.50 / 0.50

        posterior = P(E|Up)*P(Up) / [P(E|Up)*P(Up) + P(E|Down)*P(Down)]
        """
        likelihoods = {
            'positive': {'up': 0.80, 'down': 0.30},
            'negative': {'up': 0.25, 'down': 0.75},
            'neutral':  {'up': 0.50, 'down': 0.50},
        }
        lk = likelihoods.get(event.lower(), likelihoods['neutral'])
        p_prior_up   = prior
        p_prior_down = 1.0 - prior

        numerator   = lk['up']   * p_prior_up
        denominator = (lk['up']  * p_prior_up + lk['down'] * p_prior_down)

        if denominator == 0:
            return 0.5
        return np.clip(numerator / denominator, 0.0, 1.0)

    def _trend_analysis(self, closes: list[float]) -> dict:
        """
        Quick trend summary:
          - 5-day trend, 20-day trend
          - Volatility (std of daily returns)
          - Momentum
        """
        arr = np.array(closes)
        returns = np.diff(arr) / (arr[:-1] + 1e-9)

        def pct_change(window):
            if len(arr) >= window:
                return round(((arr[-1] - arr[-window]) / arr[-window]) * 100, 2)
            return 0.0

        return {
            'trend_5d':    pct_change(5),
            'trend_20d':   pct_change(20),
            'volatility':  round(float(np.std(returns[-20:]) * 100), 3) if len(returns) >= 20 else 0,
            'momentum':    round(float(np.mean(returns[-5:])) * 100, 3) if len(returns) >= 5 else 0,
            'latest_close': round(float(closes[-1]), 2),
        }

    def _signal(self, p_up_pct: float) -> str:
        """Convert probability to trading signal."""
        if p_up_pct >= 75:
            return 'STRONG BUY'
        if p_up_pct >= 60:
            return 'BUY'
        if p_up_pct >= 45:
            return 'HOLD'
        if p_up_pct >= 30:
            return 'SELL'
        return 'STRONG SELL'

    def _neutral(self, symbol: str) -> dict:
        """Return neutral 50/50 when data is insufficient."""
        return {
            'symbol':     symbol,
            'name':       STOCKS.get(symbol, {}).get('name', symbol),
            'p_up':       0.50,
            'p_down':     0.50,
            'p_up_pct':   50.0,
            'p_down_pct': 50.0,
            'days_up':    0,
            'days_down':  0,
            'total_days': 0,
            'window':     LOOKBACK_DAYS,
            'method':     'Neutral (insufficient data)',
            'event':      None,
            'signal':     'HOLD',
            'trend':      {'trend_5d': 0, 'trend_20d': 0,
                           'volatility': 0, 'momentum': 0, 'latest_close': 0},
        }


# ── CLI ───────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    pe = ProbabilityEngine()
    for key in STOCKS:
        r = pe.get_probability(key)
        print(f"{key:12s}  P(Up)={r['p_up_pct']:5.1f}%  "
              f"P(Down)={r['p_down_pct']:5.1f}%  Signal: {r['signal']}")

    print("\n--- Bayesian update for TCS (positive news) ---")
    r = pe.get_probability('TCS', event='positive')
    print(f"  Prior P(Up): {r.get('p_up_prior', 0)*100:.1f}%")
    print(f"  Posterior P(Up): {r['p_up_pct']:.1f}%")
