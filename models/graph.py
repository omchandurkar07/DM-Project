"""
models/graph.py
===============
Builds a weighted undirected graph of stocks using Pearson correlation
of daily returns as edge weights.

Implements DSA algorithms:
  • BFS  — breadth-first traversal (find nearby companies)
  • DFS  — depth-first traversal (sector dependency)
  • Dijkstra — strongest influence path
  • PageRank  — most influential company
  • MST (Kruskal) — minimum spanning tree of influence network

Uses NetworkX as the underlying graph library.
"""

import os
import sys
import numpy as np
import pandas as pd
import networkx as nx
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import STOCKS, SECTOR_COLORS, CORRELATION_THRESHOLD
from database import get_connection, execute_query, fetch_all


class StockGraph:
    """
    Manages the stock correlation graph and exposes graph algorithms
    as JSON-serialisable results for the Flask API.
    """

    def __init__(self):
        self.G: nx.Graph = nx.Graph()
        self.pagerank_scores: dict = {}
        self._try_load_graph()

    # ────────────────────────────────────────────────────────────────────────
    # Graph Construction
    # ────────────────────────────────────────────────────────────────────────

    def build_graph(self) -> nx.Graph:
        """
        1. Load close prices for all companies from DB.
        2. Compute pairwise Pearson correlation of daily returns.
        3. Create edges where |correlation| >= CORRELATION_THRESHOLD.
        4. Persist edges to graph_edges table.
        5. Compute PageRank.
        """
        close_df = self._load_close_prices()
        if close_df.empty or len(close_df.columns) < 2:
            print("[Graph] Not enough data to build graph — using static graph")
            self._build_static_graph()
            return self.G

        # Daily percentage returns
        returns = close_df.pct_change().dropna()
        corr    = returns.corr()

        self.G = nx.Graph()

        # Add nodes
        for key, info in STOCKS.items():
            if key in close_df.columns:
                self.G.add_node(key,
                                name=info['name'],
                                sector=info['sector'],
                                color=info.get('color', '#FFFFFF'))

        # Clear old edges
        execute_query("DELETE FROM graph_edges")

        # Add edges
        companies = list(close_df.columns)
        for i in range(len(companies)):
            for j in range(i + 1, len(companies)):
                a, b = companies[i], companies[j]
                if a not in corr.index or b not in corr.columns:
                    continue
                weight = corr.loc[a, b]
                if np.isnan(weight):
                    continue
                abs_w = abs(weight)
                if abs_w >= CORRELATION_THRESHOLD:
                    edge_type = self._edge_type(a, b, weight)
                    self.G.add_edge(a, b, weight=abs_w,
                                    correlation=weight, edge_type=edge_type)
                    execute_query(
                        "INSERT OR REPLACE INTO graph_edges "
                        "(company_a, company_b, weight, edge_type) VALUES (?,?,?,?)",
                        (a, b, round(abs_w, 4), edge_type)
                    )

        # PageRank (handle disconnected graph)
        try:
            self.pagerank_scores = nx.pagerank(self.G, alpha=0.85, max_iter=300)
        except Exception:
            self.pagerank_scores = {n: 1/len(self.G.nodes) for n in self.G.nodes}

        print(f"[Graph] Built: {self.G.number_of_nodes()} nodes, "
              f"{self.G.number_of_edges()} edges")
        return self.G

    # ────────────────────────────────────────────────────────────────────────
    # Graph Algorithms
    # ────────────────────────────────────────────────────────────────────────

    def bfs(self, start: str) -> dict:
        """
        Breadth-First Search from start_node.
        Returns traversal order, level (hop) of each node, and edges traversed.
        """
        if start not in self.G:
            return {'error': f'{start} not in graph', 'order': [], 'levels': {}}

        visited  = {}   # node → level
        queue    = deque([(start, 0)])
        order    = []
        edges    = []

        while queue:
            node, level = queue.popleft()
            if node in visited:
                continue
            visited[node] = level
            order.append({'node': node, 'level': level,
                          'name': STOCKS.get(node, {}).get('name', node)})

            for neighbor in sorted(self.G.neighbors(node)):
                if neighbor not in visited:
                    queue.append((neighbor, level + 1))
                    edges.append({'source': node, 'target': neighbor})

        return {
            'algorithm': 'BFS',
            'start': start,
            'order': order,
            'edges': edges,
            'description': (
                f'BFS from {start}: Explores all companies reachable '
                f'within increasing "hops" of correlation distance.'
            )
        }

    def dfs(self, start: str) -> dict:
        """
        Depth-First Search from start_node.
        Returns traversal order and tree edges.
        """
        if start not in self.G:
            return {'error': f'{start} not in graph', 'order': [], 'edges': []}

        visited = set()
        order   = []
        edges   = []

        def _dfs(node, depth=0):
            visited.add(node)
            order.append({'node': node, 'depth': depth,
                          'name': STOCKS.get(node, {}).get('name', node)})
            for neighbor in sorted(self.G.neighbors(node)):
                if neighbor not in visited:
                    edges.append({'source': node, 'target': neighbor})
                    _dfs(neighbor, depth + 1)

        _dfs(start)
        return {
            'algorithm': 'DFS',
            'start': start,
            'order': order,
            'edges': edges,
            'description': (
                f'DFS from {start}: Deeply explores one sector branch '
                f'before backtracking — useful for dependency chains.'
            )
        }

    def dijkstra(self, source: str, target: str) -> dict:
        """
        Shortest path by Dijkstra (using inverted weights so high
        correlation = short distance = strong influence).
        """
        if source not in self.G or target not in self.G:
            missing = source if source not in self.G else target
            return {'error': f'{missing} not in graph'}

        # Build inverted-weight graph
        inv_G = nx.Graph()
        for u, v, data in self.G.edges(data=True):
            w = data.get('weight', 0.5)
            inv_G.add_edge(u, v, weight=1.0 - w + 0.001)

        try:
            path = nx.dijkstra_path(inv_G, source, target, weight='weight')
            length = nx.dijkstra_path_length(inv_G, source, target, weight='weight')
        except nx.NetworkXNoPath:
            return {
                'algorithm': 'Dijkstra',
                'error': f'No path between {source} and {target}',
                'path': [], 'total_distance': None
            }

        path_info = []
        for i, node in enumerate(path):
            info = {'node': node, 'name': STOCKS.get(node, {}).get('name', node)}
            if i > 0:
                w = self.G.edges[path[i-1], node].get('weight', 0)
                info['correlation'] = round(w, 4)
            path_info.append(info)

        return {
            'algorithm': 'Dijkstra',
            'source': source, 'target': target,
            'path': path_info,
            'path_nodes': path,
            'total_distance': round(length, 4),
            'description': (
                f'Strongest influence path from {source} → {target}. '
                f'High correlation = short "influence distance".'
            )
        }

    def pagerank(self) -> dict:
        """PageRank scores — identifies most influential companies."""
        if not self.pagerank_scores:
            try:
                self.pagerank_scores = nx.pagerank(self.G, alpha=0.85)
            except Exception:
                self.pagerank_scores = {n: 1/max(len(self.G.nodes), 1)
                                        for n in self.G.nodes}

        ranked = sorted(self.pagerank_scores.items(), key=lambda x: x[1], reverse=True)
        return {
            'algorithm': 'PageRank',
            'scores': [
                {
                    'rank': i + 1,
                    'node': node,
                    'name': STOCKS.get(node, {}).get('name', node),
                    'sector': STOCKS.get(node, {}).get('sector', ''),
                    'score': round(score, 6),
                    'score_pct': round(score * 100, 3),
                }
                for i, (node, score) in enumerate(ranked)
            ],
            'description': (
                'PageRank measures which company has the most influence '
                'on others in the correlation network.'
            )
        }

    def minimum_spanning_tree(self) -> dict:
        """
        Kruskal's MST on the negated-weight graph so highest-correlation
        edges are kept (minimum cost = maximum correlation).
        """
        if self.G.number_of_edges() == 0:
            return {'algorithm': 'MST', 'edges': [], 'nodes': []}

        # Negate weights: we want max-weight spanning tree
        neg_G = nx.Graph()
        for u, v, data in self.G.edges(data=True):
            neg_G.add_edge(u, v, weight=1.0 - data.get('weight', 0))

        mst = nx.minimum_spanning_tree(neg_G, algorithm='kruskal')

        edges = []
        for u, v, data in mst.edges(data=True):
            orig_w = self.G.edges[u, v].get('weight', 0)
            edges.append({
                'source': u, 'target': v,
                'weight': round(orig_w, 4),
                'correlation': round(self.G.edges[u, v].get('correlation', orig_w), 4),
            })

        nodes = [
            {'node': n, 'name': STOCKS.get(n, {}).get('name', n),
             'sector': STOCKS.get(n, {}).get('sector', '')}
            for n in mst.nodes()
        ]

        return {
            'algorithm': 'MST (Kruskal)',
            'edges': sorted(edges, key=lambda x: x['weight'], reverse=True),
            'nodes': nodes,
            'edge_count': len(edges),
            'description': (
                "Minimum Spanning Tree (max-correlation variant) — "
                "the minimal network that keeps all companies connected "
                "through their strongest correlation links."
            )
        }

    # ────────────────────────────────────────────────────────────────────────
    # D3.js JSON Serialisation
    # ────────────────────────────────────────────────────────────────────────

    def get_graph_json(self) -> dict:
        """
        Return nodes and links in D3-force format.
        Rebuilds graph if empty.
        """
        if self.G.number_of_nodes() == 0:
            self.build_graph()

        nodes = []
        for node, data in self.G.nodes(data=True):
            pr   = self.pagerank_scores.get(node, 0)
            nodes.append({
                'id':     node,
                'name':   data.get('name', node),
                'sector': data.get('sector', ''),
                'color':  data.get('color', SECTOR_COLORS.get(data.get('sector', ''), '#888')),
                'pagerank': round(pr, 6),
                'size':   12 + pr * 300,   # visual size proportional to PageRank
            })

        links = []
        for u, v, data in self.G.edges(data=True):
            links.append({
                'source':      u,
                'target':      v,
                'weight':      round(data.get('weight', 0), 4),
                'correlation': round(data.get('correlation', 0), 4),
                'edge_type':   data.get('edge_type', ''),
            })

        return {
            'nodes': nodes,
            'links': links,
            'pagerank': {k: round(v, 6) for k, v in self.pagerank_scores.items()},
            'stats': {
                'node_count': self.G.number_of_nodes(),
                'edge_count': self.G.number_of_edges(),
                'density':    round(nx.density(self.G), 4) if self.G.number_of_nodes() > 1 else 0,
            }
        }

    def get_pagerank_scores(self) -> dict:
        """Return pagerank scores (build if needed)."""
        if not self.pagerank_scores:
            self.build_graph()
        return self.pagerank_scores

    # ────────────────────────────────────────────────────────────────────────
    # Private Helpers
    # ────────────────────────────────────────────────────────────────────────

    def _load_close_prices(self) -> pd.DataFrame:
        """Pivot close prices: index=date, columns=company."""
        rows = fetch_all("SELECT company, date, close FROM stocks ORDER BY date")
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        pivot = df.pivot(index='date', columns='company', values='close')
        pivot.index = pd.to_datetime(pivot.index)
        return pivot.dropna(how='all')

    def _edge_type(self, a: str, b: str, corr: float) -> str:
        """Classify edge type from sector information."""
        sec_a = STOCKS.get(a, {}).get('sector', '')
        sec_b = STOCKS.get(b, {}).get('sector', '')
        if sec_a == sec_b:
            return 'Same Sector'
        if corr > 0.7:
            return 'High Correlation'
        if corr > 0.5:
            return 'Moderate Correlation'
        return 'Weak Correlation'

    def _try_load_graph(self):
        """On startup, try to build graph from existing DB data."""
        try:
            rows = fetch_all("SELECT company_a, company_b, weight, edge_type FROM graph_edges")
            if rows:
                for key, info in STOCKS.items():
                    self.G.add_node(key, name=info['name'],
                                    sector=info['sector'], color=info.get('color', '#FFF'))
                for r in rows:
                    self.G.add_edge(r['company_a'], r['company_b'],
                                    weight=r['weight'], edge_type=r['edge_type'])
                try:
                    self.pagerank_scores = nx.pagerank(self.G, alpha=0.85)
                except Exception:
                    pass
                print(f"[Graph] Loaded from DB: {self.G.number_of_nodes()} nodes, "
                      f"{self.G.number_of_edges()} edges")
            else:
                self.build_graph()
        except Exception as e:
            print(f"[Graph] Could not load from DB: {e}")

    def _build_static_graph(self):
        """Fallback: manually defined edges based on domain knowledge."""
        for key, info in STOCKS.items():
            self.G.add_node(key, name=info['name'],
                            sector=info['sector'], color=info.get('color', '#FFF'))

        # IT sector cluster
        for a, b, w in [
            ('TCS', 'INFY', 0.82), ('TCS', 'WIPRO', 0.74),
            ('INFY', 'WIPRO', 0.71),
        ]:
            self.G.add_edge(a, b, weight=w, correlation=w, edge_type='Same Sector')

        # Finance sector
        for a, b, w in [('HDFCBANK', 'ICICIBANK', 0.78)]:
            self.G.add_edge(a, b, weight=w, correlation=w, edge_type='Same Sector')

        # Cross-sector
        for a, b, w in [
            ('RELIANCE', 'TCS', 0.55), ('RELIANCE', 'TATAMOTORS', 0.51),
            ('HINDUNILVR', 'RELIANCE', 0.48),
            ('HDFCBANK', 'TCS', 0.52),
        ]:
            if w >= CORRELATION_THRESHOLD:
                self.G.add_edge(a, b, weight=w, correlation=w,
                                edge_type='Cross-Sector Correlation')

        try:
            self.pagerank_scores = nx.pagerank(self.G, alpha=0.85)
        except Exception:
            pass


# ── CLI ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    sg = StockGraph()
    sg.build_graph()
    print("\n--- PageRank ---")
    pr = sg.pagerank()
    for s in pr['scores']:
        print(f"  {s['rank']}. {s['node']:12s} {s['score_pct']:.3f}%")
    print("\n--- BFS from TCS ---")
    print(sg.bfs('TCS'))
    print("\n--- Dijkstra TCS -> RELIANCE ---")
    print(sg.dijkstra('TCS', 'RELIANCE'))
    print("\n--- MST ---")
    mst = sg.minimum_spanning_tree()
    for e in mst['edges']:
        print(f"  {e['source']} <-> {e['target']}: {e['weight']}")
