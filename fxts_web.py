#!/usr/bin/env python3
"""
fxts_web.py - Browser-based UI for FXTS (replaces FXTSgui.py)

Starts a Flask web server and opens the dashboard in the default browser.
The UI replicates the PyQt5 window: a portfolio summary panel and a live
scrolling log panel, plus Print Portfolio and Test DB actions.

Usage:
    python3 fxts_web.py [--port PORT] [--no-browser]

Configuration (same as FXTSgui.py):
    config.ini [database] / [portfolio] sections, or environment variables:
        FXDB_HOST, FXDB_USER, FXDB_PASSWD, FXDB_NAME, FXTS_PORTFOLIO
"""

import collections
import configparser
import datetime
import json
import os
import queue
import sys
import threading
import time as tm
import traceback
import webbrowser
import argparse

from flask import Flask, Response, jsonify, render_template_string, send_from_directory

import DBConnector as db
import FXPortfolio as fxPf

# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _get_portfolio_name():
    cfg = configparser.ConfigParser()
    cfg.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    return os.environ.get('FXTS_PORTFOLIO',
                          cfg.get('portfolio', 'name', fallback='FX Portfolio 1'))


# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

# Ring-buffer of the last 500 log entries so new browser connections can
# catch up, plus a list of SSE subscriber queues for live streaming.
_LOG_HISTORY  = collections.deque(maxlen=500)
_SSE_CLIENTS  = []
_SSE_LOCK     = threading.Lock()
_portfolio    = None
_logfile      = None


def _write_log(message, status='I'):
    """Timestamped logger: appends to history, fans out to SSE clients, writes file."""
    timelog = tm.strftime('%Y%m%d.%H%M%S', tm.gmtime())
    entry = {'ts': timelog, 'status': status, 'msg': message}
    _LOG_HISTORY.append(entry)

    raw = "%s :-%-1s-%s" % (timelog, status, message)
    print(raw)

    if _logfile:
        try:
            _logfile.write(raw + '\n')
            _logfile.flush()
        except Exception:
            pass

    payload = 'data: ' + json.dumps(entry) + '\n\n'
    with _SSE_LOCK:
        dead = []
        for q in _SSE_CLIENTS:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _SSE_CLIENTS.remove(q)


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config['SECRET_KEY'] = 'fxts-dev'

_STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')


@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(_STATIC_DIR, filename)


# ---------------------------------------------------------------------------
# Hourly price-refresh scheduler
# ---------------------------------------------------------------------------

_next_run_utc = None   # datetime of the next scheduled price fetch


def _run_price_refresh():
    """Background task: fetch prices then recalculate signals."""
    global _portfolio
    if _portfolio is None:
        _write_log("Scheduler: portfolio not loaded, skipping refresh")
        _schedule_next_refresh()
        return
    _write_log("Scheduler: starting hourly price refresh")
    try:
        _portfolio.refreshAllPrices()
        _portfolio.refreshAllEntrySignals()
        _write_log("Scheduler: refresh complete")
    except Exception as e:
        _write_log("Scheduler: refresh failed: %s\n%s" % (e, traceback.format_exc()), status='E')
    _schedule_next_refresh()


def _schedule_next_refresh():
    """Schedule the next run at the top of the next UTC hour (+5 s buffer)."""
    global _next_run_utc
    now = datetime.datetime.utcnow()
    _next_run_utc = (now + datetime.timedelta(hours=1)).replace(minute=0, second=5, microsecond=0)
    delay = (_next_run_utc - now).total_seconds()
    t = threading.Timer(delay, _run_price_refresh)
    t.daemon = True
    t.start()
    _write_log("Scheduler: next price fetch at %s UTC" % _next_run_utc.strftime('%Y-%m-%d %H:%M:%S'))


# ---- HTML template ---------------------------------------------------------

