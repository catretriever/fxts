# DBConnector.py - Database readers and writers
# Database: MariaDB 10.6+  (PyMySQL driver — wire-compatible with MariaDB)
import sys
import os
import configparser
import traceback
import datetime as date
import time as tm

import pymysql
import pymysql.cursors


def _load_config():
    """Load DB config from config.ini, with environment variable overrides."""
    cfg = configparser.ConfigParser()
    cfg_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    cfg.read(cfg_path)
    return {
        'host':   os.environ.get('FXDB_HOST',   cfg.get('database', 'host',   fallback='localhost')),
        'user':   os.environ.get('FXDB_USER',   cfg.get('database', 'user',   fallback='fxts')),
        'passwd': os.environ.get('FXDB_PASSWD', cfg.get('database', 'passwd', fallback='')),
        'db':     os.environ.get('FXDB_NAME',   cfg.get('database', 'db',     fallback='FXDB')),
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
        self.conn = self._connect()

    def _connect(self):
        """Open a new connection and return it."""
        conn = pymysql.connect(
            host=self._cfg['host'],
            user=self._cfg['user'],
            passwd=self._cfg['passwd'],
            db=self._cfg['db'],
            cursorclass=pymysql.cursors.DictCursor,
        )
        with conn.cursor() as cursor:
            cursor.execute("SELECT VERSION()")
            row = cursor.fetchone()
            self.logger("DB connection established. Server version: %s" % row['VERSION()'])
        return conn

    #===========================================================================
    # closeConnection
    #===========================================================================
    def closeConnection(self):
        try:
            self.conn.close()
            self.logger("DB connection closed")
        except Exception as e:
            self.logger("Unable to close connection: %s" % e)
            raise

    #===========================================================================
    # openConnection
    #===========================================================================
    def openConnection(self):
        try:
            self.conn = self._connect()
        except Exception as e:
            self.logger("Failed to open connection: %s" % e)
            raise

    #===========================================================================
    # loadFXCross
    #===========================================================================
    def loadFXCross(self, crossname):
        query = "SELECT BaseCcy, QuoteCcy, Scalar, IP FROM FXCross WHERE FXCross = %s"
        self.logger(query % crossname)
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (crossname,))
                return cursor.fetchone()
        except Exception as e:
            self.logger("loadFXCross failed: %s\n%s" % (e, traceback.format_exc()))
            return None

    #===========================================================================
    # loadFXPrices
    #===========================================================================
    def loadFXPrices(self, crossname, elements):
        query = "SELECT * FROM HourlyData WHERE ticker = %s ORDER BY Date DESC, Time DESC LIMIT %s"
        self.logger(query % (crossname, elements))
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (crossname, elements))
                return cursor.fetchall()
        except Exception as e:
            self.logger("loadFXPrices failed: %s\n%s" % (e, traceback.format_exc()))
            return []

    #===========================================================================
    # loadMappedTEngines
    #===========================================================================
    def loadMappedTEngines(self, portfolio):
        query = "SELECT Id, TEngine, Weight FROM MAP_Pfo_TEngine WHERE Portfolio = %s"
        self.logger(query % portfolio)
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (portfolio,))
                return cursor.fetchall()
        except Exception as e:
            self.logger("loadMappedTEngines failed: %s\n%s" % (e, traceback.format_exc()))
            return []

    #===========================================================================
    # loadTEngine
    #===========================================================================
    def loadTEngine(self, engine):
        query = "SELECT Id, TEngine, Instrument FROM TEngine WHERE TEngine = %s"
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (engine,))
                return cursor.fetchone()
        except Exception as e:
            self.logger("loadTEngine failed: %s\n%s" % (e, traceback.format_exc()))
            return None

    #===========================================================================
    # loadMappedSigGens
    #===========================================================================
    def loadMappedSigGens(self, tengine):
        query = "SELECT Id, SigGen FROM MAP_TEngine_SigGen WHERE TEngine = %s"
        self.logger(query % tengine)
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (tengine,))
                return cursor.fetchall()
        except Exception as e:
            self.logger("loadMappedSigGens failed: %s\n%s" % (e, traceback.format_exc()))
            return []

    #===========================================================================
    # loadSigGen
    #===========================================================================
    def loadSigGen(self, siggen, sigtype):
        if sigtype == 'TP':
            query = "SELECT Id, SigGen, nMA6, nMA6_1 FROM SigGenTP WHERE SigGen = %s"
        else:
            raise ValueError("Unknown SigGen type: %s" % sigtype)

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (siggen,))
                return cursor.fetchone()
        except Exception as e:
            self.logger("loadSigGen failed: %s\n%s" % (e, traceback.format_exc()))
            return None

    #===========================================================================
    # findLastPriceDate
    #===========================================================================
    def findLastPriceDate(self, mktCode, deliveryCode):
        query = "SELECT MAX(TSDate) AS max_date FROM futures_data WHERE Instrument_ID = %s AND NM = %s"
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (mktCode, deliveryCode))
                row = cursor.fetchone()
                if row['max_date'] is None:
                    return '19000101'
                return row['max_date']
        except Exception as e:
            self.logger("findLastPriceDate failed: %s\n%s" % (e, traceback.format_exc()))
            return '19000101'

    #===========================================================================
    # findPricesForDateRange
    #===========================================================================
    def findPricesForDateRange(self, mktCode, deliveryCode, startDate, endDate):
        query = (
            "SELECT TSDate, Instrument_ID, NM, PX_Open, PX_HIGH, PX_LOW, PX_CLOSE "
            "FROM futures_data "
            "WHERE Instrument_ID = %s AND NM = %s AND TSDate BETWEEN %s AND %s"
        )
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (mktCode, deliveryCode, startDate, endDate))
                return cursor.fetchall()
        except Exception as e:
            self.logger("findPricesForDateRange failed for %s:%s: %s\n%s" % (
                mktCode, deliveryCode, e, traceback.format_exc()))
            raise

    #===========================================================================
    # findLastFXDate
    #===========================================================================
    def findLastFXDate(self, mktCode, dateFormat):
        query = "SELECT MAX(TSDate) AS max_date FROM fx_data WHERE Instrument = %s"
        fallback = date.datetime.now().replace(month=3, day=1)
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (mktCode,))
                row = cursor.fetchone()
                if row['max_date'] is None:
                    return fallback
                strDate = str(row['max_date'])
                return date.datetime(int(strDate[0:4]), int(strDate[4:6]), int(strDate[6:]))
        except Exception as e:
            self.logger("findLastFXDate failed: %s\n%s" % (e, traceback.format_exc()))
            raise

    #===========================================================================
    # findLastStateTFDate
    #===========================================================================
    def findLastStateTFDate(self, mktCode, deliveryCode, engine):
        query = (
            "SELECT MAX(TSDate) AS max_date FROM state_tf_futures "
            "WHERE Instrument = %s AND NM = %s AND Engine = %s"
        )
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (mktCode, deliveryCode, engine))
                row = cursor.fetchone()
                if row['max_date'] is None:
                    return '19000101'
                return row['max_date']
        except Exception as e:
            self.logger("findLastStateTFDate failed: %s\n%s" % (e, traceback.format_exc()))
            return '19000101'

    #===========================================================================
    # findActiveFXpairs
    #===========================================================================
    def findActiveFXpairs(self):
        query = "SELECT Instrument, CONCAT(curncy1, curncy2) AS CcyPair FROM fx_table"
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            self.logger("findActiveFXpairs failed: %s\n%s" % (e, traceback.format_exc()))
            return []

    #===========================================================================
    # storeFX
    #===========================================================================
    def storeFX(self, instr, rows):
        sql = (
            "INSERT INTO fx_data (Instrument, TSDate, PX_OPEN, PX_HIGH, PX_LOW, PX_CLOSE) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        try:
            with self.conn.cursor() as cursor:
                for r in rows:
                    rdate = tm.strptime(r['Date'], "%m/%d/%Y")
                    cursor.execute(sql, (
                        instr,
                        tm.strftime("%Y%m%d", rdate),
                        r['First'], r['High'], r['Low'], r['Last'],
                    ))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            self.logger("storeFX failed: %s\n%s" % (e, traceback.format_exc()))
            raise

    #===========================================================================
    # loadTFState
    #===========================================================================
    def loadTFState(self, mkt, nm, signal, lastDate):
        query = (
            "SELECT Instrument, Engine, TSDate, NM, FM, PX_OPEN, PX_HIGH, PX_LOW, PX_CLOSE, "
            "FM_Close, ATR, `20EMA(ATR)`, EMAFast, EMASlow, Buffer, Sig "
            "FROM state_tf_futures "
            "WHERE Instrument = %s AND NM = %s AND Engine = %s AND TSDate = %s"
        )
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (mkt, nm, signal, lastDate))
                return cursor.fetchone()
        except Exception as e:
            self.logger("loadTFState failed: %s\n%s" % (e, traceback.format_exc()))
            return None

    #===========================================================================
    # storeTFState
    #===========================================================================
    def storeTFState(self, rows):
        sql = (
            "INSERT INTO state_tf_futures "
            "(Instrument, Engine, TSDate, NM, FM, PX_OPEN, PX_HIGH, PX_LOW, PX_CLOSE, "
            "FM_CLOSE, ATR, `20EMA(ATR)`, EMAFast, EMASlow, Buffer, Sig) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        )
        try:
            with self.conn.cursor() as cursor:
                for r in rows:
                    cursor.execute(sql, (
                        r['Instrument'], r['Engine'], r['TSDate'], r['NM'], r['FM'],
                        r['PX_OPEN'], r['PX_HIGH'], r['PX_LOW'], r['PX_CLOSE'], r['FM_CLOSE'],
                        r['ATR'], r['20EMA(ATR)'], r['EMAFast'], r['EMASlow'], r['Buffer'], r['Sig'],
                    ))
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            self.logger("storeTFState failed: %s\n%s" % (e, traceback.format_exc()))
            raise

    #===========================================================================
    # loadTFEngines
    #===========================================================================
    def loadTFEngines(self):
        query = "SELECT Engine, Slow, Fast, Buffer FROM tf_engines"
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            self.logger("loadTFEngines failed: %s\n%s" % (e, traceback.format_exc()))
            return []
