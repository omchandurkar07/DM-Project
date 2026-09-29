/* static/js/charts.js — Plotly Stock Candlestick and Line Charts */

async function loadStockChart(symbol, containerId, targetPrice = null) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const symbolColors = {
    'RELIANCE': '#FF6B35',
    'TCS': '#00D4FF',
    'INFY': '#00B4D8',
    'HDFCBANK': '#7B2FBE',
    'ICICIBANK': '#9D4EDD',
    'WIPRO': '#4CC9F0',
    'HINDUNILVR': '#F72585',
    'TATAMOTORS': '#4CAF50'
  };
  const mainColor = symbolColors[symbol.toUpperCase()] || '#00d4ff';

  const hexToRgb = hex => {
    const bigint = parseInt(hex.replace('#', ''), 16);
    return `${(bigint >> 16) & 255}, ${(bigint >> 8) & 255}, ${bigint & 255}`;
  };

  try {
    const res = await fetch(`/api/stock-history/${symbol}?limit=120`);
    const data = await res.json();

    if (!data || data.length === 0) {
      container.innerHTML = '<div class="text-center py-5 text-muted">No price history available.</div>';
      return;
    }

    const dates  = data.map(d => d.date);
    const closes = data.map(d => d.close);
    const ma20   = data.map(d => d.ma20);
    const ma50   = data.map(d => d.ma50);

    // Main line chart with smooth spline and gradient fill
    const traceClose = {
      x: dates,
      y: closes,
      type: 'scatter',
      mode: 'lines',
      name: `${symbol} Price`,
      line: { color: mainColor, width: 2.2, shape: 'spline' },
      fill: 'tozeroy',
      fillcolor: `rgba(${hexToRgb(mainColor)}, 0.08)`,
    };

    // Moving Averages Traces
    const traceMA20 = {
      x: dates,
      y: ma20,
      type: 'scatter',
      mode: 'lines',
      name: 'MA20',
      line: { color: '#f59e0b', width: 1.2, dash: 'dot' }
    };

    const traceMA50 = {
      x: dates,
      y: ma50,
      type: 'scatter',
      mode: 'lines',
      name: 'MA50',
      line: { color: '#9d4edd', width: 1.2, dash: 'dash' }
    };

    const traces = [traceClose, traceMA20, traceMA50];

    // If target price provided, add predicted point for the next trading day (skipping weekends)
    if (targetPrice) {
      const parts = dates[dates.length - 1].split('-');
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10) - 1;
      const day = parseInt(parts[2], 10);
      const lastDate = new Date(year, month, day);

      let daysToAdd = 1;
      const dayOfWeek = lastDate.getDay(); // 0 = Sunday, 5 = Friday, 6 = Saturday
      if (dayOfWeek === 5) {
        daysToAdd = 3;
      } else if (dayOfWeek === 6) {
        daysToAdd = 2;
      }

      lastDate.setDate(lastDate.getDate() + daysToAdd);
      const nextYear = lastDate.getFullYear();
      const nextMonth = String(lastDate.getMonth() + 1).padStart(2, '0');
      const nextDay = String(lastDate.getDate()).padStart(2, '0');
      const nextDateStr = `${nextYear}-${nextMonth}-${nextDay}`;

      const traceTarget = {
        x: [dates[dates.length - 1], nextDateStr],
        y: [closes[closes.length - 1], targetPrice],
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Predicted Target',
        line: { color: targetPrice >= closes[closes.length - 1] ? '#10b981' : '#ef4444', width: 2.2, dash: 'longdash' },
        marker: { size: 9, symbol: 'star-diamond' }
      };
      traces.push(traceTarget);
    }

    const layout = {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      margin: { l: 55, r: 25, t: 45, b: 35 },
      showlegend: true,
      legend: {
        x: 0.01, y: 1.15,
        orientation: 'h',
        font: { color: '#94a3b8', size: 10 },
        bgcolor: 'transparent',
      },
      xaxis: {
        gridcolor: 'rgba(255, 255, 255, 0.05)',
        tickfont: { color: '#94a3b8', size: 10 },
        rangeslider: { visible: false },
        rangeselector: {
          buttons: [
            { count: 1, label: '1M', step: 'month', stepmode: 'backward' },
            { count: 3, label: '3M', step: 'month', stepmode: 'backward' },
            { count: 6, label: '6M', step: 'month', stepmode: 'backward' },
            { step: 'all', label: 'All' }
          ],
          font: { color: '#e2e8f0', size: 10 },
          bgcolor: '#1e293b',
          activecolor: '#00d4ff'
        }
      },
      yaxis: {
        gridcolor: 'rgba(255, 255, 255, 0.05)',
        tickfont: { color: '#94a3b8', size: 10 },
        tickprefix: '₹',
        title: { text: 'Stock Price', font: { color: '#94a3b8', size: 10 } }
      },
      hovermode: 'x unified',
    };

    const config = { responsive: true, displayModeBar: false };

    Plotly.newPlot(containerId, traces, layout, config);

  } catch (err) {
    console.error('Chart load error:', err);
  }
}

async function loadSparkline(symbol, containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  try {
    const res = await fetch(`/api/stock-history/${symbol}?limit=30`);
    const data = await res.json();

    if (!data || data.length === 0) {
      container.style.display = 'none';
      return;
    }

    const dates  = data.map(d => d.date);
    const closes = data.map(d => d.close);
    const isUp = closes[closes.length - 1] >= closes[0];

    const trace = {
      x: dates,
      y: closes,
      type: 'scatter',
      mode: 'lines',
      line: {
        color: isUp ? '#10b981' : '#ef4444',
        width: 1.8,
        shape: 'spline'
      },
      fill: 'tozeroy',
      fillcolor: isUp ? 'rgba(16, 185, 129, 0.05)' : 'rgba(239, 68, 68, 0.05)',
      hoverinfo: 'none'
    };

    const layout = {
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      margin: { l: 0, r: 0, t: 2, b: 2 },
      showlegend: false,
      xaxis: { visible: false },
      yaxis: { visible: false },
      hovermode: false
    };

    const config = { responsive: true, displayModeBar: false, staticPlot: true };

    Plotly.newPlot(containerId, [trace], layout, config);

  } catch (err) {
    console.error('Sparkline load error:', err);
  }
}