_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FXTS</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:        #0d1117;
    --surface:   #161b22;
    --border:    #30363d;
    --accent:    #58a6ff;
    --green:     #3fb950;
    --yellow:    #d29922;
    --red:       #f85149;
    --text:      #c9d1d9;
    --muted:     #8b949e;
    --nav-h:     48px;
  }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 14px;
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* ── Navbar ─────────────────────────────────────────────── */
  nav {
    height: var(--nav-h);
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 16px;
    gap: 12px;
    flex-shrink: 0;
  }
  nav .brand {
    font-size: 18px;
    font-weight: 700;
    color: var(--accent);
    letter-spacing: 2px;
    margin-right: 16px;
  }
  nav .subtitle {
    color: var(--muted);
    font-size: 12px;
    flex: 1;
  }
  nav button {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text);
    padding: 5px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    transition: background 0.15s, border-color 0.15s;
  }
  nav button:hover { background: var(--border); border-color: var(--accent); }
  nav button.primary { border-color: var(--accent); color: var(--accent); }
  nav button.primary:hover { background: rgba(88,166,255,0.12); }
  #status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: var(--muted); flex-shrink: 0;
    transition: background 0.3s;
  }
  #status-dot.ok  { background: var(--green); }
  #status-dot.err { background: var(--red);   }

  /* ── Main layout ─────────────────────────────────────────── */
  main {
    flex: 1;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
    overflow: hidden;
  }

  section {
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border-right: 1px solid var(--border);
  }
  section:last-child { border-right: none; }

  .pane-header {
    padding: 10px 16px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    background: var(--surface);
    flex-shrink: 0;
  }

  /* ── Portfolio pane ──────────────────────────────────────── */
  #portfolio-pane {
    padding: 16px;
    overflow-y: auto;
    flex: 1;
  }
  .pfo-name {
    font-size: 16px;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 16px;
  }
  .engine-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 12px;
  }
  .engine-title {
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 8px;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .engine-title .badge {
    font-size: 10px;
    padding: 2px 7px;
    border-radius: 20px;
    font-weight: 500;
    background: rgba(88,166,255,0.15);
    color: var(--accent);
  }
  .kv-grid {
    display: grid;
    grid-template-columns: 130px 1fr;
    gap: 4px 8px;
    font-size: 12px;
  }
  .kv-grid .k { color: var(--muted); }
  .kv-grid .v { color: var(--text);  font-family: monospace; }
  .price-row {
    margin-top: 10px;
    padding: 8px 10px;
    background: rgba(63,185,80,0.07);
    border: 1px solid rgba(63,185,80,0.2);
    border-radius: 6px;
    font-family: monospace;
    font-size: 12px;
    color: var(--green);
  }
  .siggens {
    margin-top: 10px;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .sig-chip {
    font-size: 11px;
    padding: 3px 9px;
    border-radius: 4px;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    color: var(--muted);
    font-family: monospace;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .sig-badge {
    font-size: 10px;
    font-weight: 700;
    padding: 1px 5px;
    border-radius: 3px;
    letter-spacing: 0.04em;
  }
  .sig-badge.LONG  { background: rgba(63,185,80,0.2);  color: var(--green); }
  .sig-badge.SHORT { background: rgba(248,81,73,0.2);  color: var(--red);   }
  .sig-badge.FLAT  { background: rgba(255,255,255,0.07); color: var(--muted); }
  #portfolio-loading { color: var(--muted); font-style: italic; padding: 12px 0; }
  #next-refresh { color: var(--muted); font-size: 11px; }

  /* ── Log pane ────────────────────────────────────────────── */
  #log-pane {
    flex: 1;
    overflow-y: auto;
    padding: 10px 14px;
    font-family: 'Cascadia Code', 'Fira Code', monospace;
    font-size: 12px;
    line-height: 1.7;
    background: var(--bg);
  }
  .log-I { color: var(--text); }
  .log-W { color: var(--yellow); }
  .log-E { color: var(--red); font-weight: 600; }
  .log-ts { color: var(--muted); margin-right: 6px; user-select: none; }
  .log-badge {
    display: inline-block;
    width: 16px;
    text-align: center;
    margin-right: 4px;
    border-radius: 2px;
    font-size: 10px;
  }
  .log-badge.I { color: var(--green); }
  .log-badge.W { color: var(--yellow); }
  .log-badge.E { color: var(--red); }

  /* ── Chart button (inside engine card) ──────────────────── */
  .chart-btn {
    margin-left: auto;
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 2px 9px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 11px;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
  }
  .chart-btn:hover { background: var(--border); border-color: var(--accent); color: var(--accent); }

  /* ── Chart modal ─────────────────────────────────────────── */
  #chart-modal {
    position: fixed;
    inset: 0;
    z-index: 200;
    display: none;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.78);
  }
  #chart-modal.open { display: flex; }
  #chart-box {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    width: min(96vw, 1140px);
    max-height: 92vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-shadow: 0 28px 64px rgba(0,0,0,0.65);
  }
  #chart-header {
    display: flex;
    align-items: center;
    padding: 11px 16px;
    border-bottom: 1px solid var(--border);
    gap: 10px;
    flex-shrink: 0;
  }
  #chart-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--accent);
    white-space: nowrap;
  }
  #chart-pills { display: flex; gap: 6px; flex: 1; flex-wrap: wrap; }
  #chart-close-btn {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--muted);
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    flex-shrink: 0;
  }
  #chart-close-btn:hover { background: var(--border); color: var(--text); }
  #chart-area { flex: 1; min-height: 440px; background: #0d1117; }
  #chart-legend {
    padding: 7px 16px;
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-size: 11px;
    font-family: monospace;
    border-top: 1px solid var(--border);
    background: var(--surface);
    color: var(--muted);
    flex-shrink: 0;
    min-height: 30px;
    align-items: center;
  }
  .legend-item { display: flex; align-items: center; gap: 5px; }
  .legend-swatch { width: 22px; height: 2px; border-radius: 1px; flex-shrink: 0; }

  /* ── Toast ───────────────────────────────────────────────── */
  #toast {
    position: fixed;
    bottom: 20px; right: 20px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
    max-width: 340px;
  }
  #toast.show { opacity: 1; }
  #toast.ok  { border-color: var(--green); color: var(--green); }
  #toast.err { border-color: var(--red);   color: var(--red);   }
