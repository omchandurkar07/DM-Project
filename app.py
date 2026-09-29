"""
app.py — Flask application for Stock Market Prediction System
Graph Theory + Probability + Machine Learning
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
import json, os, traceback
from datetime import datetime

from config import STOCKS, SECTOR_COLORS, SECRET_KEY, DEBUG, HOST, PORT, ADMIN_USERNAME, ADMIN_PASSWORD
from database import init_db, get_connection, fetch_all, fetch_one, execute_query
from models.data_collector import DataCollector
from models.graph          import StockGraph
from models.probability    import ProbabilityEngine
from models.prediction     import PredictionModel
from models.discrete_math  import DiscreteMathEngine

# ─────────────────────────────────────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app)

# Initialise DB tables
init_db()

# Module singletons
collector  = DataCollector()
graph_mdl  = StockGraph()
prob_eng   = ProbabilityEngine()
predictor  = PredictionModel()
dm_eng     = DiscreteMathEngine()


# ─────────────────────────────────────────────────────────────────────────────
# Context Processor — inject global template variables
# ─────────────────────────────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    return {
        'stocks':        STOCKS,
        'sector_colors': SECTOR_COLORS,
        'current_year':  datetime.now().year,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Page Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/')
@app.route('/landing')
def landing_page():
    """Landing page — intro / marketing page for the system."""
    return render_template('landing.html')


@app.route('/dashboard')
def index():
    """Dashboard — Market Summary."""
    market_data     = []
    recent_preds    = []
    data_available  = False

    try:
        for key, info in STOCKS.items():
            rows = fetch_all(
                "SELECT date,close,open,high,low,volume FROM stocks "
                "WHERE company=? ORDER BY date DESC LIMIT 2", (key,)
            )
            if len(rows) >= 2:
                data_available = True
                cur, prev = rows[0], rows[1]
                chg     = cur['close'] - prev['close']
                chg_pct = (chg / prev['close']) * 100 if prev['close'] else 0
                market_data.append({
                    'symbol':    key,
                    'name':      info['name'],
                    'sector':    info['sector'],
                    'color':     info.get('color', '#FFF'),
                    'price':     round(cur['close'], 2),
                    'change':    round(chg, 2),
                    'change_pct': round(chg_pct, 2),
                    'volume':    cur['volume'],
                    'high':      round(cur['high'], 2),
                    'low':       round(cur['low'], 2),
                    'date':      cur['date'],
                })

        recent_preds = fetch_all(
            "SELECT * FROM predictions ORDER BY created_at DESC LIMIT 6"
        )
    except Exception as e:
        print(f"[/] Error: {e}")

    return render_template('index.html',
                           market_data=market_data,
                           recent_preds=recent_preds,
                           data_available=data_available)


@app.route('/predict', methods=['GET'])
@app.route('/predict/<ticker>', methods=['GET'])
def predict_page(ticker=None):
    """Prediction page — form + result."""
    result = None
    selected = ticker or request.args.get('symbol', 'TCS')

    if request.args.get('predict') == 'true':
        try:
            ml_result   = predictor.predict(selected)
            prob_result = prob_eng.get_probability(selected, event=request.args.get('event'))
            result = {**ml_result, 'probability': prob_result}

            # Persist to DB
            execute_query(
                "INSERT INTO predictions "
                "(company,prediction,probability,predicted_price,current_price,algorithm_used) "
                "VALUES (?,?,?,?,?,?)",
                (selected,
                 ml_result['direction'],
                 prob_result['p_up'],
                 ml_result['predicted_price'],
                 ml_result['current_price'],
                 ml_result.get('algorithm_used', 'RandomForest'))
            )
        except Exception as e:
            result = {'error': str(e), 'symbol': selected}

    return render_template('prediction.html', result=result, selected=selected)


@app.route('/graph')
@app.route('/network-graph')
def graph_page():
    """Graph visualization page."""
    return render_template('graph.html')


@app.route('/probability')
def probability_page():
    """Probability analysis page."""
    prob_data = {}
    event     = request.args.get('event', None)
    sym       = request.args.get('symbol', None)

    for key in STOCKS:
        try:
            prob_data[key] = prob_eng.get_probability(key, event=event if key==sym else None)
        except Exception as e:
            print(f"[Probability] {key}: {e}")

    return render_template('probability.html',
                           prob_data=prob_data,
                           selected_event=event,
                           selected_sym=sym)


@app.route('/discrete-math')
def discrete_math_page():
    """Discrete Mathematics analysis hub featuring Graph Theory, Logic, Combinatorics, Sets, Recurrence."""
    graph_res = dm_eng.graph_theory_analysis()
    logic_res = dm_eng.evaluate_boolean_strategy(
        p_volatility=request.args.get('p', '1') == '1',
        q_trend=request.args.get('q', '1') == '1',
        r_rsi=request.args.get('r', '0') == '1',
        s_volume=request.args.get('s', '1') == '1'
    )
    combo_res = dm_eng.combinatorial_subportfolios(int(request.args.get('k', 3)))
    set_res   = dm_eng.set_theory_analysis()
    recur_res = dm_eng.recurrence_analysis(request.args.get('symbol', 'TCS'))

    return render_template('discrete_math.html',
                           graph_res=graph_res,
                           logic_res=logic_res,
                           combo_res=combo_res,
                           set_res=set_res,
                           recur_res=recur_res,
                           selected_sym=request.args.get('symbol', 'TCS'),
                           selected_k=int(request.args.get('k', 3)))


@app.route('/history')
def history_page():
    """Past predictions table."""
    predictions = fetch_all(
        "SELECT * FROM predictions ORDER BY created_at DESC LIMIT 100"
    )
    # Attach company names
    for p in predictions:
        p['name'] = STOCKS.get(p['company'], {}).get('name', p['company'])
    return render_template('history.html', predictions=predictions)


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page."""
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_page'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin_page'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Admin logout route."""
    session.pop('admin_logged_in', None)
    return redirect(url_for('landing_page'))


@app.route('/admin', methods=['GET', 'POST'])
def admin_page():
    """Admin panel — data refresh, model training, graph rebuild."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    messages = []

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'refresh_data':
            try:
                collector.fetch_and_store_all()
                messages.append({'type': 'success',
                                 'text': '✅ Stock data refreshed successfully!'})
            except Exception as e:
                messages.append({'type': 'error', 'text': f'❌ {e}'})

        elif action == 'train_model':
            try:
                m = predictor.train_all()
                ok = sum(1 for v in m.values() if 'error' not in v)
                messages.append({'type': 'success',
                                 'text': f'✅ Models trained for {ok}/{len(m)} stocks!'})
            except Exception as e:
                messages.append({'type': 'error', 'text': f'❌ {e}'})

        elif action == 'rebuild_graph':
            try:
                graph_mdl.build_graph()
                n = graph_mdl.G.number_of_nodes()
                e = graph_mdl.G.number_of_edges()
                messages.append({'type': 'success',
                                 'text': f'✅ Graph rebuilt: {n} nodes, {e} edges'})
            except Exception as e:
                messages.append({'type': 'error', 'text': f'❌ {e}'})

        elif action == 'full_pipeline':
            try:
                collector.fetch_and_store_all()
                graph_mdl.build_graph()
                predictor.train_all()
                messages.append({'type': 'success',
                                 'text': '✅ Full pipeline executed successfully!'})
            except Exception as e:
                messages.append({'type': 'error', 'text': f'❌ {e}'})

    # Stats
    stock_count = fetch_one("SELECT COUNT(*) AS c FROM stocks")
    pred_count  = fetch_one("SELECT COUNT(*) AS c FROM predictions")
    edge_count  = fetch_one("SELECT COUNT(*) AS c FROM graph_edges")

    model_files = []
    try:
        from config import MODEL_DIR
        if os.path.isdir(MODEL_DIR):
            model_files = [f for f in os.listdir(MODEL_DIR) if f.endswith('.pkl')]
    except Exception:
        pass

    return render_template('admin.html',
                           messages=messages,
                           stock_count=(stock_count or {}).get('c', 0),
                           pred_count=(pred_count  or {}).get('c', 0),
                           edge_count=(edge_count  or {}).get('c', 0),
                           model_files=model_files)


