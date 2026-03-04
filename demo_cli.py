#!/usr/bin/env python3
"""
demo_cli.py - FXTS headless demo

Bootstraps an in-memory SQLite database with the same schema and sample
data as setup_test_db.sql, then exercises the full FXTS object hierarchy
(FXPortfolio → TEngine → FXCross / SignalTP) and prints a portfolio
summary to stdout.

No MySQL server or display is required.

Usage:
  python3 demo_cli.py
"""

import os
import sqlite3
import sys
import time as tm

# ---------------------------------------------------------------------------
# Minimal SQLite-backed DB connector (mirrors the FXDB API surface)
# ---------------------------------------------------------------------------

class SQLiteDB:
    """Drop-in replacement for DBConnector.FXDB that uses an in-memory SQLite DB."""

    # SQLite schema (mirrors setup_test_db.sql without MySQL-specific syntax)
    _SCHEMA = """
    CREATE TABLE FXCross (
        Id       INTEGER PRIMARY KEY AUTOINCREMENT,
        FXCross  TEXT NOT NULL UNIQUE,
        BaseCcy  TEXT NOT NULL,
        QuoteCcy TEXT NOT NULL,
        Scalar   REAL NOT NULL DEFAULT 1.0,
        IP       TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE HourlyData (
        Id     INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT NOT NULL,
        Date   TEXT NOT NULL,
        Time   TEXT NOT NULL,
        Open   REAL NOT NULL,
        High   REAL NOT NULL,
        Low    REAL NOT NULL,
        Close  REAL NOT NULL
    );
    CREATE TABLE TEngine (
        Id         INTEGER PRIMARY KEY AUTOINCREMENT,
        TEngine    TEXT NOT NULL UNIQUE,
        Instrument TEXT NOT NULL
    );
    CREATE TABLE MAP_Pfo_TEngine (
        Id        INTEGER PRIMARY KEY AUTOINCREMENT,
        Portfolio TEXT NOT NULL,
        TEngine   TEXT NOT NULL,
        Weight    REAL NOT NULL DEFAULT 1.0
    );
    CREATE TABLE MAP_TEngine_SigGen (
        Id      INTEGER PRIMARY KEY AUTOINCREMENT,
        TEngine TEXT NOT NULL,
        SigGen  TEXT NOT NULL
    );
    CREATE TABLE SigGenTP (
        Id     INTEGER PRIMARY KEY AUTOINCREMENT,
        SigGen TEXT NOT NULL UNIQUE,
        nMA6   INTEGER NOT NULL DEFAULT 6,
        nMA6_1 INTEGER NOT NULL DEFAULT 7
    );
    CREATE TABLE fx_table (
        Id         INTEGER PRIMARY KEY AUTOINCREMENT,
        Instrument TEXT NOT NULL UNIQUE,
        curncy1    TEXT NOT NULL,
        curncy2    TEXT NOT NULL
    );
    CREATE TABLE fx_data (
        Id         INTEGER PRIMARY KEY AUTOINCREMENT,
        Instrument TEXT NOT NULL,
        TSDate     TEXT NOT NULL,
        PX_OPEN    REAL,
        PX_HIGH    REAL,
        PX_LOW     REAL,
        PX_CLOSE   REAL
    );
    CREATE TABLE futures_data (
        Id            INTEGER PRIMARY KEY AUTOINCREMENT,
        TSDate        TEXT NOT NULL,
        Instrument_ID TEXT NOT NULL,
        NM            TEXT NOT NULL,
        PX_Open       REAL,
        PX_HIGH       REAL,
        PX_LOW        REAL,
        PX_CLOSE      REAL
    );
    CREATE TABLE tf_engines (
        Id     INTEGER PRIMARY KEY AUTOINCREMENT,
        Engine TEXT NOT NULL UNIQUE,
        Slow   INTEGER NOT NULL,
        Fast   INTEGER NOT NULL,
        Buffer REAL NOT NULL DEFAULT 0.0
    );
    CREATE TABLE state_tf_futures (
        Id          INTEGER PRIMARY KEY AUTOINCREMENT,
        Instrument  TEXT NOT NULL,
        Engine      TEXT NOT NULL,
        TSDate      TEXT NOT NULL,
        NM          TEXT NOT NULL,
        FM          TEXT NOT NULL DEFAULT '',
        PX_OPEN     REAL, PX_HIGH REAL, PX_LOW REAL, PX_CLOSE REAL,
        FM_CLOSE    REAL, ATR REAL, EMA20ATR REAL,
        EMAFast     REAL, EMASlow REAL, Buffer REAL, Sig INTEGER DEFAULT 0
    );
    """

    # Sample data (identical to setup_test_db.sql)
    _DATA = [
        ("INSERT INTO FXCross (FXCross,BaseCcy,QuoteCcy,Scalar,IP) VALUES (?,?,?,?,?)", [
            ('GBPJPY','GBP','JPY',100.0,'192.168.1.1'),
            ('EURUSD','EUR','USD',  1.0,'192.168.1.2'),
            ('USDJPY','USD','JPY',100.0,'192.168.1.3'),
            ('GBPUSD','GBP','USD',  1.0,'192.168.1.4'),
            ('AUDUSD','AUD','USD',  1.0,'192.168.1.5'),
        ]),
        ("INSERT INTO HourlyData (ticker,Date,Time,Open,High,Low,Close) VALUES (?,?,?,?,?,?,?)", [
            ('GBPJPY','2026-03-04','14:00:00',190.250,190.510,190.100,190.420),
            ('GBPJPY','2026-03-04','13:00:00',190.030,190.310,189.900,190.250),
            ('GBPJPY','2026-03-04','12:00:00',189.780,190.100,189.650,190.030),
            ('GBPJPY','2026-03-04','11:00:00',189.500,189.850,189.400,189.780),
            ('GBPJPY','2026-03-04','10:00:00',189.200,189.600,189.050,189.500),
            ('GBPJPY','2026-03-04','09:00:00',188.900,189.300,188.750,189.200),
            ('GBPJPY','2026-03-04','08:00:00',188.600,189.000,188.450,188.900),
            ('GBPJPY','2026-03-04','07:00:00',188.300,188.700,188.150,188.600),
            ('GBPJPY','2026-03-04','06:00:00',188.000,188.400,187.900,188.300),
            ('GBPJPY','2026-03-04','05:00:00',187.750,188.100,187.650,188.000),
            ('EURUSD','2026-03-04','14:00:00',1.08520,1.08650,1.08440,1.08600),
            ('EURUSD','2026-03-04','13:00:00',1.08380,1.08550,1.08320,1.08520),
            ('EURUSD','2026-03-04','12:00:00',1.08200,1.08420,1.08150,1.08380),
            ('EURUSD','2026-03-04','11:00:00',1.08050,1.08260,1.07980,1.08200),
            ('EURUSD','2026-03-04','10:00:00',1.07900,1.08100,1.07830,1.08050),
        ]),
        ("INSERT INTO TEngine (TEngine,Instrument) VALUES (?,?)", [
            ('GBPJPYeng01','GBPJPY'),
            ('EURUSDeng01','EURUSD'),
        ]),
        ("INSERT INTO MAP_Pfo_TEngine (Portfolio,TEngine,Weight) VALUES (?,?,?)", [
            ('FX Portfolio 1','GBPJPYeng01',0.6),
            ('FX Portfolio 1','EURUSDeng01',0.4),
        ]),
        ("INSERT INTO MAP_TEngine_SigGen (TEngine,SigGen) VALUES (?,?)", [
            ('GBPJPYeng01','GBPJPY_TP_6_7'),
            ('GBPJPYeng01','GBPJPY_TP_12_13'),
            ('EURUSDeng01','EURUSD_TP_6_7'),
        ]),
        ("INSERT INTO SigGenTP (SigGen,nMA6,nMA6_1) VALUES (?,?,?)", [
            ('GBPJPY_TP_6_7',   6,  7),
            ('GBPJPY_TP_12_13',12, 13),
            ('EURUSD_TP_6_7',   6,  7),
        ]),
        ("INSERT INTO fx_table (Instrument,curncy1,curncy2) VALUES (?,?,?)", [
            ('GBPJPY Curncy','GBP','JPY'),
            ('EURUSD Curncy','EUR','USD'),
            ('USDJPY Curncy','USD','JPY'),
        ]),
        ("INSERT INTO fx_data (Instrument,TSDate,PX_OPEN,PX_HIGH,PX_LOW,PX_CLOSE) VALUES (?,?,?,?,?,?)", [
            ('GBPJPY Curncy','20260304',188.000,190.510,187.650,190.420),
            ('GBPJPY Curncy','20260303',187.200,188.500,186.900,188.000),
            ('GBPJPY Curncy','20260228',186.500,187.800,186.100,187.200),
        ]),
        ("INSERT INTO tf_engines (Engine,Slow,Fast,Buffer) VALUES (?,?,?,?)", [
            ('TF_GBPJPY_32_8', 32, 8, 0.002),
            ('TF_GBPJPY_64_16',64,16, 0.003),
            ('TF_EURUSD_32_8', 32, 8, 0.001),
        ]),
    ]

    def __init__(self, log):
        self.logger = log
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self._load_schema()
        log("SQLite in-memory database ready")

    # -- Schema loading -------------------------------------------------------

    def _load_schema(self):
        cur = self.conn.cursor()
        for stmt in self._SCHEMA.split(';'):
            stmt = stmt.strip()
            if stmt:
                cur.execute(stmt)
        for sql, rows in self._DATA:
            cur.executemany(sql, rows)
        self.conn.commit()

    # -- API methods (match DBConnector.FXDB) --------------------------------

    def _q(self, sql, params=()):
        """Execute a query and return all rows as dicts."""
        cur = self.conn.cursor()
        # Convert MySQL %s to SQLite ?
        sql = sql.replace('%s', '?')
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def _q1(self, sql, params=()):
        rows = self._q(sql, params)
        return rows[0] if rows else None

    def closeConnection(self):
        pass  # in-memory DB; nothing to close for demo

    def openConnection(self):
        pass

    def loadFXCross(self, crossname):
        return self._q1(
            "SELECT BaseCcy, QuoteCcy, Scalar, IP FROM FXCross WHERE FXCross = %s",
            (crossname,))

    def loadFXPrices(self, crossname, elements):
        return self._q(
            "SELECT * FROM HourlyData WHERE ticker = %s "
            "ORDER BY Date DESC, Time DESC LIMIT %s",
            (crossname, elements))

    def loadMappedTEngines(self, portfolio):
        return self._q(
            "SELECT Id, TEngine, Weight FROM MAP_Pfo_TEngine WHERE Portfolio = %s",
            (portfolio,))

    def loadTEngine(self, engine):
        return self._q1(
            "SELECT Id, TEngine, Instrument FROM TEngine WHERE TEngine = %s",
            (engine,))

    def loadMappedSigGens(self, tengine):
        return self._q(
            "SELECT Id, SigGen FROM MAP_TEngine_SigGen WHERE TEngine = %s",
            (tengine,))

    def loadSigGen(self, siggen, sigtype):
        if sigtype != 'TP':
            raise ValueError("Unknown SigGen type: %s" % sigtype)
        return self._q1(
            "SELECT Id, SigGen, nMA6, nMA6_1 FROM SigGenTP WHERE SigGen = %s",
            (siggen,))

    def findActiveFXpairs(self):
        return self._q(
            "SELECT Instrument, curncy1 || curncy2 AS CcyPair FROM fx_table")

    def loadTFEngines(self):
        return self._q("SELECT Engine, Slow, Fast, Buffer FROM tf_engines")

    def findLastFXDate(self, mktCode, dateFormat=None):
        import datetime
        row = self._q1(
            "SELECT MAX(TSDate) AS max_date FROM fx_data WHERE Instrument = %s",
            (mktCode,))
        if row is None or row['max_date'] is None:
            return datetime.datetime.now().replace(month=3, day=1)
        s = str(row['max_date'])
        return datetime.datetime(int(s[0:4]), int(s[4:6]), int(s[6:]))


# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

def make_logger(prefix=''):
    def log(message, status='I'):
        ts = tm.strftime('%Y%m%d.%H%M%S', tm.gmtime())
        print(f"{ts} :-{status}-{prefix}{message}")
    return log


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def run_demo():
    log = make_logger()
    log("=" * 60)
    log("FXTS CLI Demo — powered by SQLite in-memory test DB")
    log("=" * 60)

    # Wire up the SQLite DB
    db = SQLiteDB(log)

    # Monkey-patch DBConnector so FXPortfolio / TEngine / etc. use our SQLite DB
    import DBConnector
    _orig_init = DBConnector.FXDB.__init__

    def _patched_init(self, logger):
        self.logger = logger
        self._cfg = {}
        self.conn = None
        # Delegate all method calls to our SQLiteDB instance
        for name in dir(db):
            if not name.startswith('_'):
                setattr(self, name, getattr(db, name))
        logger("DB connection established (SQLite in-memory test database)")

    DBConnector.FXDB.__init__ = _patched_init

    # Now load portfolio through the real application classes
    import FXPortfolio

    portfolio_name = os.environ.get('FXTS_PORTFOLIO', 'FX Portfolio 1')
    log(f"Loading portfolio: {portfolio_name}")

    dbconn = DBConnector.FXDB(log)
    portfolio = FXPortfolio.FXPortfolio(log, dbconn, portfolio_name)

    # Print full portfolio
    log("")
    log("--- Portfolio Summary ---")
    portfolio.printPfo()

    # Extra: show active FX pairs and TF engines from the DB
    log("")
    log("--- Active FX Pairs ---")
    for pair in db.findActiveFXpairs():
        log(f"  {pair['Instrument']:20s}  ({pair['CcyPair']})")

    log("")
    log("--- Trend-Following Engine Parameters ---")
    for eng in db.loadTFEngines():
        log(f"  {eng['Engine']:25s}  slow={eng['Slow']:3d}  fast={eng['Fast']:3d}  "
            f"buffer={eng['Buffer']:.4f}")

    log("")
    log("Demo complete.")


if __name__ == '__main__':
    run_demo()
