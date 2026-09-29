# 📈 Stock Market Prediction System

A full-stack **Flask web application** for Indian NSE stock market analysis using **Graph Theory**, **Probability Analysis**, and **Machine Learning**.

---

## 🚀 Features

- 📊 **Market Dashboard** — Real-time market summary for top Indian NSE stocks
- 🔗 **Graph Theory Analysis** — Stock correlation networks built with NetworkX
- 🎲 **Probability Engine** — Statistical probability calculations for price movement
- 🤖 **ML Predictions** — XGBoost-based price predictions with trained models
- 📉 **Interactive Charts** — Dynamic visualizations using Plotly
- 🗄️ **SQLite Database** — Persistent storage of historical stock data & predictions
- 🛠️ **Admin Panel** — Data collection and model training controls

---

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, Flask, Flask-CORS |
| Data | yFinance, Pandas, NumPy |
| ML | Scikit-learn, XGBoost, Joblib |
| Graph | NetworkX, SciPy |
| Visualization | Plotly, Matplotlib |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |

---

## 📁 Project Structure

```
StockPrediction/
│
├── app.py               # Main Flask application & all routes
├── config.py            # Central configuration (stocks, ML settings, etc.)
├── database.py          # Database initialization & helper functions
├── requirements.txt     # Python dependencies
├── stockprediction.db   # SQLite database
│
├── models/
│   ├── data_collector.py  # Fetches stock data via yFinance
│   ├── graph.py           # Graph theory & correlation analysis
│   ├── probability.py     # Probability engine for price movement
│   ├── prediction.py      # XGBoost ML model training & inference
│   └── saved/             # Saved trained model files
│
├── templates/
│   ├── base.html          # Base layout template
│   ├── index.html         # Market dashboard (home page)
│   ├── graph.html         # Stock correlation graph view
│   ├── prediction.html    # ML prediction interface
│   ├── probability.html   # Probability analysis view
│   ├── history.html       # Historical data view
│   └── admin.html         # Admin panel
│
├── static/
│   └── css/
│       └── style.css      # Application stylesheet
│
└── dataset/               # Raw/processed dataset files
```

---

## 🧰 Stocks Covered (NSE)

| Ticker | Company | Sector |
|--------|---------|--------|
| RELIANCE | Reliance Industries | Energy |
| TCS | Tata Consultancy Services | IT |
| INFY | Infosys | IT |
| HDFCBANK | HDFC Bank | Finance |
| ICICIBANK | ICICI Bank | Finance |
| WIPRO | Wipro | IT |
| HINDUNILVR | Hindustan Unilever | FMCG |
| TATAMOTORS | Tata Motors | Auto |

---

## ⚙️ Installation & Setup

### Prerequisites
- Python 3.9+
- pip

### 1. Clone / Download the Project
```bash
cd "Electricity thief detection/StockPrediction"
```

### 2. Create a Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python app.py
```

### 5. Open in Browser
```
http://localhost:5000
```

---

## 🖥️ Usage Guide

1. **Home Dashboard** (`/`) — View market summary for all tracked stocks.
2. **Graph View** (`/graph`) — Explore stock correlation graphs powered by NetworkX.
3. **Probability** (`/probability`) — Analyse statistical probability of price movements.
4. **Prediction** (`/prediction`) — Get XGBoost ML-based price forecasts.
5. **History** (`/history`) — Browse historical OHLCV data stored in the database.
6. **Admin Panel** (`/admin`) — Trigger data collection and model (re)training.

---

## 🔧 Configuration

All key settings are centralized in [`config.py`](config.py):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DATA_PERIOD` | `2y` | Historical data fetch window |
| `LOOKBACK_DAYS` | `100` | Rolling window for probability |
| `CORRELATION_THRESHOLD` | `0.4` | Min correlation to draw a graph edge |
| `TRAIN_TEST_SPLIT` | `0.80` | ML train/test split ratio |
| `PORT` | `5000` | Flask server port |
| `DEBUG` | `True` | Flask debug mode |

---

## 📦 Dependencies

```
flask==3.0.3
flask-cors==4.0.1
yfinance==0.2.40
pandas==2.2.2
numpy==1.26.4
scikit-learn==1.5.0
xgboost==2.0.3
networkx==3.3
matplotlib==3.9.0
plotly==5.22.0
scipy==1.13.1
joblib==1.4.2
requests==2.32.3
python-dateutil==2.9.0
```

---

## 📌 Notes

- Stock data is fetched live via the **Yahoo Finance API** (`yfinance`). An active internet connection is required.
- On first run, visit the **Admin Panel** to collect data and train models before using prediction features.
- The SQLite database file (`stockprediction.db`) is auto-created on first launch.

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'Add some feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is for **educational purposes**. Feel free to use and modify it as needed.

---

> Built with ❤️ using Flask, XGBoost & Graph Theory
