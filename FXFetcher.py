# FXFetcher.py - Hourly FX OHLC data fetcher
# Source: Yahoo Finance public chart API (no API key required)
# Requires: requests  (pip install requests — already a Flask dependency)

import datetime
import traceback

try:
    import requests as _req
except ImportError:
    _req = None

# ---------------------------------------------------------------------------
# Yahoo Finance symbol mapping (internal name → Yahoo Finance ticker)
# Add pairs here as needed; unknown crosses fall back to NAME=X
# ---------------------------------------------------------------------------
_YF_SYMBOLS = {
    'AUDUSD': 'AUDUSD=X',
    'EURCAD': 'EURCAD=X',
    'EURGBP': 'EURGBP=X',
    'EURJPY': 'EURJPY=X',
    'EURUSD': 'EURUSD=X',
    'GBPAUD': 'GBPAUD=X',
    'GBPCAD': 'GBPCAD=X',
    'GBPJPY': 'GBPJPY=X',
    'GBPUSD': 'GBPUSD=X',
    'NZDUSD': 'NZDUSD=X',
    'USDCAD': 'USDCAD=X',
    'USDCHF': 'USDCHF=X',
    'USDJPY': 'USDJPY=X',
}

_YF_CHART_URL = 'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
_HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; FXTS/1.0)'}
_TIMEOUT = 15  # seconds


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_hourly(crossname, since_dt=None, log=None):
    """Fetch hourly OHLC bars for an FX cross from Yahoo Finance.

    Args:
        crossname: Internal cross name, e.g. 'GBPJPY'
        since_dt:  datetime (UTC, timezone-naive).  Only bars strictly after
                   this timestamp are returned.  None → last 7 days.
        log:       Optional callable(msg) for error/info reporting.

    Returns:
        List of dicts sorted oldest-first, ready to append to HourlyData.csv:
          [{'Date': 'YYYY-MM-DD', 'Time': 'HH:MM:SS',
            'Open': '1.23456', 'High': '…', 'Low': '…', 'Close': '…'}, …]
        Returns [] on any error.
    """
    if _req is None:
        _emit(log, "FXFetcher: 'requests' package not installed")
        return []

    symbol = _YF_SYMBOLS.get(crossname.upper(), crossname.upper() + '=X')
    url = _YF_CHART_URL.format(symbol=symbol)

    # Use period1/period2 for incremental fetches, range= for initial seed
    if since_dt is not None:
        params = {
            'interval': '1h',
            'period1':  int(since_dt.timestamp()),
            'period2':  int(datetime.datetime.utcnow().timestamp()),
        }
    else:
        params = {'interval': '1h', 'range': '7d'}

    try:
        resp = _req.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as exc:
        _emit(log, "FXFetcher: HTTP request failed for %s: %s" % (crossname, exc))
        return []

    try:
        result = payload['chart']['result']
        if not result:
            _emit(log, "FXFetcher: empty result for %s" % crossname)
            return []
        block  = result[0]
        stamps = block.get('timestamp') or []
        quote  = block['indicators']['quote'][0]
        opens  = quote.get('open',  [])
        highs  = quote.get('high',  [])
        lows   = quote.get('low',   [])
        closes = quote.get('close', [])
    except (KeyError, IndexError, TypeError) as exc:
        _emit(log, "FXFetcher: unexpected response format for %s: %s" % (crossname, exc))
        return []

    bars = []
    for i, ts in enumerate(stamps):
        if ts is None:
            continue
        try:
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        except IndexError:
            continue
        if None in (o, h, l, c):
            continue  # incomplete bar — skip
        dt = datetime.datetime.utcfromtimestamp(ts)
        if since_dt is not None and dt <= since_dt:
            continue
        bars.append({
            'Date':  dt.strftime('%Y-%m-%d'),
            'Time':  dt.strftime('%H:%M:%S'),
            'Open':  '%.5f' % o,
            'High':  '%.5f' % h,
            'Low':   '%.5f' % l,
            'Close': '%.5f' % c,
        })

    bars.sort(key=lambda r: (r['Date'], r['Time']))

    if bars:
        _emit(log, "FXFetcher: %d new bar(s) for %s (latest: %s %s)"
              % (len(bars), crossname, bars[-1]['Date'], bars[-1]['Time']))
    else:
        _emit(log, "FXFetcher: no new bars for %s" % crossname)

    return bars


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _emit(log, msg):
    if log:
        log(msg)