</style>
</head>
<body>

<nav>
  <span class="brand">FXTS</span>
  <span class="subtitle" id="nav-subtitle">Connecting…</span>
  <span id="next-refresh"></span>
  <button class="primary" onclick="fetchPrices()">&#8659; Fetch Prices</button>
  <button onclick="loadPortfolio()">&#8635; Refresh</button>
  <button onclick="printPortfolio()">Print Portfolio</button>
  <button onclick="testDB()">Test DB</button>
  <div id="status-dot" title="Log stream"></div>
</nav>

<main>
  <section>
    <div class="pane-header">Portfolio</div>
    <div id="portfolio-pane">
      <p id="portfolio-loading">Loading…</p>
    </div>
  </section>

  <section>
    <div class="pane-header">Live Log</div>
    <div id="log-pane"></div>
  </section>
</main>

<div id="toast"></div>

<!-- ── Chart modal ──────────────────────────────────────────────────────── -->
<div id="chart-modal">
  <div id="chart-box">
    <div id="chart-header">
      <span id="chart-title"></span>
      <div id="chart-pills"></div>
      <button id="chart-close-btn" onclick="closeChart()">&#x2715; Close</button>
    </div>
    <div id="chart-area"></div>
    <div id="chart-legend"></div>
  </div>
</div>

<script>
// ── Utilities ────────────────────────────────────────────────────────────────

function toast(msg, type='ok') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'show ' + type;
  clearTimeout(el._t);
  el._t = setTimeout(() => { el.className = ''; }, 3500);
}

// ── Log streaming (SSE) ───────────────────────────────────────────────────────

const logPane = document.getElementById('log-pane');
let autoScroll = true;
logPane.addEventListener('scroll', () => {
  autoScroll = logPane.scrollHeight - logPane.scrollTop - logPane.clientHeight < 40;
});

function appendLog(entry) {
  const line = document.createElement('div');
  line.className = 'log-' + entry.status;
  line.innerHTML =
    `<span class="log-ts">${entry.ts}</span>` +
    `<span class="log-badge ${entry.status}">${entry.status}</span>` +
    escapeHtml(entry.msg);
  logPane.appendChild(line);
  if (autoScroll) logPane.scrollTop = logPane.scrollHeight;
}

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Fetch log history, then open SSE stream
fetch('/api/log/history')
  .then(r => r.json())
  .then(entries => {
    entries.forEach(appendLog);
    startSSE();
  });

