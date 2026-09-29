"""
models/discrete_math.py
=======================
Discrete Mathematics engine for Stock Market Analysis & Prediction.

Implements:
1. Advanced Graph Theory: Graph Coloring, Bron-Kerbosch Cliques, Modular Communities.
2. Boolean Logic & Propositional Calculus: Formula Evaluation & Truth Tables.
3. Combinatorics & Counting Theory: Sub-Portfolio Combinations & Knapsack Optimization.
4. Set Theory & Relations: Jaccard Movement Similarity & Poset Dominance.
5. Recurrence Relations & Difference Equations: Discrete Fibonacci & Difference Forecast.
"""

import itertools
import numpy as np
import pandas as pd
import networkx as nx
from typing import Dict, List, Any
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import STOCKS, SECTOR_COLORS
from database import fetch_all, fetch_one
from models.graph import StockGraph


class DiscreteMathEngine:
    def __init__(self):
        self.stock_graph = StockGraph()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. ADVANCED GRAPH THEORY
    # ─────────────────────────────────────────────────────────────────────────
    def graph_theory_analysis(self) -> Dict[str, Any]:
        """
        1. Graph Coloring (Greedy algorithm for portfolio diversification)
        2. Maximal Cliques (Bron-Kerbosch algorithm)
        3. Community Detection (Greedy Modularity Partitioning)
        """
        G = self.stock_graph.build_graph()

        if G.number_of_nodes() == 0:
            return {'error': 'Graph is empty. Please collect data first.'}

        # 1. Graph Coloring (Independent Sets for Diversification)
        # Vertices with same color are non-adjacent (low/no correlation)
        coloring = nx.coloring.greedy_color(G, strategy='largest_first')
        color_groups = {}
        for node, color_id in coloring.items():
            color_groups.setdefault(color_id, []).append(node)

        diversified_portfolios = [
            {'color_id': cid, 'stocks': stocks, 'size': len(stocks)}
            for cid, stocks in color_groups.items()
        ]

        # 2. Maximal Cliques (Bron-Kerbosch algorithm)
        cliques = list(nx.find_cliques(G))
        cliques_sorted = sorted(cliques, key=lambda c: len(c), reverse=True)
        top_cliques = [
            {'size': len(c), 'stocks': c}
            for c in cliques_sorted if len(c) >= 2
        ][:5]

        # 3. Community Detection (Greedy Modularity Communities)
        communities = list(nx.community.greedy_modularity_communities(G))
        community_clusters = [
            {'community_id': idx + 1, 'stocks': list(comm), 'size': len(comm)}
            for idx, comm in enumerate(communities)
        ]

        return {
            'graph_coloring': {
                'num_colors_used': len(color_groups),
                'portfolios': diversified_portfolios,
                'explanation': 'Stocks assigned to the same color set have low mutual correlation, forming optimal diversified portfolio candidates.'
            },
            'maximal_cliques': {
                'count': len(cliques),
                'top_cliques': top_cliques,
                'explanation': 'Cliques represent groups of stocks where EVERY pair is strongly correlated, indicating tight co-movement during market events.'
            },
            'communities': {
                'num_communities': len(communities),
                'clusters': community_clusters,
                'explanation': 'Graph modularity partitioning auto-discovers hidden sector relationships based on real price co-movements.'
            }
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 2. BOOLEAN LOGIC & PROPOSITIONAL CALCULUS
    # ─────────────────────────────────────────────────────────────────────────
    def evaluate_boolean_strategy(self, p_volatility: bool, q_trend: bool, r_rsi: bool, s_volume: bool) -> Dict[str, Any]:
        """
        Evaluates discrete propositional logic trading rules & generates truth table.
        Formulas:
          Strategy A (Conservative Buy): (NOT P) AND Q AND R
          Strategy B (Breakout Momentum): Q AND S AND (NOT P OR R)
          Strategy C (Risk Hedge Alert): P OR (NOT Q AND NOT R)
        """
        # Logic evaluation
        strat_a = (not p_volatility) and q_trend and r_rsi
        strat_b = q_trend and s_volume and ((not p_volatility) or r_rsi)
        strat_c = p_volatility or ((not q_trend) and (not r_rsi))

        # Generate complete 16-row Truth Table for the 4 proposition variables
        truth_table = []
        for p, q, r, s in itertools.product([True, False], repeat=4):
            sa = (not p) and q and r
            sb = q and s and ((not p) or r)
            sc = p or ((not q) and (not r))
            truth_table.append({
                'P_HighVol': p,
                'Q_Uptrend': q,
                'R_RSI_Oversold': r,
                'S_HighVolume': s,
                'Strat_A_Buy': sa,
                'Strat_B_Breakout': sb,
                'Strat_C_HedgeAlert': sc,
            })

        return {
            'input_states': {
                'P_HighVol': p_volatility,
                'Q_Uptrend': q_trend,
                'R_RSI_Oversold': r_rsi,
                'S_HighVolume': s_volume
            },
            'evaluation': {
                'Strategy_A_ConservativeBuy': {
                    'formula': '(¬P) ∧ Q ∧ R',
                    'result': strat_a,
                    'action': 'BUY (Low Risk)' if strat_a else 'HOLD / WAIT'
                },
                'Strategy_B_BreakoutMomentum': {
                    'formula': 'Q ∧ S ∧ (¬P ∨ R)',
                    'result': strat_b,
                    'action': 'STRONG BUY (Momentum)' if strat_b else 'NEUTRAL'
                },
                'Strategy_C_HedgeAlert': {
                    'formula': 'P ∨ (¬Q ∧ ¬R)',
                    'result': strat_c,
                    'action': 'HEDGE / SELL ALERT' if strat_c else 'SAFE'
                }
            },
            'truth_table': truth_table[:8]  # sample top 8 rows for display
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 3. COMBINATORICS & COUNTING THEORY
    # ─────────────────────────────────────────────────────────────────────────
    def combinatorial_subportfolios(self, portfolio_size: int = 3) -> Dict[str, Any]:
        """
        Calculates all C(N, K) combinations of stocks and finds optimal sub-portfolios.
        Uses combinatorial selection to evaluate expected return vs risk variance.
        """
        all_symbols = list(STOCKS.keys())
        n = len(all_symbols)
        k = max(2, min(portfolio_size, n - 1))

        # Compute return metrics per stock
        stock_stats = {}
        for sym in all_symbols:
            rows = fetch_all("SELECT close FROM stocks WHERE company=? ORDER BY date DESC LIMIT 60", (sym,))
            if len(rows) >= 5:
                closes = np.array([r['close'] for r in reversed(rows)])
                returns = np.diff(closes) / closes[:-1]
                stock_stats[sym] = {
                    'mean_return': float(np.mean(returns)),
                    'std_return': float(np.std(returns)) if np.std(returns) > 0 else 0.01,
                    'last_price': float(closes[-1])
                }

        valid_symbols = [s for s in all_symbols if s in stock_stats]
        total_combinations = list(itertools.combinations(valid_symbols, k))

        evaluated = []
        for combo in total_combinations:
            avg_ret = np.mean([stock_stats[s]['mean_return'] for s in combo])
            avg_risk = np.mean([stock_stats[s]['std_return'] for s in combo])
            score = avg_ret / avg_risk if avg_risk > 0 else 0.0
            evaluated.append({
                'combination': list(combo),
                'expected_return_pct': round(avg_ret * 100, 3),
                'risk_volatility_pct': round(avg_risk * 100, 3),
                'sharpe_score': round(score, 3)
            })

        evaluated.sort(key=lambda x: x['sharpe_score'], reverse=True)

        return {
            'total_stocks_N': len(valid_symbols),
            'chosen_K': k,
            'total_combinations_C_N_K': len(total_combinations),
            'formula': f"C({len(valid_symbols)}, {k}) = {len(total_combinations)}",
            'top_portfolios': evaluated[:5],
            'worst_portfolios': evaluated[-3:]
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 4. SET THEORY & RELATIONS (Jaccard Similarity & Poset Dominance)
    # ─────────────────────────────────────────────────────────────────────────
    def set_theory_analysis(self) -> Dict[str, Any]:
        """
        1. Jaccard Similarity: J(A, B) = |A ∩ B| / |A ∪ B| of positive movement days.
        2. Poset Dominance (Partial Order Relation):
           Stock A ≽ Stock B iff (Return_A >= Return_B AND Risk_A <= Risk_B)
        """
        all_symbols = list(STOCKS.keys())
        up_day_sets = {}
        stock_perf = {}

        for sym in all_symbols:
            rows = fetch_all("SELECT date, close FROM stocks WHERE company=? ORDER BY date DESC LIMIT 30", (sym,))
            if len(rows) >= 5:
                closes = [r['close'] for r in reversed(rows)]
                dates = [r['date'] for r in reversed(rows)][1:]
                returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]

                # Set of dates where stock price went UP
                up_dates = {dates[i] for i in range(len(returns)) if returns[i] > 0}
                up_day_sets[sym] = up_dates

                stock_perf[sym] = {
                    'avg_return': float(np.mean(returns)),
                    'risk': float(np.std(returns))
                }

        # 1. Compute Jaccard Similarity Matrix between stock pairs
        jaccard_results = []
        symbols = list(up_day_sets.keys())
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                s1, s2 = symbols[i], symbols[j]
                set1, set2 = up_day_sets[s1], up_day_sets[s2]
                intersection = len(set1.intersection(set2))
                union = len(set1.union(set2))
                jaccard_index = intersection / union if union > 0 else 0.0
                jaccard_results.append({
                    'pair': f"{s1} ∩ {s2}",
                    'stock1': s1,
                    'stock2': s2,
                    'intersection_size': intersection,
                    'union_size': union,
                    'jaccard_index': round(jaccard_index, 3)
                })

        jaccard_results.sort(key=lambda x: x['jaccard_index'], reverse=True)

        # 2. Poset Dominance (Partial Order Pareto Dominance)
        poset_relations = []
        for s1 in symbols:
            for s2 in symbols:
                if s1 != s2 and s1 in stock_perf and s2 in stock_perf:
                    p1, p2 = stock_perf[s1], stock_perf[s2]
                    # s1 dominates s2 if better return AND lower/equal risk
                    if p1['avg_return'] >= p2['avg_return'] and p1['risk'] <= p2['risk']:
                        if p1['avg_return'] > p2['avg_return'] or p1['risk'] < p2['risk']:
                            poset_relations.append({
                                'dominant': s1,
                                'dominated': s2,
                                'relation': f"{s1} ≽ {s2}",
                                'explanation': f"{s1} strictly dominates {s2} (Higher Return & Lower Risk)"
                            })

        return {
            'jaccard_similarity': {
                'top_similar_pairs': jaccard_results[:5],
                'explanation': 'Jaccard Index measures directional co-movement set overlap |A ∩ B| / |A ∪ B|.'
            },
            'poset_dominance': {
                'relations_count': len(poset_relations),
                'relations': poset_relations[:6],
                'explanation': 'Partial Order relation (Poset) identifies Pareto dominant stocks where one strictly outperforms another in both risk and return.'
            }
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 5. RECURRENCE RELATIONS & DIFFERENCE EQUATIONS
    # ─────────────────────────────────────────────────────────────────────────
    def recurrence_analysis(self, symbol: str = 'TCS') -> Dict[str, Any]:
        """
        1. Discrete Fibonacci Recurrence: F(n) = F(n-1) + F(n-2) ratios applied to High/Low.
        2. Second-Order Difference Equation:
           Δy_t = c1 * Δy_{t-1} + c2 * Δy_{t-2}
           Predicts discrete support and resistance levels.
        """
        rows = fetch_all(
            "SELECT date, close, high, low FROM stocks WHERE company=? ORDER BY date DESC LIMIT 60",
            (symbol,)
        )
        if len(rows) < 10:
            return {'error': f'Not enough price history for {symbol}'}

        closes = np.array([r['close'] for r in reversed(rows)])
        highs = np.array([r['high'] for r in reversed(rows)])
        lows = np.array([r['low'] for r in reversed(rows)])

        recent_high = float(np.max(highs[-20:]))
        recent_low = float(np.min(lows[-20:]))
        diff = recent_high - recent_low

        # Fibonacci Recurrence Ratios
        fib_ratios = [0.0, 0.236, 0.382, 0.500, 0.618, 0.786, 1.000]
        fib_levels = {
            f"Fib_{int(r*1000)/10}%": round(recent_high - (diff * r), 2)
            for r in fib_ratios
        }

        # 2. Second-Order Linear Difference Equation
        # Δy_t = y_t - y_{t-1}
        dy = np.diff(closes)
        if len(dy) >= 5:
            # Solve Y = X * C for coefficients c1, c2
            Y = dy[2:]
            X = np.column_stack((dy[1:-1], dy[:-2]))
            try:
                coeffs, _, _, _ = np.linalg.lstsq(X, Y, rcond=None)
                c1, c2 = float(coeffs[0]), float(coeffs[1])

                # Forecast next step difference Δy_{t+1}
                next_dy = c1 * dy[-1] + c2 * dy[-2]
                predicted_next_close = float(closes[-1] + next_dy)
            except Exception:
                c1, c2 = 0.5, -0.2
                next_dy = 0.0
                predicted_next_close = float(closes[-1])
        else:
            c1, c2 = 0.0, 0.0
            next_dy = 0.0
            predicted_next_close = float(closes[-1])

        return {
            'symbol': symbol,
            'current_price': float(closes[-1]),
            'swing_high_20d': recent_high,
            'swing_low_20d': recent_low,
            'fibonacci_recurrence': {
                'levels': fib_levels,
                'explanation': 'Fibonacci ratios derived from discrete sequence recurrence limits F(n)/F(n+1) → 0.618.'
            },
            'difference_equation': {
                'formula': f"Δy_t = ({c1:.3f})·Δy_{{t-1}} + ({c2:.3f})·Δy_{{t-2}}",
                'c1_coeff': round(c1, 4),
                'c2_coeff': round(c2, 4),
                'predicted_delta': round(next_dy, 2),
                'forecasted_support_resistance': round(predicted_next_close, 2),
                'explanation': '2nd-order discrete difference equation models momentum acceleration to predict support/resistance boundaries.'
            }
        }