# ─────────────────────────────────────────────────────────────────────────────
# API Routes (JSON)
# ─────────────────────────────────────────────────────────────────────────────

@app.route('/api/graph-data')
def api_graph_data():
    """D3.js force-graph data."""
    try:
        data = graph_mdl.get_graph_json()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e), 'nodes': [], 'links': []})


@app.route('/api/predict', methods=['POST'])
def api_predict():
    """AJAX prediction endpoint."""
    body   = request.get_json(force=True) or {}
    symbol = body.get('symbol', 'TCS').upper()
    event  = body.get('event', None)

    try:
        ml   = predictor.predict(symbol)
        prob = prob_eng.get_probability(symbol, event=event)
        execute_query(
            "INSERT INTO predictions "
            "(company,prediction,probability,predicted_price,current_price,algorithm_used) "
            "VALUES (?,?,?,?,?,?)",
            (symbol, ml['direction'], prob['p_up'],
             ml['predicted_price'], ml['current_price'],
             ml.get('algorithm_used', 'RF'))
        )
        return jsonify({'success': True, **ml, 'probability': prob})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/stock-history/<ticker>')
def api_stock_history(ticker):
    """OHLCV + indicator time-series for Plotly charts."""
    limit = int(request.args.get('limit', 180))
    rows  = fetch_all(
        "SELECT date,open,high,low,close,volume,ma20,ma50,rsi,macd "
        "FROM stocks WHERE company=? ORDER BY date DESC LIMIT ?",
        (ticker.upper(), limit)
    )
    rows.reverse()
    return jsonify(rows)