function startSSE() {
  const dot = document.getElementById('status-dot');
  const es = new EventSource('/api/log/stream');
  es.onopen    = () => { dot.className = 'ok'; };
  es.onerror   = () => { dot.className = 'err'; setTimeout(startSSE, 3000); es.close(); };
  es.onmessage = e => { appendLog(JSON.parse(e.data)); };
}

// ── Portfolio ─────────────────────────────────────────────────────────────────

function loadPortfolio() {
  document.getElementById('portfolio-loading').style.display = 'block';
  document.getElementById('portfolio-loading').textContent = 'Loading…';

  fetch('/api/portfolio')
    .then(r => r.json())
    .then(data => renderPortfolio(data))
    .catch(err => toast('Portfolio fetch failed: ' + err, 'err'));
}

function renderPortfolio(data) {
  const pane = document.getElementById('portfolio-pane');
  if (data.error) {
    pane.innerHTML = `<p style="color:var(--red)">${escapeHtml(data.error)}</p>`;
    return;
  }

  document.getElementById('nav-subtitle').textContent =
    data.name + ' \u2014 ' + data.engines.length + ' engine(s)';

  let html = `<div class="pfo-name">${escapeHtml(data.name)}</div>`;

  data.engines.forEach(eng => {
    const fx = eng.instrument;
    const priceHtml = fx.last_price
      ? `<div class="price-row">${escapeHtml(fx.last_price)}</div>` : '';

    const sigHtml = eng.signal_generators.map(sg => {
      const label = sg.signal === 1 ? 'LONG' : sg.signal === -1 ? 'SHORT' : 'FLAT';
      const tip = `nMA6=${sg.nMA6} nMA6_1=${sg.nMA6_1}` +
        (sg.fast_ma != null ? ` | fast=${sg.fast_ma} slow=${sg.slow_ma}` : '');
      return `<span class="sig-chip" title="${tip}">${escapeHtml(sg.name)}` +
             `<span class="sig-badge ${label}">${label}</span></span>`;
    }).join('');

    html += `
      <div class="engine-card">
        <div class="engine-title">
          ${escapeHtml(eng.name)}
          <span class="badge">${escapeHtml(fx.cross_name || '')}</span>
          <button class="chart-btn" onclick="openChart(${JSON.stringify(eng.name)}, ${JSON.stringify(fx.cross_name)})">&#128202; Chart</button>
        </div>
        <div class="kv-grid">
          <span class="k">Instrument</span>
          <span class="v">${escapeHtml(fx.cross_name)} [${escapeHtml(fx.base_ccy)}/${escapeHtml(fx.quote_ccy)}]</span>
          <span class="k">Scalar</span>
          <span class="v">${fx.scalar}</span>
          <span class="k">Price bars</span>
          <span class="v">${fx.bar_count}</span>
        </div>
        ${priceHtml}
        <div class="siggens">${sigHtml}</div>
      </div>`;
  });

  pane.innerHTML = html;
}

// ── Actions ───────────────────────────────────────────────────────────────────

function printPortfolio() {
  fetch('/api/portfolio/print', { method: 'POST' })
    .then(r => r.json())
    .then(d => toast(d.message || d.error, d.error ? 'err' : 'ok'));
}

function testDB() {
  toast('Testing DB connection…');
  fetch('/api/db/test', { method: 'POST' })
    .then(r => r.json())
    .then(d => toast(d.message || d.error, d.error ? 'err' : 'ok'));
}

function fetchPrices() {
  toast('Fetching prices…');
  fetch('/api/prices/refresh', { method: 'POST' })
    .then(r => r.json())
    .then(d => {
      toast(d.message || d.error, d.error ? 'err' : 'ok');
      if (!d.error) loadPortfolio();
    });
}

// ── Chart ─────────────────────────────────────────────────────────────────────

const _LWC_CDN = '/static/lightweight-charts.standalone.production.js';
let _lwcReady  = false;
let _activeChart = null;
const _MA_COLORS = ['#58a6ff','#d29922','#f97583','#bc8cff','#79c0ff','#ffa657'];

function _loadLWC() {
  if (_lwcReady) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = _LWC_CDN;
    s.onload  = () => { _lwcReady = true; resolve(); };
    s.onerror = ()  => reject(new Error('Chart library failed to load from CDN. Check network access.'));
    document.head.appendChild(s);
  });
}

