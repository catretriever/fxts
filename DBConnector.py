# DBConnector.py - Database readers and writers
# Database: text files (CSV) in the data/ directory
import sys
import os
import csv
import configparser
import traceback
import datetime as date
import time as tm


def _load_config():
    """Load DB config from config.ini, with environment variable overrides."""
    cfg = configparser.ConfigParser()
    cfg_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    cfg.read(cfg_path)
    default_data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    return {
        'data_dir': os.environ.get('FXDB_DATA_DIR',
                                   cfg.get('database', 'data_dir', fallback=default_data_dir)),
    }


#===============================================================================
# FXDB
#===============================================================================
class FXDB():
    #===========================================================================
    # __init__
    #===========================================================================
    def __init__(self, log):
        self.logger = log
        self._cfg = _load_config()
        self._data_dir = self._cfg['data_dir']
        self._connect()

    def _connect(self):
        if not os.path.isdir(self._data_dir):
            raise FileNotFoundError("Data directory not found: %s" % self._data_dir)
        self.logger("File-based DB ready. Data directory: %s" % self._data_dir)

    def _table_path(self, name):
        return os.path.join(self._data_dir, name + '.csv')

    def _read(self, table):
        path = self._table_path(table)
        try:
            with open(path, newline='', encoding='utf-8') as f:
                return list(csv.DictReader(f))
        except FileNotFoundError:
            return []

    def _append(self, table, rows, fieldnames):
        path = self._table_path(table)
        exists = os.path.isfile(path)
        next_id = len(self._read(table)) + 1
        with open(path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['Id'] + fieldnames)
            if not exists:
                writer.writeheader()
            for i, row in enumerate(rows):
                out = {'Id': next_id + i}
                out.update({k: row.get(k, '') for k in fieldnames})
                writer.writerow(out)

    #===========================================================================
    # closeConnection
    #===========================================================================
    def closeConnection(self):
        self.logger("File-based DB closed")

    #===========================================================================
    # openConnection
    #===========================================================================
    def openConnection(self):
        self._connect()

    #===========================================================================
    # loadFXCross
    #===========================================================================
    def loadFXCross(self, crossname):
        query = "FXCross.csv WHERE FXCross = %s"
        self.logger(query % crossname)
        for r in self._read('FXCross'):
            if r.get('FXCross') == crossname:
                return r
        return None

    #===========================================================================
    # loadFXPrices
    #===========================================================================
    def loadFXPrices(self, crossname, elements):
        query = "HourlyData.csv WHERE ticker = %s ORDER BY Date DESC, Time DESC LIMIT %s"
        self.logger(query % (crossname, elements))
        rows = [r for r in self._read('HourlyData') if r.get('ticker') == crossname]
        rows.sort(key=lambda r: (r.get('Date', ''), r.get('Time', '')), reverse=True)
        return rows[:int(elements)]

    #===========================================================================
    # loadMappedTEngines
    #===========================================================================
    def loadMappedTEngines(self, portfolio):
        query = "MAP_Pfo_TEngine.csv WHERE Portfolio = %s"
        self.logger(query % portfolio)
        return [r for r in self._read('MAP_Pfo_TEngine') if r.get('Portfolio') == portfolio]

    #===========================================================================
    # loadTEngine
    #===========================================================================
    def loadTEngine(self, engine):
        for r in self._read('TEngine'):
            if r.get('TEngine') == engine:
                return r
        return None

    #===========================================================================
    # loadMappedSigGens
    #===========================================================================
    def loadMappedSigGens(self, tengine):
        query = "MAP_TEngine_SigGen.csv WHERE TEngine = %s"
        self.logger(query % tengine)
        return [r for r in self._read('MAP_TEngine_SigGen') if r.get('TEngine') == tengine]

    #===========================================================================
    # loadSigGen
    #===========================================================================
    def loadSigGen(self, siggen, sigtype):
        if sigtype == 'TP':
            table = 'SigGenTP'
        else:
            raise ValueError("Unknown SigGen type: %s" % sigtype)
        for r in self._read(table):
            if r.get('SigGen') == siggen:
                return r
        return None

    #===========================================================================
    # findLastPriceDate
    #===========================================================================
    def findLastPriceDate(self, mktCode, deliveryCode):
        dates = [
            r['TSDate'] for r in self._read('futures_data')
            if r.get('Instrument_ID') == mktCode and r.get('NM') == deliveryCode and r.get('TSDate')
        ]
        return max(dates) if dates else '19000101'

    #===========================================================================
    # findPricesForDateRange
    #===========================================================================
    def findPricesForDateRange(self, mktCode, deliveryCode, startDate, endDate):
        return [
            r for r in self._read('futures_data')
            if r.get('Instrument_ID') == mktCode
            and r.get('NM') == deliveryCode
            and startDate <= r.get('TSDate', '') <= endDate
        ]

    #===========================================================================
    # findLastFXDate
    #===========================================================================
    def findLastFXDate(self, mktCode, dateFormat):
        fallback = date.datetime.now().replace(month=3, day=1)
        dates = [
            r['TSDate'] for r in self._read('fx_data')
            if r.get('Instrument') == mktCode and r.get('TSDate')
        ]
        if not dates:
            return fallback
        strDate = max(dates)
        return date.datetime(int(strDate[0:4]), int(strDate[4:6]), int(strDate[6:]))

    #===========================================================================
    # findLastStateTFDate
    #===========================================================================
    def findLastStateTFDate(self, mktCode, deliveryCode, engine):
        dates = [
            r['TSDate'] for r in self._read('state_tf_futures')
            if r.get('Instrument') == mktCode
            and r.get('NM') == deliveryCode
            and r.get('Engine') == engine
            and r.get('TSDate')
        ]
        return max(dates) if dates else '19000101'

    #===========================================================================
    # findActiveFXpairs
    #===========================================================================
    def findActiveFXpairs(self):
        result = []
        for r in self._read('fx_table'):
            row = dict(r)
            row['CcyPair'] = row.get('curncy1', '') + row.get('curncy2', '')
            result.append(row)
        return result

    #===========================================================================
    # storeFX
    #===========================================================================
    def storeFX(self, instr, rows):
        fieldnames = ['Instrument', 'TSDate', 'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_CLOSE']
        try:
            records = []
            for r in rows:
                rdate = tm.strptime(r['Date'], "%m/%d/%Y")
                records.append({
                    'Instrument': instr,
                    'TSDate':     tm.strftime("%Y%m%d", rdate),
                    'PX_OPEN':   r['First'],
                    'PX_HIGH':   r['High'],
                    'PX_LOW':    r['Low'],
                    'PX_CLOSE':  r['Last'],
                })
            self._append('fx_data', records, fieldnames)
        except Exception as e:
            self.logger("storeFX failed: %s\n%s" % (e, traceback.format_exc()))
            raise

    #===========================================================================
    # loadTFState
    #===========================================================================
    def loadTFState(self, mkt, nm, signal, lastDate):
        for r in self._read('state_tf_futures'):
            if (r.get('Instrument') == mkt and r.get('NM') == nm
                    and r.get('Engine') == signal and r.get('TSDate') == str(lastDate)):
                return r
        return None

    #===========================================================================
    # storeTFState
    #===========================================================================
    def storeTFState(self, rows):
        fieldnames = [
            'Instrument', 'Engine', 'TSDate', 'NM', 'FM',
            'PX_OPEN', 'PX_HIGH', 'PX_LOW', 'PX_CLOSE', 'FM_CLOSE',
            'ATR', '20EMA(ATR)', 'EMAFast', 'EMASlow', 'Buffer', 'Sig',
        ]
        try:
            self._append('state_tf_futures', rows, fieldnames)
        except Exception as e:
            self.logger("storeTFState failed: %s\n%s" % (e, traceback.format_exc()))
            raise

    #===========================================================================
    # loadLastHourlyTimestamp
    #===========================================================================
    def loadLastHourlyTimestamp(self, ticker):
        """Return the latest bar datetime (UTC-naive) for ticker, or None."""
        import datetime as _dt
        rows = [r for r in self._read('HourlyData') if r.get('ticker') == ticker]
        if not rows:
            return None
        latest = max(rows, key=lambda r: (r.get('Date', ''), r.get('Time', '')))
        try:
            return _dt.datetime.strptime(
                '%s %s' % (latest['Date'], latest['Time']), '%Y-%m-%d %H:%M:%S')
        except Exception:
            return None

    #===========================================================================
    # storeHourlyBars
    #===========================================================================
    def storeHourlyBars(self, ticker, bars):
        """Append a list of OHLC bar dicts to HourlyData.csv for the given ticker.

        Each bar dict must contain: Date, Time, Open, High, Low, Close.
        """
        fieldnames = ['ticker', 'Date', 'Time', 'Open', 'High', 'Low', 'Close']
        records = [{'ticker': ticker, **bar} for bar in bars]
        self._append('HourlyData', records, fieldnames)

    #===========================================================================
    # loadTFEngines
    #===========================================================================
    def loadTFEngines(self):
        return self._read('tf_engines')
