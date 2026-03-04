#FXCross.py - FX Cross Rate Instrument

#import sys
import numpy as np
#===============================================================================
# FXCross
#===============================================================================
class FXCross():
    #===========================================================================
    # __init__
    #===========================================================================
    def __init__(self, log, dbconn,crossname):
        self.logger=log
        self.conn = dbconn
        self.crossName = crossname
        self.BaseCcy = ''
        self.QuoteCcy = ''
        self.prices = []
        self.IP = ''
        
        self.logger("Initialising FXCross: %s" %self.crossName)
        
        try:
            instrumentDetails = self.conn.loadFXCross(self.crossName)
            
            self.BaseCcy = instrumentDetails['BaseCcy']
            self.QuoteCcy = instrumentDetails['QuoteCcy']
            self.prices = []
            self.Scalar = instrumentDetails['Scalar']
            self.IP = instrumentDetails['IP']

            self.reloadPrices(2000)
            self.logger('Loaded %s price Elements for %s' %(len(self.prices), self.crossName))
        #self.engines = nothing
        except:
            self.logger("Failed to initialise Instrument: %s%s" %(self.BaseCcy,self.QuoteCcy))
    
    #===========================================================================
    # getHighestHigh
    #===========================================================================
    def getHighestHigh(self, numElements):
        c1, c2, c3, c4, c5, c6, c7 = zip(self.prices)
        
        npprices = np.asarray(c4)
        candidate = npprices[5]
        print candidate
        
    #===========================================================================
    # getLowestLow
    #===========================================================================
    def getLowestLow(self, numElements):
        pass
        
    #===========================================================================
    # getLastTimestamp
    #===========================================================================
    def getLastTimestamp(self):
        pass
        
    #===========================================================================
    # getPricesForPeriod
    #===========================================================================
    def getPricesForPeriod(self, numElements):
        pass
        
    #===========================================================================
    # appendPrice
    #===========================================================================
    def appendPrice(self,timestamp, O,H,L,C):
        pass
        
    #===========================================================================
    # insertPrice
    #===========================================================================
    def insertPrice(self, timestamp, O,H,L,C):
        pass

    #===========================================================================
    # reloadPrices
    #===========================================================================
    def reloadPrices(self, dataPeriod):
        self.logger("Attempting to reload all prices for: %s%s" %(self.BaseCcy,self.QuoteCcy))

        try:
            tmpPrices = []
            tmpPrices = self.conn.loadFXPrices(self.crossName, dataPeriod)
            
            self.prices = tmpPrices
            
#            num_rows = len(tmpPrices)
#            
#            x = map(list,list(tmpPrices))
#            x = sum(x, [])
#            
#            D = np.fromiter(iterable=x, dtype=float, count=-1)
#            D = D.reshape(num_rows, -1)
#            
#            self.prices = D
        except:
            self.logger("Failed to re-load prices for: %s%s" %(self.BaseCcy,self.QuoteCcy))
        
    #===========================================================================
    # printLastPrice
    #===========================================================================
    def printLastPrice(self):
        lastPrice = self.prices[len(self.prices)-1] # remember arrays are base 0
        outstr = 'Latest Price, %s: %s %s O[%s], H[%s], L[%s], C[%s]' %(self.crossName, lastPrice['Date'],lastPrice['Time'],lastPrice['Open'],lastPrice['High'],lastPrice['Low'],lastPrice['Close'])
        return outstr
    