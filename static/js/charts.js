/* static/js/charts.js — Plotly Stock Candlestick and Line Charts */

async function loadStockChart(symbol, containerId, targetPrice = null, latestQuote = null) {
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
    const bigint = Number.parseInt(hex.replace('#', ''), 16);
    return `${(bigint >> 16) & 255}, ${(bigint >> 8) & 255}, ${bigint & 255}`;
  };

  try {
    const res = await fetch(`/api/stock-history/${symbol}?limit=120`);
    if (!res.ok) throw new Error(`History request failed (${res.status})`);
    const data = await res.json();

    if (!data || data.length === 0) {
      container.innerHTML = '<div class="text-center py-5 text-muted">No price history available.</div>';
      return;
    }

    const dates  = data.map(d => d.date);
    const closes = data.map(d => d.close);
    const ma20   = data.map(d => d.ma20);
    const ma50   = data.map(d => d.ma50);
    const lastClose = closes[closes.length - 1];
    const firstClose = closes[0];
    const livePrice = latestQuote && Number.isFinite(Number(latestQuote.price))
      ? Number(latestQuote.price) : lastClose;
    const highest = Math.max(...data.map(d => Number(d.high)).filter(Number.isFinite));
    const lowest = Math.min(...data.map(d => Number(d.low)).filter(Number.isFinite));
    const changePct = firstClose ? ((livePrice / firstClose) - 1) * 100 : 0;

    const fmtPrice = value => `₹${Number(value).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`;
    const summaryLatest = document.getElementById('home-chart-latest');
    const summaryChange = document.getElementById('home-chart-change');
    const summaryRange = document.getElementById('home-chart-range');
    const summaryDate = document.getElementById('home-chart-date');
    if (summaryLatest) summaryLatest.textContent = fmtPrice(livePrice);
    if (summaryChange) {
      summaryChange.textContent = `${changePct > 0 ? '+' : ''}${changePct.toFixed(2)}%`;
      summaryChange.classList.toggle('is-positive', changePct > 0);
      summaryChange.classList.toggle('is-negative', changePct < 0);
    }
    if (summaryRange) summaryRange.textContent =
      `${fmtPrice(Math.max(highest, livePrice))} / ${fmtPrice(Math.min(lowest, livePrice))}`;
    if (summaryDate) summaryDate.textContent =
      latestQuote && latestQuote.display_time
        ? `Quote ${latestQuote.display_time}`
        : `History through ${dates[dates.length - 1]}`;

    // A lightly filled line emphasizes the trend without distorting daily moves.
    const traceClose = {
      x: dates,
      y: closes,
      type: 'scatter',
      mode: 'lines',
      name: `${symbol} Price`,
      line: { color: mainColor, width: 2.8 },
      fill: 'tozeroy',
      fillcolor: `rgba(${hexToRgb(mainColor)}, 0.07)`,
      hovertemplate: '<b>%{x|%d %b %Y}</b><br>Close: ₹%{y:,.2f}<extra></extra>',
    };

    // Moving Averages Traces
    const traceMA20 = {
      x: dates,
      y: ma20,
      type: 'scatter',
      mode: 'lines',
      name: 'MA20',
      line: { color: '#fbbf24', width: 1.8, dash: 'dot' },
      hovertemplate: 'MA20: ₹%{y:,.2f}<extra></extra>',
    };

    const traceMA50 = {
      x: dates,
      y: ma50,
      type: 'scatter',
      mode: 'lines',
      name: 'MA50',
      line: { color: '#c084fc', width: 1.8, dash: 'dash' },
      hovertemplate: 'MA50: ₹%{y:,.2f}<extra></extra>',
    };

    const traces = [traceClose, traceMA20, traceMA50];
    traces.push({
      x: [dates[dates.length - 1]],
      y: [lastClose],
      type: 'scatter',
      mode: 'markers',
      name: 'Latest close',
      showlegend: false,
      marker: {
        color: mainColor,
        size: 9,
        line: { color: '#e0f2fe', width: 2 }
      },
      hovertemplate: '<b>Latest close</b><br>₹%{y:,.2f}<extra></extra>',
    });

    if (latestQuote && latestQuote.timestamp && Number.isFinite(Number(latestQuote.price))) {
      const quoteX = latestQuote.timestamp;
      const quoteDate = String(quoteX).slice(0, 10);
      if (quoteDate >= dates[dates.length - 1]) {
        traces.push({
          x: [dates[dates.length - 1], quoteX],
          y: [lastClose, livePrice],
          type: 'scatter',
          mode: 'lines+markers',
          name: latestQuote.is_intraday ? 'Latest intraday price' : 'Latest quote',
          line: { color: '#f8fafc', width: 2, dash: 'dot' },
          marker: {
            color: '#f8fafc',
            size: [0, 9],
            line: { color: mainColor, width: 3 },
          },
          hovertemplate: '<b>Latest available price</b><br>₹%{y:,.2f}<extra></extra>',
        });
      }
    }

    const visiblePrices = [...closes, ...ma20.filter(Number.isFinite), ...ma50.filter(Number.isFinite), livePrice];
    const minVisiblePrice = Math.min(...visiblePrices);
    const maxVisiblePrice = Math.max(...visiblePrices);

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
      margin: { l: 68, r: 82, t: 108, b: 48 },
      showlegend: true,
      legend: {
        x: 0.5, y: 1.28,
        xanchor: 'center',
        orientation: 'h',
        font: { color: '#cbd5e1', size: 11 },
        bgcolor: 'transparent',
        itemsizing: 'constant',
      },
      xaxis: {
        gridcolor: 'rgba(148, 163, 184, 0.09)',
        linecolor: 'rgba(148, 163, 184, 0.18)',
        tickfont: { color: '#94a3b8', size: 10 },
        tickformat: '%b %Y',
        rangeslider: { visible: false },
        rangeselector: {
          x: 0,
          y: 1.13,
          buttons: [
            { count: 1, label: '1M', step: 'month', stepmode: 'backward' },
            { count: 3, label: '3M', step: 'month', stepmode: 'backward' },
            { count: 6, label: '6M', step: 'month', stepmode: 'backward' },
            { step: 'all', label: 'All' }
          ],
          font: { color: '#dbeafe', size: 10 },
          bgcolor: 'rgba(30, 41, 59, 0.82)',
          activecolor: mainColor,
          bordercolor: 'rgba(148, 163, 184, 0.2)',
          borderwidth: 1,
        }
      },
      yaxis: {
        gridcolor: 'rgba(148, 163, 184, 0.1)',
        zeroline: false,
        rangemode: 'normal',
        range: [
          minVisiblePrice * 0.97,
          maxVisiblePrice * 1.03,
        ],
        tickfont: { color: '#94a3b8', size: 10 },
        tickprefix: '₹',
        tickformat: ',.0f',
        title: { text: 'Price (INR)', font: { color: '#94a3b8', size: 10 } },
      },
      annotations: [{
        xref: 'paper',
        x: 1.015,
        y: livePrice,
        yref: 'y',
        text: fmtPrice(livePrice),
        showarrow: false,
        xanchor: 'left',
        bgcolor: mainColor,
        borderpad: 5,
        font: { color: '#06111f', size: 10, family: 'Inter, sans-serif' },
      },
      ],
      hovermode: 'x unified',
      hoverlabel: {
        bgcolor: '#0f1b2d',
        bordercolor: 'rgba(148, 163, 184, 0.25)',
        font: { color: '#e2e8f0', family: 'Inter, sans-serif', size: 11 },
      },
    };

    const config = { responsive: true, displayModeBar: false };

    await Plotly.react(containerId, traces, layout, config);

  } catch (err) {
    console.error('Chart load error:', err);
    const summaryLatest = document.getElementById('home-chart-latest');
    if (summaryLatest) summaryLatest.textContent = 'Unavailable';
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