function openChart(engineName, crossName) {
  const modal = document.getElementById('chart-modal');
  modal.classList.add('open');
  document.getElementById('chart-title').textContent = engineName + '  ·  ' + crossName;
  document.getElementById('chart-pills').innerHTML   = '';
  document.getElementById('chart-legend').textContent = 'Loading chart data…';
  document.getElementById('chart-area').innerHTML    = '';
  if (_activeChart) { try { _activeChart.remove(); } catch(e) {} _activeChart = null; }

  _loadLWC()
    .then(() => fetch('/api/charts/' + encodeURIComponent(engineName)))
    .then(r => r.json())
    .then(data => {
      if (data.error) throw new Error(data.error);
      _renderChart(data);
    })
    .catch(err => {
      document.getElementById('chart-area').innerHTML =
        `<p style="color:var(--red);padding:24px;font-family:monospace;font-size:13px">${escapeHtml(String(err))}</p>`;
      document.getElementById('chart-legend').textContent = '';
    });
}

function closeChart() {
  document.getElementById('chart-modal').classList.remove('open');
  if (_activeChart) { try { _activeChart.remove(); } catch(e) {} _activeChart = null; }
}

document.getElementById('chart-modal').addEventListener('click', e => {
  if (e.target === document.getElementById('chart-modal')) closeChart();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeChart(); });

