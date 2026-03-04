#dbconnector.py - CB database readers and writers
import sys
#import MySQLdb
import MySQLdb.cursors
import datetime as date
import time as tm

##class MySQLCursorDict(MySQLdb.cursor.MySQLCursor):
## 
##  def fetchone(self):
##    row = self._fetch_row()
##    if row:
##      return dict(zip(self.column_names, self._row_to_python(row)))
##    return None


#===============================================================================
# FXDB
#===============================================================================
class FXDB():
    #===========================================================================
    # __init__
    #===========================================================================
    def __init__(self, log):
        self.host = 'localhost'
        self.user = 'matt'
        self.passwd = 'matt'
        self.db = 'FXDB'
        #self.db = 'chapelb1_cb'
        
##        self.host = 'www.chapelbaycapital.com'
##        self.user = 'chapelb1_mluser'
##        self.passwd = 'StAlbans123'
##        self.db = 'chapelb1_cb'

        self.logger = log
       
        try:
            self.conn = MySQLdb.connect (host = self.host,
                                         user = self.user,
                                         passwd = self.passwd,
                                         db = self.db,
                                         cursorclass=MySQLdb.cursors.DictCursor) 
            cursor = self.conn.cursor ()
            cursor.execute ("SELECT VERSION()")
            row = cursor.fetchone ()
            #print row
            self.logger("db Connection established. Server version: %s" %(row['VERSION()']))
            cursor.close ()
        except:
            self.logger("Unable to establish db connection on instantiation: %s" %sys.exc_info()[0])
            self.logger("%s" %sys.exc_info()[1])
            raise

    #===========================================================================
    # closeConnection
    #===========================================================================
    def closeConnection(self):
        try:
            self.conn.close()
            self.logger("db Connection closed")
        except:
            self.logger("Unable to close connection: %s" %sys.exc_info()[0])
            raise
 
    #===========================================================================
    # openConnection
    #===========================================================================
    def openConnection(self):
        try:
            self.conn = MySQLdb.connect (host = self.host,
                                 user = self.user,
                                 passwd = self.passwd,
                                 db = self.db)
            self.logger("db Connection established.")
        except:
            self.logger("Failed to open connection: %s" %sys.exc_info()[0])
            raise

    #===========================================================================
    # loadFXCross
    #===========================================================================
    def loadFXCross(self, crossname):
    
        query = 'Select BaseCcy, QuoteCcy, Scalar, IP from FXCross where FXCross ="%s"' %crossname
        self.logger(query)
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            rows = cursor.fetchone ()
            return rows
        except:
            return     
    #..................................................................................

    #===========================================================================
    # loadFXPrices
    #===========================================================================
    def loadFXPrices(self, crossname, elements):
    
        query = 'SELECT  * FROM HourlyData WHERE ticker="%s" order by Date desc,Time desc limit %s;' %(crossname,elements)
        self.logger(query)
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            rows = cursor.fetchall ()
            return rows
        except:
            return     

    #===========================================================================
    # loadMappedTEngines
    #===========================================================================
    def loadMappedTEngines(self, portfolio):
    
        query = 'Select Id, TEngine, Weight from MAP_Pfo_TEngine where Portfolio ="%s"' %portfolio
        print query
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            rows = cursor.fetchall ()
            return rows
        except:
            return []

    #===========================================================================
    # loadTEngine
    #===========================================================================
    def loadTEngine(self, engine):
    
        query = 'Select Id, TEngine, Instrument from TEngine where TEngine ="%s"' %engine
    
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            rows = cursor.fetchone ()
            return rows
        except:
            return []
    
    #===========================================================================
    # loadMappedSigGens
    #===========================================================================
    def loadMappedSigGens(self, tengine):
    
        query = 'Select Id, SigGen from MAP_TEngine_SigGen where TEngine ="%s"' %tengine
        print query
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            rows = cursor.fetchall ()
            return rows
        except:
            return []

    #===========================================================================
    # loadSigGen
    #===========================================================================
    def loadSigGen(self, siggen, sigtype):
        
        if sigtype == 'TP':
            query = 'Select Id, SigGen, nMA6, nMA6_1 from SigGenTP where SigGen ="%s"' %siggen
        else:
            query = 'Unknown SigGen type %s' %sigtype
    
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            rows = cursor.fetchone ()
            return rows
        except:
            return []
                
    #===========================================================================
    # findLastPriceDate
    #===========================================================================
    def findLastPriceDate(self, mktCode, deliveryCode):
        #if mktCode[-1:] == "_":
            #mktCode = mktCode[:2]
        query = 'Select max(TSDate) from futures_data where Instrument_ID="%s" and NM="%s"'  %(mktCode, deliveryCode)
        #print query
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            row = cursor.fetchone ()
            if row['max(TSDate)'] is None:
                return '19000101'
            else:
                return row['max(TSDate)']
        except:
            return '19000101'
        
    #===========================================================================
    # findPricesForDateRange
    #===========================================================================
    def findPricesForDateRange(self, mktCode, deliveryCode, startDate, endDate):
        #if mktCode[-1:] == "_":
            #mktCode = mktCode[:2]
        query = 'Select TSDate, Instrument_ID, NM, PX_Open, PX_HIGH, PX_LOW, PX_CLOSE from futures_data where Instrument_ID="%s" and NM="%s" and TSDate between "%s" and "%s"'  %(mktCode, deliveryCode, startDate, endDate)
        #print query
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            rows = cursor.fetchall ()
            return rows
        except:
            self.logger("Unable to load price data for %s:%s" %(mktCode, deliveryCode))
            self.logger("%s : %s" %(sys.exc_info()[0], sys.exc_info()[1]))
            raise
   
    #===========================================================================
    # findLastFXDate
    #===========================================================================
    def findLastFXDate(self, mktCode, dateFormat):

        query = 'Select max(TSDate) from fx_data where Instrument="%s"'  %mktCode
        
        returnDateMMDDYYYY = date.datetime.now().replace(month=3,day=1)

        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            row = cursor.fetchone ()
            #print row
            if row['max(TSDate)'] == None:
                pass
            else:
                strDate = str(row['max(TSDate)'])

                returnDateMMDDYYYY = date.datetime(int(strDate[0:4]),int(strDate[4:6]),int(strDate[6:]))
        except:
            self.logger('findLastFXDate() - %s' %sys.exc_info()[0])
            raise
            pass
            
        return returnDateMMDDYYYY

    #===========================================================================
    # findLastStateTFDate
    #===========================================================================
    def findLastStateTFDate(self, mktCode, deliveryCode, engine):
        #if mktCode[-1:] == "_":
            #mktCode = mktCode[:2]
        query = 'Select max(TSDate) from state_tf_futures where Instrument="%s" and NM="%s" and Engine="%s"'  %(mktCode, deliveryCode, engine)
        print query
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            row = cursor.fetchone ()
            if row['max(TSDate)'] is None:
                return '19000101'
            else:
                return row['max(TSDate)']
        except:
            print 'Unable to find last SigTF date, defaulting to 19000101'
            return '19000101'

    #===========================================================================
    # findActiveFXpairs
    #===========================================================================
    def findActiveFXpairs(self):
        query = 'SELECT Instrument,concat(curncy1,curncy2) as "CcyPair" FROM fx_table'
        
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            rows = cursor.fetchall()
            return rows
        except:
            self.logger("No FX pairs defined")
            return 'null'

    #===========================================================================
    # storeFX
    #===========================================================================
    def storeFX(self, instr, rows):
        sqlHead = 'Insert into fx_data (Instrument, TSDate, PX_OPEN, PX_HIGH, PX_LOW, PX_CLOSE) values '
        sqlMain = sqlHead
        for r in rows:
            rdate = tm.strptime(r['Date'], "%m/%d/%Y")
            sqlPiece = '("%s", %s, %s, %s, %s, %s),' %(instr,tm.strftime("%Y%m%d", rdate),r['First'],r['High'],r['Low'],r['Last'])
            sqlMain = sqlMain + sqlPiece
        
        sqlMain = sqlMain[:-1]

        try:
            cursor = self.conn.cursor ()
            cursor.execute (sqlMain)
            retrow = cursor.fetchone ()
        except:
            self.logger('unable to save data: %s' %sys.exc_info()[0])
            raise

    #===========================================================================
    # loadTFState
    #===========================================================================
    def loadTFState(self, mkt, nm, signal, lastDate):
        #print mkt, nm, signal,lastDate
        query = 'SELECT Instrument, Engine, TSDate, NM, FM, PX_OPEN, PX_HIGH, PX_LOW, PX_CLOSE, FM_Close, ATR, `20EMA(ATR)`, EMAFast, EMASlow, Buffer, Sig from state_tf_futures where Instrument="%s" and NM="%s" and Engine="%s" and TSDate="%s"' %(mkt, nm, signal,lastDate)
        print query
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            rows = cursor.fetchone()
            return rows
        except:
            self.logger("No existing TF signals found")
            return 'null'


    #===========================================================================
    # storeTFState
    #===========================================================================
    def storeTFState(self, rows):
        sqlHead = 'Insert into state_tf_futures (Instrument, Engine, TSDate, NM, FM, PX_OPEN, PX_HIGH, PX_LOW, PX_CLOSE, FM_CLOSE, ATR, `20EMA(ATR)`, EMAFast, EMASlow, Buffer, Sig) values '
        sqlMain = sqlHead
        for r in rows:
            sqlPiece = '("%s", %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s),' \
                       %(r['Instrument'], r['Engine'], r['TSDate'], r['NM'], r['FM'], \
                         r['PX_OPEN'], r['PX_HIGH'], r['PX_LOW'], r['PX_CLOSE'], r['FM_CLOSE'], \
                         r['ATR'], r['20EMA(ATR)'], r['EMAFast'], r['EMASlow'], r['Buffer'], r['Sig'])
            sqlMain = sqlMain + sqlPiece
        
        sqlMain = sqlMain[:-1]

        try:
            cursor = self.conn.cursor ()
            cursor.execute (sqlMain)
            retrow = cursor.fetchone ()
        except:
            self.logger('unable to save data: %s' %sys.exc_info()[0])
            raise

    #===========================================================================
    # loadTFEngines
    #===========================================================================
    def loadTFEngines(self):
        query = 'SELECT Engine, Slow, Fast, Buffer from tf_engines'
        
        try:
            cursor = self.conn.cursor ()
            cursor.execute (query)
            rows = cursor.fetchall()
            return rows
        except:
            self.logger("No existing TF engines config found")
            return 'null'