@app.route('/api/graph-algorithm/<algorithm>')
def api_graph_algorithm(algorithm):
    """Run a graph algorithm and return JSON result."""
    start = request.args.get('start', 'TCS').upper()
    end   = request.args.get('end',   'RELIANCE').upper()

    algo_map = {
        'bfs':      lambda: graph_mdl.bfs(start),
        'dfs':      lambda: graph_mdl.dfs(start),
        'dijkstra': lambda: graph_mdl.dijkstra(start, end),
        'pagerank': lambda: graph_mdl.pagerank(),
        'mst':      lambda: graph_mdl.minimum_spanning_tree(),
    }

    fn = algo_map.get(algorithm.lower())
    if not fn:
        return jsonify({'error': f'Unknown algorithm: {algorithm}'})
    try:
        return jsonify({'success': True, 'result': fn()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/probability/<ticker>')
def api_probability(ticker):
    """Probability data for a single stock, with optional event."""
    event = request.args.get('event', None)
    try:
        data = prob_eng.get_probability(ticker.upper(), event=event)
        return jsonify({'success': True, **data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/market-ticker')
def api_market_ticker():
    """Lightweight market ticker data for the top bar."""
    data = []
    for key, info in STOCKS.items():
        rows = fetch_all(
            "SELECT close FROM stocks WHERE company=? ORDER BY date DESC LIMIT 2",
            (key,)
        )
        if len(rows) >= 2:
            chg_pct = ((rows[0]['close'] - rows[1]['close']) / rows[1]['close']) * 100
            data.append({
                'symbol':     key,
                'name':       info['name'],
                'price':      round(rows[0]['close'], 2),
                'change_pct': round(chg_pct, 2),
            })
    return jsonify(data)


@app.route('/api/rebuild-graph', methods=['POST'])
def api_rebuild_graph():
    """Rebuild graph edges based on current stock returns in the DB."""
    try:
        graph_mdl.build_graph()
        n = graph_mdl.G.number_of_nodes()
        e = graph_mdl.G.number_of_edges()
        return jsonify({'success': True, 'nodes': n, 'edges': e})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/refresh-all', methods=['POST'])
def api_refresh_all():
    """Full pipeline: fetch → graph → train."""
    try:
        collector.fetch_and_store_all()
        graph_mdl.build_graph()
        predictor.train_all()
        return jsonify({'success': True, 'message': 'Full pipeline completed!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Auto-initialise if database is empty
    try:
        count = fetch_one("SELECT COUNT(*) AS c FROM stocks") or {}
        if count.get('c', 0) == 0:
            print("[App] No data found — running initial data fetch …")
            collector.fetch_and_store_all()
            graph_mdl.build_graph()
            predictor.train_all()
            print("[App] Initialisation complete.")
    except Exception as e:
        print(f"[App] Init warning: {e}")

    app.run(debug=DEBUG, host=HOST, port=PORT)
