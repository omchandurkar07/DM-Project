# 📈 Stock Market Prediction System
### Project Presentation & Report Document (PPRD)
**Course:** Data Mining & Computational Programming (DM CP)  
**Institute:** VIT Pune — SY SEM 1  
**Project Title:** Stock Market Prediction using Graph Theory, Probability Analysis & Machine Learning

---

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Problem Statement](#2-problem-statement)
3. [Objectives](#3-objectives)
4. [System Architecture](#4-system-architecture)
5. [Modules & Algorithms](#5-modules--algorithms)
6. [Dataset & Data Collection](#6-dataset--data-collection)
7. [Technologies Used](#7-technologies-used)
8. [Project Structure](#8-project-structure)
9. [Module-wise Explanation](#9-module-wise-explanation)
10. [API Endpoints](#10-api-endpoints)
11. [Results & Output](#11-results--output)
12. [Configuration Parameters](#12-configuration-parameters)
13. [Installation & Setup](#13-installation--setup)
14. [Conclusion](#14-conclusion)
15. [References](#15-references)

---

## 1. Project Overview

The **Stock Market Prediction System** is a full-stack web application built with **Python (Flask)** that combines three analytical domains to predict and analyse NSE (National Stock Exchange of India) stock price behaviour:

| Domain | Technique |
|--------|----------|
| **Graph Theory** | Stock correlation networks, BFS, DFS, Dijkstra, PageRank, MST |
| **Probability Analysis** | Bayesian/statistical probability of price movement events |
| **Machine Learning** | XGBoost + Random Forest models for price prediction |
| **Discrete Mathematics** | Boolean logic, Combinatorics, Set Theory, Recurrence Relations |

The system fetches live data from Yahoo Finance via the `yfinance` API, stores it in an SQLite database, and serves an interactive web dashboard.

---

## 2. Problem Statement

Stock market prediction is inherently complex due to the volatile, non-linear nature of financial data. Traditional analysis often treats each stock in isolation. This project addresses:

- **Isolation Problem** — Stocks are inter-related; sector movements affect each other.
- **Uncertainty Quantification** — Investors need probabilistic confidence, not just directional predictions.
- **Feature Engineering Gap** — Raw OHLCV data alone lacks the technical indicators needed for accurate ML models.
- **Lack of Transparency** — "Black box" predictions without mathematical backing reduce trust.

**Goal:** Build an explainable, multi-technique prediction platform combining graph relationships, probabilistic reasoning, and supervised ML.

---

## 3. Objectives

- [x] Collect and store 2 years of historical OHLCV data for 8 major NSE stocks
- [x] Compute technical indicators (MA20, MA50, RSI, MACD) for ML feature engineering
- [x] Build a stock correlation graph and apply graph algorithms (BFS, DFS, Dijkstra, PageRank, MST)
- [x] Implement a probability engine for statistical event analysis
- [x] Train XGBoost/Random Forest models per stock for price movement prediction
- [x] Develop a Discrete Mathematics module (logic gates, combinatorics, set theory, recurrence)
- [x] Provide an interactive Flask web dashboard with Plotly charts
- [x] Implement a secured admin panel for data refresh and model retraining

---

## 4. System Architecture

```
+-------------------------------------------------------------+
|                      User (Browser)                         |
+----------------------------+--------------------------------+
                             |
                        HTTP / AJAX
+----------------------------v--------------------------------+
|                    Flask Web Server                         |
|              app.py  -  Routes & Controllers                |
+------+------------+-------------+--------------+-----------+
       |            |             |              |
  +----v----+  +---v----+  +-----v----+  +------v------+
  |  Graph  |  |  Prob  |  |  Predict |  |  Discrete   |
  | Module  |  | Engine |  |  Model   |  |  Math Eng.  |
  +----+----+  +---+----+  +-----+----+  +------+------+
       |            |             |              |
       +------------+-------------+--------------+
                           |
              +------------v------------+
              |   SQLite Database       |
              |   (stockprediction.db)  |
              +------------+------------+
                           |
              +------------v------------+
              |  Data Collector         |
              |  (yFinance API)         |
              +-------------------------+
```

---

## 5. Modules & Algorithms

### 5.1 Graph Theory Module (`models/graph.py`)

The core analytical module that treats stocks as **graph nodes** and their **correlations as weighted edges**.

| Algorithm | Purpose | Complexity |
|-----------|---------|------------|
| **BFS** (Breadth-First Search) | Explore stock relationships level by level | O(V + E) |
| **DFS** (Depth-First Search) | Deep traversal of correlation paths | O(V + E) |
| **Dijkstra's Algorithm** | Find the most correlated path between two stocks | O((V+E) log V) |
| **PageRank** | Rank stocks by their systemic importance in the network | O(V x iterations) |
| **MST** (Minimum Spanning Tree) | Find the backbone correlation structure (Kruskal/Prim) | O(E log E) |
| **Clustering Coefficient** | Detect stock market communities/sectors | O(V^3) |

**Graph Construction:**
- Node = Each stock ticker (8 nodes)
- Edge = Pearson correlation coefficient > threshold (0.4)
- Edge Weight = Correlation value in [-1, 1]

### 5.2 Probability Engine (`models/probability.py`)

Applies **statistical probability** over a rolling window of 100 trading days to estimate event likelihood.

| Metric | Formula |
|--------|--------|
| P(price up) | `count(close > open) / total_days` |
| P(high > threshold) | `count(high > X) / total_days` |
| Conditional Prob. | Bayesian inference for compound events |
| Volatility | Rolling standard deviation of daily returns |

### 5.3 ML Prediction Module (`models/prediction.py`)

Trains a per-stock **ensemble model** using engineered features from historical data.

**Feature Set:**

| Feature | Description |
|---------|-------------|
| `close`, `open`, `high`, `low` | Raw OHLCV price data |
| `volume` | Trading volume |
| `ma20`, `ma50` | 20-day & 50-day Moving Averages |
| `rsi` | Relative Strength Index (momentum) |
| `macd` | Moving Average Convergence Divergence |
| `price_change` | Daily returns |
| `volatility` | Rolling std of returns |

**Model Pipeline:**
1. Fetch features from SQLite DB
2. Compute `target` = next-day close price (regression) / direction (classification)
3. Train/Test split: 80/20
4. Train `XGBoostRegressor` + `RandomForestClassifier`
5. Serialize with `joblib` to `models/saved/*.pkl`
6. On prediction: load model -> engineer features -> return `predicted_price` + `direction`

### 5.4 Discrete Mathematics Engine (`models/discrete_math.py`)

Applies formal Discrete Mathematics concepts to stock market analysis:

| Concept | Application |
|---------|------------|
| **Boolean Logic / Logic Gates** | Strategy evaluation: if (volatile AND trending AND RSI_ok AND volume_high) -> BUY |
| **Combinatorics** | Count all C(n, k) sub-portfolio combinations from stock universe |
| **Set Theory** | Sector union/intersection/difference analysis (e.g., IT n Finance) |
| **Recurrence Relations** | Model price sequences via linear recurrence (Fibonacci-like patterns) |
| **Graph Theory** (extended) | Full graph metrics: degree, betweenness, modularity |

---

## 6. Dataset & Data Collection

### Source
- **Yahoo Finance API** via the `yfinance` Python library
- **Period:** 2 years of daily OHLCV data

### Stocks Covered (NSE)

| Ticker | Company | Sector | Yahoo Symbol |
|--------|---------|--------|-------------|
| RELIANCE | Reliance Industries | Energy | RELIANCE.NS |
| TCS | Tata Consultancy Services | IT | TCS.NS |
| INFY | Infosys | IT | INFY.NS |
| HDFCBANK | HDFC Bank | Finance | HDFCBANK.NS |
| ICICIBANK | ICICI Bank | Finance | ICICIBANK.NS |
| WIPRO | Wipro | IT | WIPRO.NS |
| HINDUNILVR | Hindustan Unilever | FMCG | HINDUNILVR.NS |
| TATAMOTORS | Tata Motors | Auto | TMPV.NS |

### Database Schema (SQLite)

**Table: `stocks`**
```sql
CREATE TABLE stocks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company     TEXT,
    date        TEXT,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      INTEGER,
    ma20        REAL,
    ma50        REAL,
    rsi         REAL,
    macd        REAL
);
```

**Table: `predictions`**
```sql
CREATE TABLE predictions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    company         TEXT,
    prediction      TEXT,
    probability     REAL,
    predicted_price REAL,
    current_price   REAL,
    algorithm_used  TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Table: `graph_edges`**
```sql
CREATE TABLE graph_edges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT,
    target      TEXT,
    weight      REAL
);
```

---

## 7. Technologies Used

| Layer | Library / Tool | Version | Purpose |
|-------|---------------|---------|--------|
| **Backend** | Flask | 3.0.3 | Web framework & routing |
| **Backend** | Flask-CORS | 4.0.1 | Cross-origin resource sharing |
| **Data** | yfinance | 0.2.40 | Yahoo Finance data fetcher |
| **Data** | Pandas | 2.2.2 | Data manipulation |
| **Data** | NumPy | 1.26.4 | Numerical computing |
| **ML** | Scikit-learn | 1.5.0 | Random Forest, preprocessing |
| **ML** | XGBoost | 2.0.3 | Gradient boosted trees |
| **ML** | Joblib | 1.4.2 | Model serialization |
| **Graph** | NetworkX | 3.3 | Graph construction & algorithms |
| **Graph** | SciPy | 1.13.1 | Sparse matrices, graph metrics |
| **Visualization** | Plotly | 5.22.0 | Interactive charts |
| **Visualization** | Matplotlib | 3.9.0 | Static chart generation |
| **Database** | SQLite | built-in | Persistent data storage |
| **Frontend** | HTML5 / CSS3 / JS | — | UI & interactivity |
| **Config** | python-dotenv | 1.2.2 | Environment variable management |

---

## 8. Project Structure

```
StockPrediction/
|
+-- app.py               # Main Flask application - all routes & controllers
+-- config.py            # Central configuration (stocks, ML settings, etc.)
+-- database.py          # DB initialization & helper functions
+-- requirements.txt     # Python package dependencies
+-- pprd.md              # This document - Project Presentation & Report
+-- README.md            # Quick-start guide
+-- run.bat              # Windows batch launcher
+-- .env                 # Environment variables (not committed)
+-- .env.example         # Template for .env
+-- stockprediction.db   # SQLite database (auto-created)
|
+-- models/
|   +-- data_collector.py  # Fetches & stores data via yFinance
|   +-- graph.py           # Graph Theory module (BFS, DFS, Dijkstra, PageRank, MST)
|   +-- probability.py     # Probability engine for price movement analysis
|   +-- prediction.py      # XGBoost / RandomForest model training & inference
|   +-- discrete_math.py   # Discrete Mathematics engine
|   +-- saved/             # Serialized trained model files (.pkl)
|
+-- templates/
|   +-- base.html          # Base layout template
|   +-- index.html         # Market dashboard (home page)
|   +-- graph.html         # Stock correlation graph view
|   +-- prediction.html    # ML prediction interface
|   +-- probability.html   # Probability analysis view
|   +-- discrete_math.html # Discrete Mathematics analysis hub
|   +-- history.html       # Prediction history table
|   +-- admin.html         # Admin panel
|   +-- admin_login.html   # Admin login page
|
+-- static/
|   +-- css/style.css      # Application stylesheet
|   +-- js/graph_viz.js    # D3.js graph visualization logic
|
+-- dataset/               # Raw / processed dataset files
```

---

## 9. Module-wise Explanation

### `app.py` — Flask Application Core
- Registers all page routes (`/`, `/predict`, `/graph`, `/probability`, `/discrete-math`, `/history`, `/admin`)
- Registers all API routes (`/api/graph-data`, `/api/predict`, `/api/stock-history/<ticker>`, etc.)
- Initializes module singletons: `DataCollector`, `StockGraph`, `ProbabilityEngine`, `PredictionModel`, `DiscreteMathEngine`
- Auto-initializes the DB if empty on first startup

### `config.py` — Central Configuration
- Defines the stock universe (8 NSE stocks with Yahoo Finance symbols)
- Sets ML hyperparameters (train/test split = 0.80, random state = 42)
- Graph settings (correlation threshold = 0.4)
- Flask settings (port = 5000, debug = True)
- Admin credentials loaded from `.env`

### `database.py` — Database Layer
- `init_db()` — Creates all tables on first run
- `get_connection()` — Returns a `sqlite3` connection with `Row` factory
- `fetch_all()`, `fetch_one()` — Safe query helpers returning dict-like rows
- `execute_query()` — Safe parameterized write queries

### `models/data_collector.py` — Data Pipeline
- `fetch_and_store_all()` — Loops over all stocks, calls `yfinance.download()`, computes MA20, MA50, RSI, MACD and upserts to DB

### `models/graph.py` — Graph Theory Engine
- `build_graph()` — Computes pairwise Pearson correlations, constructs `networkx.Graph`, stores edges in DB
- `bfs(start)` / `dfs(start)` — Traversal algorithms
- `dijkstra(start, end)` — Shortest path (highest correlation path)
- `pagerank()` — Stock importance ranking
- `minimum_spanning_tree()` — Backbone graph structure
- `get_graph_json()` — Exports nodes/links for D3.js visualization

### `models/probability.py` — Probability Engine
- `get_probability(symbol, event)` — Returns `{p_up, p_down, volatility, ...}` using rolling window stats

### `models/prediction.py` — ML Module
- `train_all()` — Trains one model per stock, saves `.pkl` to `models/saved/`
- `predict(symbol)` — Loads model, engineers features, returns `{predicted_price, direction, confidence, ...}`

### `models/discrete_math.py` — Discrete Math Engine
- `graph_theory_analysis()` — Extended graph metrics
- `evaluate_boolean_strategy(p, q, r, s)` — Logic gate evaluation for trading strategy
- `combinatorial_subportfolios(k)` — C(n, k) sub-portfolio enumeration
- `set_theory_analysis()` — Sector-based set operations
- `recurrence_analysis(symbol)` — Price sequence modelled as recurrence relation

---

## 10. API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/graph-data` | D3.js force-graph JSON (nodes + links) |
| POST | `/api/predict` | AJAX prediction for a stock |
| GET | `/api/stock-history/<ticker>` | OHLCV + indicators time-series |
| GET | `/api/graph-algorithm/<algo>` | Run BFS / DFS / Dijkstra / PageRank / MST |
| GET | `/api/probability/<ticker>` | Probability data for a single stock |
| GET | `/api/market-ticker` | Lightweight ticker bar data |
| POST | `/api/rebuild-graph` | Rebuild graph edges from current DB data |
| POST | `/api/refresh-all` | Full pipeline: fetch -> graph -> train |

---

## 11. Results & Output

### Pages / Views

| Route | Page | Key Output |
|-------|------|-----------|
| `/` | Market Dashboard | Live prices, change %, volume, recent predictions |
| `/graph` | Graph View | Interactive D3.js stock correlation network |
| `/probability` | Probability | P(up), P(down), volatility per stock |
| `/predict` | Prediction | Predicted next-day price + direction + confidence |
| `/discrete-math` | DM Hub | Logic gate results, sub-portfolios, set diagrams, recurrence |
| `/history` | History | Last 100 predictions table |
| `/admin` | Admin Panel | Data refresh, model train, graph rebuild |

### Sample Prediction Output
```json
{
  "symbol": "TCS",
  "direction": "UP",
  "predicted_price": 3842.75,
  "current_price": 3801.20,
  "confidence": 0.73,
  "algorithm_used": "XGBoost",
  "probability": {
    "p_up": 0.58,
    "p_down": 0.42,
    "volatility": 0.021
  }
}
```

### Sample Graph Algorithm Output (BFS from TCS)
```json
{
  "success": true,
  "result": {
    "traversal_order": ["TCS", "INFY", "WIPRO", "HDFCBANK", "RELIANCE"],
    "edges_traversed": 7
  }
}
```

---

## 12. Configuration Parameters

All parameters are centralized in `config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DATA_PERIOD` | `2y` | Historical data fetch window (yFinance period string) |
| `LOOKBACK_DAYS` | `100` | Rolling window for probability calculations |
| `CORRELATION_THRESHOLD` | `0.4` | Minimum Pearson correlation to draw a graph edge |
| `TRAIN_TEST_SPLIT` | `0.80` | ML model train/test split ratio |
| `RANDOM_STATE` | `42` | Random seed for reproducibility |
| `PORT` | `5000` | Flask server port |
| `DEBUG` | `True` | Flask debug mode (set to False in production) |
| `ADMIN_USERNAME` | (from .env) | Admin panel username |
| `ADMIN_PASSWORD` | (from .env) | Admin panel password |

---

## 13. Installation & Setup

### Prerequisites
- Python 3.9+
- pip
- Active internet connection (for yFinance API)

### Step-by-Step

```bash
# 1. Navigate to project directory
cd "SY SEM 1 at VIT Pune/DM CP/DM-Project/Electricity thief detection/StockPrediction"

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 4. Install dependencies
pip install -r requirements.txt

# 5. Set environment variables
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux
# Edit .env with your credentials

# 6. Run the application
python app.py

# OR use the batch launcher (Windows)
run.bat
```

### First-Time Setup
On first startup, if the database is empty, the app automatically:
1. Fetches 2 years of data for all 8 stocks via yFinance
2. Builds the correlation graph
3. Trains ML models for each stock

Alternatively, visit the **Admin Panel** (`/admin`) and run **"Full Pipeline"**.

### Access
```
http://localhost:5000
```

---

## 14. Conclusion

This project successfully demonstrates the application of multiple Computer Science & Mathematics disciplines to a real-world financial prediction problem:

- **Graph Theory** reveals hidden inter-stock relationships and ranks stocks by systemic importance using PageRank, enabling portfolio-aware decision making.
- **Probability Analysis** provides statistically grounded confidence intervals instead of binary predictions, quantifying uncertainty.
- **Machine Learning (XGBoost)** learns from engineered technical indicators to forecast next-day price direction and magnitude with measurable accuracy.
- **Discrete Mathematics** formalises trading strategies using Boolean logic, enumerates portfolio combinations via combinatorics, and models price patterns through recurrence relations.

The system is extensible — new stocks, algorithms, or ML models can be plugged in via `config.py` and the modular architecture.

---

## 15. References

1. **yFinance Library** — https://pypi.org/project/yfinance/
2. **NetworkX Documentation** — https://networkx.org/documentation/stable/
3. **XGBoost Documentation** — https://xgboost.readthedocs.io/
4. **Flask Documentation** — https://flask.palletsprojects.com/
5. **Plotly Python** — https://plotly.com/python/
6. **Pearson Correlation** — Statistical correlation for financial time-series
7. **PageRank Algorithm** — Brin & Page, 1998 — "The Anatomy of a Large-Scale Hypertextual Web Search Engine"
8. **Technical Indicators (RSI, MACD, MA)** — J. Welles Wilder, "New Concepts in Technical Trading Systems" (1978)
9. **NSE India** — https://www.nseindia.com/

---

> Built with Flask · XGBoost · NetworkX · Plotly · SQLite  
> Prepared for academic/educational purposes — DM-CP Course Project, VIT Pune