function _renderChart(data) {
  const area = document.getElementById('chart-area');
  area.innerHTML = '';

  const chart = LightweightCharts.createChart(area, {
    width:  area.clientWidth,
    height: area.clientHeight || 440,
    layout:      { background: { type: 'solid', color: '#0d1117' }, textColor: '#c9d1d9' },
    grid:        { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
    crosshair:   { mode: LightweightCharts.CrosshairMode.Normal },
    timeScale:   { timeVisible: true, secondsVisible: false, borderColor: '#30363d' },
    rightPriceScale: { borderColor: '#30363d' },
  });
  _activeChart = chart;

  // Keep chart filling the container when the window resizes
  new ResizeObserver(() => {
    chart.applyOptions({ width: area.clientWidth, height: area.clientHeight });
  }).observe(area);

  // Candlestick series
  const cSeries = chart.addCandlestickSeries({
    upColor: '#3fb950', downColor: '#f85149',
    borderUpColor: '#3fb950', borderDownColor: '#f85149',
    wickUpColor:   '#3fb950', wickDownColor:   '#f85149',
  });
  cSeries.setData(data.candles);

  // MA line series + legend metadata
  const legendMeta = [];
  let colorIdx = 0;
  const allLineSeries = [];

  data.ma_series.forEach(sg => {
    [['fast', sg.fast], ['slow', sg.slow]].forEach(([type, series]) => {
      if (!series.data.length) return;
      const color = _MA_COLORS[colorIdx++ % _MA_COLORS.length];
      const label = `${sg.name} SMA(${series.period})`;
      const ls = chart.addLineSeries({
        color, lineWidth: 1,
        priceLineVisible: false, lastValueVisible: true, title: label,
      });
      ls.setData(series.data);
      legendMeta.push({ label, color, series: ls });
      allLineSeries.push({ ls, label, color });
    });
    // Signal pills in header
    const lbl = sg.signal === 1 ? 'LONG' : sg.signal === -1 ? 'SHORT' : 'FLAT';
    document.getElementById('chart-pills').innerHTML +=
      `<span class="sig-badge ${lbl}" style="font-size:11px">${escapeHtml(sg.name)}: ${lbl}</span>`;
  });

  // Dynamic legend — updates on crosshair move
  const legendEl = document.getElementById('chart-legend');

  function setLegend(param) {
    let html = '';
    if (param && param.time) {
      const c = param.seriesData && param.seriesData.get(cSeries);
      if (c) html += `<span class="legend-item" style="color:var(--text)">
        O&nbsp;<b>${c.open}</b>&nbsp; H&nbsp;<b>${c.high}</b>&nbsp; L&nbsp;<b>${c.low}</b>&nbsp; C&nbsp;<b>${c.close}</b>
        </span>`;
      allLineSeries.forEach(({ ls, label, color }) => {
        const v = param.seriesData && param.seriesData.get(ls);
        html += `<span class="legend-item">
          <span class="legend-swatch" style="background:${color}"></span>
          ${escapeHtml(label)}${v ? '&nbsp;<b>' + v.value.toFixed(5) + '</b>' : ''}
          </span>`;
      });
    } else {
      html = legendMeta.map(m =>
        `<span class="legend-item">
          <span class="legend-swatch" style="background:${m.color}"></span>
          ${escapeHtml(m.label)}</span>`
      ).join('');
      if (!html) html = '<span style="color:var(--muted)">Move cursor over chart to inspect values</span>';
    }
    legendEl.innerHTML = html;
  }

  chart.subscribeCrosshairMove(setLegend);
  setLegend(null);
  chart.timeScale().fitContent();
}

// Poll /api/scheduler/status every 30 s to show next scheduled refresh
function updateNextRefresh() {
  fetch('/api/scheduler/status')
    .then(r => r.json())
    .then(d => {
      const el = document.getElementById('next-refresh');
      el.textContent = d.next_run ? 'Next fetch: ' + d.next_run : '';
    })
    .catch(() => {});
}
updateNextRefresh();
setInterval(updateNextRefresh, 30000);

// Init
loadPortfolio();
</script>
</body>
</html>
"""


# ---- Routes ----------------------------------------------------------------

@app.route('/')
def index():
    return render_template_string(_TEMPLATE)


@app.route('/api/portfolio')
def api_portfolio():
    if _portfolio is None:
        return jsonify({'error': 'Portfolio not loaded'})

    engines = []
    for eng_name, eng in _portfolio.tEngines.items():
        fx = eng.instrument
        sig_gens = []
        for sg_name, sg in eng.sigGens.items():
            sig_gens.append({
                'name':    sg.signalName,
                'nMA6':    sg.nMA6,
                'nMA6_1':  sg.nMA6_1,
                'signal':  getattr(sg, 'signal',  0),
                'fast_ma': getattr(sg, 'fast_ma', None),
                'slow_ma': getattr(sg, 'slow_ma', None),
            })
        fx_data = {
            'cross_name': fx.crossName if fx else '',
            'base_ccy':   fx.BaseCcy   if fx else '',
            'quote_ccy':  fx.QuoteCcy  if fx else '',
            'scalar':     fx.Scalar    if fx else 0,
            'bar_count':  len(fx.prices) if fx else 0,
            'last_price': fx.printLastPrice() if (fx and fx.prices) else '',
        }
        engines.append({
            'name': eng.engineName,
            'instrument': fx_data,
            'signal_generators': sig_gens,
        })

    return jsonify({'name': _portfolio.portfolioName, 'engines': engines})


@app.route('/api/portfolio/print', methods=['POST'])
def api_portfolio_print():
    if _portfolio is None:
        return jsonify({'error': 'No portfolio loaded'})
    _portfolio.printPfo()
    return jsonify({'message': 'Portfolio printed to log'})


@app.route('/api/db/test', methods=['POST'])
def api_db_test():
    _write_log("Testing DB connection...")
    try:
        conn = db.FXDB(_write_log)
        conn.closeConnection()
        conn.openConnection()
        conn.closeConnection()
        _write_log("DB connection test passed")
        return jsonify({'message': 'DB connection test passed'})
    except Exception as e:
        msg = "DB connection test failed: %s" % e
        _write_log(msg, status='E')
        return jsonify({'error': msg})


@app.route('/api/prices/refresh', methods=['POST'])
def api_prices_refresh():
    if _portfolio is None:
        return jsonify({'error': 'Portfolio not loaded'})
    def _do():
        _portfolio.refreshAllPrices()
        _portfolio.refreshAllEntrySignals()
    threading.Thread(target=_do, daemon=True).start()
    return jsonify({'message': 'Price fetch and signal recalculation started'})


@app.route('/api/charts/<engine_name>')
def api_chart(engine_name):
    if _portfolio is None:
        return jsonify({'error': 'Portfolio not loaded'})
    eng = _portfolio.tEngines.get(engine_name)
    if eng is None:
        return jsonify({'error': 'Engine not found: %s' % engine_name})
    fx = eng.instrument
    if fx is None or not fx.prices:
        return jsonify({'error': 'No price data for %s' % engine_name})

    # prices is newest-first; reverse to oldest-first for the chart
    prices = list(reversed(fx.prices))

    candles = []
    for p in prices:
        try:
            dt = datetime.datetime.strptime('%s %s' % (p['Date'], p['Time']),
                                            '%Y-%m-%d %H:%M:%S')
            candles.append({
                'time':  int(dt.timestamp()),
                'open':  float(p['Open']),
                'high':  float(p['High']),
                'low':   float(p['Low']),
                'close': float(p['Close']),
            })
        except (ValueError, KeyError):
            continue

    closes = [c['close'] for c in candles]
    times  = [c['time']  for c in candles]

    # Rolling SMAs for every signal generator attached to this engine
    ma_series = []
    for sg_name, sg in eng.sigGens.items():
        n_fast = int(sg.nMA6)
        n_slow = int(sg.nMA6_1)
        fast_data, slow_data = [], []
        for i in range(len(closes)):
            n = i + 1
            if n >= n_fast:
                fast_data.append({'time': times[i],
                                  'value': round(sum(closes[i+1-n_fast:i+1]) / n_fast, 5)})
            if n >= n_slow:
                slow_data.append({'time': times[i],
                                  'value': round(sum(closes[i+1-n_slow:i+1]) / n_slow, 5)})
        ma_series.append({
            'name':   sg_name,
            'signal': getattr(sg, 'signal', 0),
            'fast':   {'period': n_fast, 'data': fast_data},
            'slow':   {'period': n_slow, 'data': slow_data},
        })

    return jsonify({'cross_name': fx.crossName, 'candles': candles, 'ma_series': ma_series})


@app.route('/api/scheduler/status')
def api_scheduler_status():
    if _next_run_utc:
        return jsonify({'next_run': _next_run_utc.strftime('%H:%M UTC')})
    return jsonify({'next_run': None})


@app.route('/api/log/history')
def api_log_history():
    return jsonify(list(_LOG_HISTORY))


@app.route('/api/log/stream')
def api_log_stream():
    """Server-Sent Events endpoint — pushes new log entries in real time."""
    q = queue.Queue(maxsize=200)
    with _SSE_LOCK:
        _SSE_CLIENTS.append(q)

    def generate():
        try:
            while True:
                try:
                    yield q.get(timeout=25)
                except queue.Empty:
                    yield ': keepalive\n\n'   # prevent proxy timeouts
        finally:
            with _SSE_LOCK:
                try:
                    _SSE_CLIENTS.remove(q)
                except ValueError:
                    pass

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache',
                             'X-Accel-Buffering': 'no'})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def load_portfolio():
    """Load the portfolio then start the hourly price-refresh scheduler."""
    global _portfolio
    try:
        dbconn = db.FXDB(_write_log)
        _write_log("Loading Portfolio...")
        _portfolio = fxPf.FXPortfolio(_write_log, dbconn, _get_portfolio_name())
        # Kick off signal calculation on the data already in HourlyData.csv
        _portfolio.refreshAllEntrySignals()
        # Schedule recurring hourly fetches
        _schedule_next_refresh()
    except Exception as e:
        _write_log("Failed to load portfolio: %s\n%s" % (e, traceback.format_exc()),
                   status='E')


def main():
    global _logfile

    parser = argparse.ArgumentParser(description='FXTS web UI')
    parser.add_argument('--port',       type=int, default=5000)
    parser.add_argument('--host',       default='127.0.0.1')
    parser.add_argument('--no-browser', action='store_true',
                        help='Do not open browser automatically')
    args = parser.parse_args()

    # Open log file
    try:
        _logfile = open(os.path.join(os.path.dirname(__file__), 'FXTS.log'), 'a')
    except Exception as e:
        print("Failed to open logfile: %s" % e)

    _write_log("Starting FXTS web UI on http://%s:%d" % (args.host, args.port))

    # Load portfolio in a background thread so the server starts immediately
    threading.Thread(target=load_portfolio, daemon=True).start()

    # Open browser after a short delay
    if not args.no_browser:
        url = 'http://%s:%d' % (args.host, args.port)
        threading.Timer(1.2, webbrowser.open, args=[url]).start()

    app.run(host=args.host, port=args.port, threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
