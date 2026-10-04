"""One-off script to write the new prediction.html template."""
import os

TEMPLATE = r"""{% extends 'base.html' %}

{% block title %}Stock Prediction — StockGraph{% endblock %}

{% block extra_head %}
<style>
/* ── Prediction Page Extra Styles ── */
.pred-disclaimer {
  background: rgba(245,158,11,0.08);
  border: 1px solid rgba(245,158,11,0.25);
  border-radius: var(--radius-sm);
  padding: .65rem 1rem;
  font-size: .75rem;
  color: #f59e0b;
  display: flex;
  align-items: center;
  gap: .5rem;
}
.dir-badge {
  display: inline-flex;
  align-items: center;
  gap: .5rem;
  padding: .45rem 1.4rem;
  border-radius: 999px;
  font-size: 1.05rem;
  font-weight: 800;
  letter-spacing: .06em;
  text-transform: uppercase;
}
.dir-badge.up   { background:rgba(16,185,129,.15); color:#10b981; border:1.5px solid rgba(16,185,129,.45); }
.dir-badge.down { background:rgba(239,68,68,.15);  color:#ef4444; border:1.5px solid rgba(239,68,68,.45); }

.stat-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:.75rem; }
@media(min-width:576px){ .stat-grid { grid-template-columns:repeat(4,1fr); } }
.stat-box {
  background:rgba(255,255,255,.035);
  border:1px solid rgba(255,255,255,.07);
  border-radius:var(--radius-md);
  padding:1rem .85rem;
  text-align:center;
  transition:var(--transition);
}
.stat-box:hover { border-color:rgba(0,212,255,.25); }
.stat-box .label { font-size:.68rem; text-transform:uppercase; letter-spacing:.1em; color:var(--text-secondary); margin-bottom:.35rem; }
.stat-box .value { font-family:'JetBrains Mono',monospace; font-size:1.05rem; font-weight:700; color:var(--text-primary); }
.stat-box.target .value { color:#00d4ff; }
.stat-box.profit .value { color:#10b981; }
.stat-box.loss   .value { color:#ef4444; }

.prob-row   { display:flex; align-items:center; gap:.75rem; margin-top:1rem; }
.prob-label { font-size:.72rem; font-family:'JetBrains Mono',monospace; min-width:52px; }
.prob-track { flex:1; height:10px; background:rgba(255,255,255,.06); border-radius:999px; overflow:hidden; }
.prob-fill-up { height:100%; background:linear-gradient(90deg,#10b981,#00d4ff); border-radius:999px; transition:width .6s ease; }
.prob-fill-dn { height:100%; background:linear-gradient(90deg,#ef4444,#f97316); border-radius:999px; transition:width .6s ease; }
.prob-pct { font-size:.75rem; font-family:'JetBrains Mono',monospace; min-width:38px; text-align:right; }

.ind-table { width:100%; border-collapse:collapse; }
.ind-table tr { border-bottom:1px solid rgba(255,255,255,.05); }
.ind-table tr:last-child { border-bottom:none; }
.ind-table td { padding:.55rem .5rem; font-size:.82rem; }
.ind-table td:first-child { color:var(--text-secondary); font-weight:500; }
.ind-table td:last-child  { font-family:'JetBrains Mono',monospace; text-align:right; color:#e2e8f0; }

.conf-ring-wrap { display:flex; align-items:center; gap:1rem; }
.conf-ring {
  --pct: 0;
  width:68px; height:68px; flex-shrink:0;
  border-radius:50%;
  background:conic-gradient(#00d4ff calc(var(--pct)*1%), rgba(255,255,255,.07) 0%);
  display:flex; align-items:center; justify-content:center;
}
.conf-ring-inner {
  width:52px; height:52px;
  background:#0d1526;
  border-radius:50%;
  display:flex; align-items:center; justify-content:center;
  font-family:'JetBrains Mono',monospace;
  font-size:.9rem; font-weight:700; color:#00d4ff;
}
.pred-loading { display:none; flex-direction:column; align-items:center; gap:1rem; padding:3rem 0; }
.pred-loading.active { display:flex; }
.spinner-ring {
  width:52px; height:52px;
  border:3px solid rgba(0,212,255,.15);
  border-top-color:#00d4ff;
  border-radius:50%;
  animation:spin .8s linear infinite;
}
@keyframes spin { to { transform:rotate(360deg); } }
.sect-title { font-size:.68rem; text-transform:uppercase; letter-spacing:.12em; color:var(--text-secondary); font-weight:600; margin-bottom:.65rem; }
.fi-bar-wrap { display:flex; align-items:center; gap:.6rem; margin-bottom:.4rem; }
.fi-bar-track { flex:1; height:5px; background:rgba(255,255,255,.07); border-radius:4px; overflow:hidden; }
.fi-bar-fill  { height:100%; background:var(--gradient-1); border-radius:4px; }
.fi-label { font-size:.7rem; min-width:110px; font-family:'JetBrains Mono',monospace; color:var(--text-secondary); }
.fi-pct   { font-size:.7rem; min-width:36px; text-align:right; color:#00d4ff; }
</style>
{% endblock %}

{% block content %}
<div class="page-header py-2 mb-4">
  <h1 class="gradient-text"><i class="bi bi-cpu me-2"></i>Stock Price &amp; Direction Predictor</h1>
  <p class="text-muted" style="font-size:.9rem;">
    Graph-boosted Machine Learning forecast using XGBoost + Random Forest.
    Select a stock and click <strong>Predict</strong>.
  </p>
</div>

<div class="pred-disclaimer mb-4">
  <i class="bi bi-exclamation-triangle-fill"></i>
  <span>
    <strong>Disclaimer:</strong> Predictions are <em>model estimates only</em>, not guaranteed future prices.
    Stock markets are inherently unpredictable. Do not make financial decisions based solely on these outputs.
  </span>
</div>

<div class="row g-4">

  <!-- LEFT: Controls -->
  <div class="col-lg-4">
    <div class="glass-card mb-4">
      <div class="card-header-styled">
        <div class="fw-bold"><i class="bi bi-sliders me-2 text-info"></i>Prediction Parameters</div>
      </div>
      <div class="card-body-styled">
        <div class="mb-3">
          <label class="form-label text-muted fs-8 fw-semibold text-uppercase" for="stock-select-ajax">Select Company</label>
          <select id="stock-select-ajax" class="form-select form-select-dark w-100">
            {% for key, info in stocks.items() %}
            <option value="{{ key }}" {% if selected == key %}selected{% endif %}>
              {{ key }} &mdash; {{ info.name }} ({{ info.sector }})
            </option>
            {% endfor %}
          </select>
        </div>
        <div class="mb-4">
          <label class="form-label text-muted fs-8 fw-semibold text-uppercase" for="event-select-ajax">Market Sentiment Event (Bayesian)</label>
          <select id="event-select-ajax" class="form-select form-select-dark w-100">
            <option value="">None (Standard Market)</option>
            <option value="positive">Positive Sector News (Bullish)</option>
            <option value="negative">Negative Sector News (Bearish)</option>
          </select>
        </div>
        <button id="predict-btn" class="btn btn-glow w-100 py-2">
          <i class="bi bi-lightning-charge-fill me-1"></i> Predict Next-Day Price
        </button>
      </div>
    </div>

    <!-- AJAX Stock Profile (filled dynamically) -->
    <div id="stock-profile-card" class="glass-card" style="display:none;">
      <div class="card-header-styled">
        <div class="fw-bold"><i class="bi bi-info-circle me-2 text-cyan"></i>Stock Profile</div>
      </div>
      <div class="card-body-styled">
        <div class="d-flex justify-content-between mb-2">
          <span class="text-muted fs-8">Company:</span><span class="fw-semibold" id="sp-name">-</span>
        </div>
        <div class="d-flex justify-content-between mb-2">
          <span class="text-muted fs-8">Symbol:</span><span class="mono text-cyan fw-bold" id="sp-symbol">-</span>
        </div>
        <div class="d-flex justify-content-between mb-2">
          <span class="text-muted fs-8">Data as of:</span><span class="mono fs-8" id="sp-date">-</span>
        </div>
        <div class="d-flex justify-content-between mb-2">
          <span class="text-muted fs-8">Algorithm:</span>
          <span class="badge bg-secondary bg-opacity-50 text-light fs-8" id="sp-algo">-</span>
        </div>
        <div id="sp-fi-wrap" class="mt-3 pt-3 border-top border-secondary border-opacity-25" style="display:none;">
          <div class="sect-title">Top Feature Importance</div>
          <div id="sp-fi-list"></div>
        </div>
      </div>
    </div>

    {% if result and not result.error %}
    <!-- SSR Stock Profile -->
    <div id="stock-profile-card-ssr" class="glass-card mt-3">
      <div class="card-header-styled">
        <div class="fw-bold"><i class="bi bi-info-circle me-2 text-cyan"></i>Stock Profile</div>
        <span class="stock-sector-badge" style="border-color:var(--accent-cyan);color:var(--accent-cyan);">
          {{ stocks[result.symbol].sector }}
        </span>
      </div>
      <div class="card-body-styled">
        <div class="d-flex justify-content-between mb-2">
          <span class="text-muted fs-8">Company:</span><span class="fw-semibold">{{ result.name }}</span>
        </div>
        <div class="d-flex justify-content-between mb-2">
          <span class="text-muted fs-8">Symbol:</span><span class="mono text-cyan fw-bold">{{ result.symbol }}</span>
        </div>
        <div class="d-flex justify-content-between mb-2">
          <span class="text-muted fs-8">Data as of:</span><span class="mono fs-8">{{ result.data_date }}</span>
        </div>
        <div class="d-flex justify-content-between mb-2">
          <span class="text-muted fs-8">Algorithm:</span>
          <span class="badge bg-secondary bg-opacity-50 text-light fs-8">{{ result.algorithm_used }}</span>
        </div>
        {% if result.top_features %}
        <div class="mt-3 pt-3 border-top border-secondary border-opacity-25">
          <div class="sect-title">Top Feature Importance</div>
          {% for feat in result.top_features %}
          <div class="fi-bar-wrap">
            <span class="fi-label">{{ feat.feature }}</span>
            <div class="fi-bar-track"><div class="fi-bar-fill" style="width:{{ (feat.importance*100)|round(1) }}%"></div></div>
            <span class="fi-pct">{{ (feat.importance*100)|round(1) }}%</span>
          </div>
          {% endfor %}
        </div>
        {% endif %}
      </div>
    </div>
    {% endif %}
  </div>

  <!-- RIGHT: Results -->
  <div class="col-lg-8">

    <!-- Loading Spinner -->
    <div class="pred-loading glass-card py-5" id="pred-loading">
      <div class="spinner-ring"></div>
      <span class="text-muted">Running ML prediction pipeline&hellip;</span>
    </div>

    <!-- AJAX Result Panel -->
    <div id="pred-result-panel" style="display:none;">

      <!-- Hero -->
      <div class="glass-card mb-4">
        <div class="card-body-styled">
          <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
            <div>
              <div class="text-muted" style="font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;">Next-Day Forecast</div>
              <div class="fw-bold" style="font-size:1.6rem;" id="r-symbol-name">-</div>
            </div>
            <div id="r-dir-badge" class="dir-badge">-</div>
          </div>

          <div class="stat-grid mb-3">
            <div class="stat-box"><div class="label">Current Price</div><div class="value" id="r-current">-</div></div>
            <div class="stat-box target"><div class="label">Predicted Price</div><div class="value" id="r-pred">-</div></div>
            <div class="stat-box" id="r-change-box"><div class="label" id="r-change-label">Expected Change</div><div class="value" id="r-change">-</div></div>
            <div class="stat-box"><div class="label">Data Date</div><div class="value" id="r-date" style="font-size:.82rem;">-</div></div>
          </div>

          <div class="row g-3">
            <div class="col-md-5">
              <div class="sect-title">Model Confidence</div>
              <div class="conf-ring-wrap">
                <div class="conf-ring" id="conf-ring"><div class="conf-ring-inner" id="conf-ring-txt">-</div></div>
                <div>
                  <div class="text-muted" style="font-size:.82rem;">Classifier probability</div>
                  <div class="fw-semibold" style="font-size:.85rem;" id="conf-label">for predicted direction</div>
                </div>
              </div>
            </div>
            <div class="col-md-7">
              <div class="sect-title">Direction Probability (ML Classifier)</div>
              <div class="prob-row">
                <span class="prob-label" style="color:#10b981;">&#9650; UP</span>
                <div class="prob-track"><div class="prob-fill-up" id="prob-up-bar" style="width:50%"></div></div>
                <span class="prob-pct" id="prob-up-pct" style="color:#10b981;">-</span>
              </div>
              <div class="prob-row">
                <span class="prob-label" style="color:#ef4444;">&#9660; DOWN</span>
                <div class="prob-track"><div class="prob-fill-dn" id="prob-dn-bar" style="width:50%"></div></div>
                <span class="prob-pct" id="prob-dn-pct" style="color:#ef4444;">-</span>
              </div>
              <div class="mt-2 d-flex justify-content-between" style="font-size:.72rem;color:var(--text-secondary);">
                <span>Bayesian Signal: <strong class="text-light" id="r-bayes-signal">-</strong></span>
                <span id="r-bayes-method">-</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Indicators -->
      <div class="glass-card mb-4">
        <div class="card-header-styled">
          <div class="fw-bold"><i class="bi bi-activity me-2 text-cyan"></i>Technical Indicators Used</div>
          <span class="fs-8 text-muted">Calculated from historical OHLCV data in SQLite</span>
        </div>
        <div class="card-body-styled">
          <table class="ind-table">
            <tbody>
              <tr><td><i class="bi bi-graph-up me-2 text-warning opacity-75"></i>MA20 (20-day Moving Average)</td><td id="ind-ma20">-</td></tr>
              <tr><td><i class="bi bi-graph-up-arrow me-2 opacity-75" style="color:#9d4edd;"></i>MA50 (50-day Moving Average)</td><td id="ind-ma50">-</td></tr>
              <tr><td><i class="bi bi-speedometer me-2 text-info opacity-75"></i>RSI (Relative Strength Index)</td><td id="ind-rsi">-</td></tr>
              <tr><td><i class="bi bi-bar-chart-line me-2 text-success opacity-75"></i>MACD</td><td id="ind-macd">-</td></tr>
              <tr><td><i class="bi bi-wind me-2 text-danger opacity-75"></i>Volatility (20-day return std)</td><td id="ind-vol">-</td></tr>
              <tr><td><i class="bi bi-percent me-2 opacity-75" style="color:#f59e0b;"></i>Daily Price Change</td><td id="ind-chg">-</td></tr>
            </tbody>
          </table>
          <p class="text-muted mt-3 mb-0" style="font-size:.72rem;">
            MA20, MA50, RSI, and MACD are pre-stored per row in SQLite.
            Volatility is the 20-day rolling standard deviation of daily returns.
            Price Change is the previous day close % change.
            All indicators are computed without using future data (no leakage).
          </p>
        </div>
      </div>

      <!-- Metrics -->
      <div class="glass-card mb-4" id="pred-metrics-card" style="display:none;">
        <div class="card-header-styled">
          <div class="fw-bold"><i class="bi bi-clipboard-data me-2 text-cyan"></i>Model Evaluation Metrics</div>
          <span class="fs-8 text-muted">Holdout test set &mdash; last 20% of chronological data, no future leakage</span>
        </div>
        <div class="card-body-styled d-flex flex-wrap gap-4">
          <div><div class="text-muted fs-8">Direction Accuracy</div><div class="mono fw-bold" id="m-acc">-</div></div>
          <div><div class="text-muted fs-8">Majority Baseline Accuracy</div><div class="mono fw-bold" id="m-base-acc">-</div></div>
          <div><div class="text-muted fs-8">Price RMSE / Baseline RMSE</div><div class="mono fw-bold" id="m-rmse">-</div></div>
        </div>
      </div>

      <!-- Chart -->
      <div class="glass-card mb-4">
        <div class="card-header-styled">
          <div class="fw-bold"><i class="bi bi-graph-up-arrow me-2 text-cyan"></i><span id="r-chart-title">Price History &amp; Target</span></div>
          <span class="fs-8 text-muted">Last 120 Days</span>
        </div>
        <div class="card-body-styled">
          <div id="prediction-stock-chart" style="height:340px;width:100%;"></div>
        </div>
      </div>

    </div><!-- /pred-result-panel -->

    <!-- Error Panel -->
    <div id="pred-error-panel" style="display:none;" class="alert alert-glass error mb-4">
      <i class="bi bi-exclamation-triangle-fill fs-4"></i>
      <div><strong>Prediction Error:</strong> <span id="pred-error-msg"></span></div>
    </div>

    <!-- ───── SSR Results (server-side fallback) ───── -->
    {% if result %}
      {% if result.error %}
      <div class="alert alert-glass error mb-4">
        <i class="bi bi-exclamation-triangle-fill fs-4"></i>
        <div><strong>Prediction Error:</strong> {{ result.error }}</div>
      </div>
      {% else %}

      <div class="glass-card mb-4" id="ssr-hero">
        <div class="card-body-styled">
          <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
            <div>
              <div class="text-muted" style="font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;">
                Next-Day Forecast &middot; Data through {{ result.data_date }}
              </div>
              <div class="fw-bold" style="font-size:1.5rem;">{{ result.symbol }} &mdash; {{ result.name }}</div>
            </div>
            <div class="dir-badge {% if result.direction == 'UP' %}up{% else %}down{% endif %}">
              {% if result.direction == 'UP' %}
                <i class="bi bi-arrow-up-circle-fill"></i> UP
              {% else %}
                <i class="bi bi-arrow-down-circle-fill"></i> DOWN
              {% endif %}
            </div>
          </div>

          <div class="stat-grid mb-3">
            <div class="stat-box"><div class="label">Current Price</div><div class="value">&#8377;{{ result.current_price }}</div></div>
            <div class="stat-box target"><div class="label">Predicted Price</div><div class="value">&#8377;{{ result.predicted_price }}</div></div>
            <div class="stat-box {% if result.change >= 0 %}profit{% else %}loss{% endif %}">
              <div class="label">{% if result.change >= 0 %}Expected Profit{% else %}Expected Loss{% endif %}</div>
              <div class="value">
                {% if result.change >= 0 %}+{% endif %}&#8377;{{ result.change|abs }}
                <span style="font-size:.75rem;">({{ result.change_pct|abs }}%)</span>
              </div>
            </div>
            <div class="stat-box"><div class="label">Confidence</div><div class="value">{{ result.confidence_pct }}%</div></div>
          </div>

          {% if result.probability %}
          <div class="row g-3">
            <div class="col-md-7">
              <div class="sect-title">Direction Probability (ML Classifier)</div>
              <div class="prob-row">
                <span class="prob-label" style="color:#10b981;">&#9650; UP</span>
                <div class="prob-track"><div class="prob-fill-up" style="width:{{ (result.probability.up*100)|round(1) }}%"></div></div>
                <span class="prob-pct" style="color:#10b981;">{{ (result.probability.up*100)|round(1) }}%</span>
              </div>
              <div class="prob-row">
                <span class="prob-label" style="color:#ef4444;">&#9660; DOWN</span>
                <div class="prob-track"><div class="prob-fill-dn" style="width:{{ (result.probability.down*100)|round(1) }}%"></div></div>
                <span class="prob-pct" style="color:#ef4444;">{{ (result.probability.down*100)|round(1) }}%</span>
              </div>
              {% if result.bayesian %}
              <div class="mt-2 d-flex justify-content-between" style="font-size:.72rem;color:var(--text-secondary);">
                <span>Bayesian Signal: <strong class="text-light">{{ result.bayesian.signal }}</strong></span>
                <span>{{ result.bayesian.method }}</span>
              </div>
              {% endif %}
            </div>
          </div>
          {% endif %}
        </div>
      </div>

      {% if result.indicators %}
      <div class="glass-card mb-4">
        <div class="card-header-styled">
          <div class="fw-bold"><i class="bi bi-activity me-2 text-cyan"></i>Technical Indicators Used</div>
          <span class="fs-8 text-muted">Calculated from historical OHLCV data in SQLite</span>
        </div>
        <div class="card-body-styled">
          <table class="ind-table">
            <tbody>
              {% set ind = result.indicators %}
              <tr>
                <td><i class="bi bi-graph-up me-2 text-warning opacity-75"></i>MA20 (20-day Moving Average)</td>
                <td>{% if ind.ma20 is not none %}&#8377;{{ ind.ma20 }}{% else %}N/A{% endif %}</td>
              </tr>
              <tr>
                <td><i class="bi bi-graph-up-arrow me-2 opacity-75" style="color:#9d4edd;"></i>MA50 (50-day Moving Average)</td>
                <td>{% if ind.ma50 is not none %}&#8377;{{ ind.ma50 }}{% else %}N/A{% endif %}</td>
              </tr>
              <tr>
                <td><i class="bi bi-speedometer me-2 text-info opacity-75"></i>RSI (Relative Strength Index)</td>
                <td>{% if ind.rsi is not none %}{{ ind.rsi }}{% else %}N/A{% endif %}</td>
              </tr>
              <tr>
                <td><i class="bi bi-bar-chart-line me-2 text-success opacity-75"></i>MACD</td>
                <td>{% if ind.macd is not none %}{{ ind.macd }}{% else %}N/A{% endif %}</td>
              </tr>
              <tr>
                <td><i class="bi bi-wind me-2 text-danger opacity-75"></i>Volatility (20-day return std)</td>
                <td>{% if ind.volatility is not none %}{{ (ind.volatility*100)|round(2) }}%{% else %}N/A{% endif %}</td>
              </tr>
              <tr>
                <td><i class="bi bi-percent me-2 opacity-75" style="color:#f59e0b;"></i>Daily Price Change</td>
                <td>{% if ind.price_change is not none %}{{ ind.price_change }}%{% else %}N/A{% endif %}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      {% endif %}

      {% if result.metrics and result.metrics.get('accuracy') is not none %}
      <div class="glass-card mb-4">
        <div class="card-header-styled">
          <div class="fw-bold"><i class="bi bi-clipboard-data me-2 text-cyan"></i>Model Evaluation Metrics</div>
          <span class="fs-8 text-muted">Holdout test set (no future data leakage)</span>
        </div>
        <div class="card-body-styled d-flex flex-wrap gap-4">
          <div><div class="text-muted fs-8">Direction Accuracy</div><div class="mono fw-bold">{{ (result.metrics.accuracy*100)|round(1) }}%</div></div>
          <div><div class="text-muted fs-8">Majority Baseline</div><div class="mono fw-bold">{{ (result.metrics.baseline_accuracy*100)|round(1) }}%</div></div>
          <div><div class="text-muted fs-8">RMSE / Baseline RMSE</div><div class="mono fw-bold">&#8377;{{ result.metrics.rmse|round(2) }} / &#8377;{{ result.metrics.baseline_rmse|round(2) }}</div></div>
        </div>
      </div>
      {% endif %}

      <div class="glass-card mb-4" id="ssr-chart-card">
        <div class="card-header-styled">
          <div class="fw-bold"><i class="bi bi-graph-up-arrow me-2 text-cyan"></i>{{ result.symbol }} Price History &amp; Target</div>
          <span class="fs-8 text-muted">Last 120 Days</span>
        </div>
        <div class="card-body-styled">
          <div id="ssr-prediction-chart" style="height:340px;width:100%;"></div>
        </div>
      </div>

      {% endif %}
    {% else %}
    <!-- Empty state -->
    <div class="glass-card text-center py-5 px-4" id="pred-empty-state">
      <div class="mb-3"><i class="bi bi-cpu text-info" style="font-size:3.5rem;"></i></div>
      <h3 class="fw-bold text-light mb-2">Ready to Run ML Prediction</h3>
      <p class="text-muted mx-auto" style="max-width:480px;">
        Select a stock and click <strong>Predict Next-Day Price</strong>. The model uses
        2 years of historical OHLCV data, computes MA20, MA50, RSI, MACD, Volatility and
        runs XGBoost (price regression) + Random Forest (direction classification).
      </p>
      <div class="mt-3" style="font-size:.78rem;color:var(--text-muted);">
        Models are pre-trained and cached &mdash; prediction completes in 1&ndash;2 seconds.
      </div>
    </div>
    {% endif %}

  </div><!-- /col-lg-8 -->
</div><!-- /row -->
{% endblock %}

{% block extra_scripts %}
<script src="{{ url_for('static', filename='js/charts.js') }}"></script>

{% if result and not result.error %}
<script>
document.addEventListener('DOMContentLoaded', function() {
  loadStockChart("{{ result.symbol }}", "ssr-prediction-chart", {{ result.predicted_price }});
  var es = document.getElementById('pred-empty-state');
  if (es) es.style.display = 'none';
});
</script>
{% endif %}

<script>
/* ===================================================================
   Prediction Page — AJAX Predict Logic
   ===================================================================
   Flow:
   1. User selects stock + event and clicks "Predict"
   2. JS sends POST /api/predict  { symbol, event }
   3. Flask loads latest data from SQLite
   4. XGBoost predicts next-day price
   5. Random Forest predicts direction + probability
   6. Response JSON is rendered into the result panel
   =================================================================== */
(function () {
  var btn      = document.getElementById('predict-btn');
  var selStock = document.getElementById('stock-select-ajax');
  var selEvent = document.getElementById('event-select-ajax');
  var loading  = document.getElementById('pred-loading');
  var resPan   = document.getElementById('pred-result-panel');
  var errPan   = document.getElementById('pred-error-panel');
  var errMsg   = document.getElementById('pred-error-msg');
  var emptyEl  = document.getElementById('pred-empty-state');
  var ssrHero  = document.getElementById('ssr-hero');
  var ssrChart = document.getElementById('ssr-chart-card');
  var ssrProf  = document.getElementById('stock-profile-card-ssr');

  function fmtRupee(v) {
    if (v == null) return '-';
    return '\u20B9' + parseFloat(v).toLocaleString('en-IN', {
      minimumFractionDigits: 2, maximumFractionDigits: 2
    });
  }
  function fmtNum(v, d) {
    if (v == null) return 'N/A';
    return parseFloat(v).toFixed(d != null ? d : 2);
  }
  function setText(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
  }
  function showLoading() {
    if (loading)  loading.classList.add('active');
    if (resPan)   resPan.style.display   = 'none';
    if (errPan)   errPan.style.display   = 'none';
    if (emptyEl)  emptyEl.style.display  = 'none';
    if (ssrHero)  ssrHero.style.display  = 'none';
    if (ssrChart) ssrChart.style.display = 'none';
    if (ssrProf)  ssrProf.style.display  = 'none';
  }
  function hideLoading() {
    if (loading) loading.classList.remove('active');
  }
  function showError(msg) {
    hideLoading();
    if (errMsg) errMsg.textContent = msg;
    if (errPan) errPan.style.display = 'flex';
  }

  function renderResult(d) {
    hideLoading();

    /* Symbol + name */
    setText('r-symbol-name', d.symbol + ' \u2014 ' + (d.name || d.symbol));
    setText('sp-name',   d.name || d.symbol);
    setText('sp-symbol', d.symbol);
    setText('sp-date',   d.data_date || '-');
    setText('sp-algo',   d.algorithm_used || '-');

    /* Direction badge */
    var badge = document.getElementById('r-dir-badge');
    if (badge) {
      var isUp = d.direction === 'UP';
      badge.className = 'dir-badge ' + (isUp ? 'up' : 'down');
      badge.innerHTML = isUp
        ? '<i class="bi bi-arrow-up-circle-fill"></i> UP'
        : '<i class="bi bi-arrow-down-circle-fill"></i> DOWN';
    }

    /* Stats */
    setText('r-current', fmtRupee(d.current_price));
    setText('r-pred',    fmtRupee(d.predicted_price));
    setText('r-date',    d.data_date || '-');

    var cbox = document.getElementById('r-change-box');
    var clbl = document.getElementById('r-change-label');
    var cval = document.getElementById('r-change');
    if (d.change != null) {
      var ip = d.change >= 0;
      if (cbox) cbox.className = 'stat-box ' + (ip ? 'profit' : 'loss');
      if (clbl) clbl.textContent = ip ? 'Expected Profit' : 'Expected Loss';
      if (cval) cval.textContent =
        (ip ? '+' : '-') + '\u20B9' + Math.abs(d.change).toFixed(2) +
        ' (' + Math.abs(d.change_pct).toFixed(2) + '%)';
    }

    /* Confidence ring (CSS conic-gradient) */
    var cpct = d.confidence_pct != null
      ? d.confidence_pct
      : (d.confidence * 100).toFixed(1);
    var ring = document.getElementById('conf-ring');
    if (ring) ring.style.setProperty('--pct', cpct);
    setText('conf-ring-txt', parseFloat(cpct).toFixed(0) + '%');
    setText('conf-label',    'Confidence in ' + d.direction + ' direction');

    /* Probability bars */
    var prob = d.probability || {};
    var upP  = ((prob.up   || 0) * 100).toFixed(1);
    var dnP  = ((prob.down || 0) * 100).toFixed(1);
    var ub = document.getElementById('prob-up-bar'); if (ub) ub.style.width = upP + '%';
    var db = document.getElementById('prob-dn-bar'); if (db) db.style.width = dnP + '%';
    setText('prob-up-pct', upP + '%');
    setText('prob-dn-pct', dnP + '%');

    /* Bayesian */
    var bay = d.bayesian || {};
    setText('r-bayes-signal', bay.signal || '-');
    setText('r-bayes-method', bay.method || '-');

    /* Indicators */
    var ind = d.indicators || {};
    setText('ind-ma20', ind.ma20   != null ? '\u20B9' + fmtNum(ind.ma20, 2)  : 'N/A');
    setText('ind-ma50', ind.ma50   != null ? '\u20B9' + fmtNum(ind.ma50, 2)  : 'N/A');
    setText('ind-rsi',  ind.rsi    != null ? fmtNum(ind.rsi, 2)              : 'N/A');
    setText('ind-macd', ind.macd   != null ? fmtNum(ind.macd, 4)             : 'N/A');
    setText('ind-vol',  ind.volatility   != null ? (ind.volatility * 100).toFixed(2) + '%' : 'N/A');
    setText('ind-chg',  ind.price_change != null ? ind.price_change.toFixed(4) + '%'       : 'N/A');

    /* Model metrics */
    var met = d.metrics || {};
    var mc  = document.getElementById('pred-metrics-card');
    if (met.accuracy != null && mc) {
      mc.style.display = '';
      setText('m-acc',      fmtNum(met.accuracy         * 100, 1) + '%');
      setText('m-base-acc', fmtNum(met.baseline_accuracy * 100, 1) + '%');
      setText('m-rmse',     '\u20B9' + fmtNum(met.rmse, 2) + ' / \u20B9' + fmtNum(met.baseline_rmse, 2));
    }

    /* Feature importance */
    var fiW = document.getElementById('sp-fi-wrap');
    var fiL = document.getElementById('sp-fi-list');
    var spC = document.getElementById('stock-profile-card');
    if (spC) spC.style.display = '';
    if (d.top_features && d.top_features.length && fiW && fiL) {
      fiW.style.display = '';
      fiL.innerHTML = d.top_features.map(function (f) {
        var pct = (f.importance * 100).toFixed(1);
        return '<div class="fi-bar-wrap">' +
          '<span class="fi-label">' + f.feature + '</span>' +
          '<div class="fi-bar-track"><div class="fi-bar-fill" style="width:' + pct + '%"></div></div>' +
          '<span class="fi-pct">' + pct + '%</span></div>';
      }).join('');
    }

    setText('r-chart-title', d.symbol + ' Price History & Target');
    if (resPan) resPan.style.display = '';

    /* Load Plotly chart */
    if (typeof loadStockChart === 'function') {
      loadStockChart(d.symbol, 'prediction-stock-chart', d.predicted_price);
    }
  }

  /* ── Button click → AJAX predict ──────────────────────────────── */
  if (btn) {
    btn.addEventListener('click', async function () {
      var symbol = selStock ? selStock.value.trim().toUpperCase() : 'TCS';
      var event  = selEvent ? selEvent.value : '';
      showLoading();
      try {
        var resp = await fetch('/api/predict', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ symbol: symbol, event: event || null })
        });
        var data = await resp.json();
        if (!data.success) {
          showError(data.error || 'Unknown server error.');
          return;
        }
        renderResult(data);
      } catch (err) {
        showError('Network error: ' + err.message);
      }
    });
  }

  /* ── Sync dropdowns with URL params on page load (SSR fallback) ── */
  var uP  = new URLSearchParams(window.location.search);
  var sym = uP.get('symbol');
  var ev  = uP.get('event');
  if (sym && selStock) selStock.value = sym;
  if (ev  && selEvent) selEvent.value = ev;
})();
</script>
{% endblock %}
"""

dest = r'd:\SY SEM 1 at VIT Pune\DM CP\DM-Project\Electricity thief detection\StockPrediction\templates\prediction.html'
with open(dest, 'w', encoding='utf-8') as f:
    f.write(TEMPLATE)
print(f'Written {len(TEMPLATE)} chars to {dest}')
