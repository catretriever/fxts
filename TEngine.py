#TEngine.py - Trading SYstem Class - where a Trading Engine is a combination of a market and 1-n Sig Generators

#import sys
import FXCross
import SignalTP

#===============================================================================
# TEngine
#===============================================================================
class TEngine():
    #===========================================================================
    # __init__
    #===========================================================================
    def __init__(self, log, dbconn,name):
        self.logger=log
        self.conn = dbconn
        self.engineName = name
        self.instrument = ''
        self.sigGens = dict()
        
        self.logger("Loading TEngine: %s" %(self.engineName))
        
        try:
            engineDetails = self.conn.loadTEngine(self.engineName)
            self.instrument = FXCross.FXCross(self.logger, self.conn,engineDetails['Instrument'])
            siggenmap = self.conn.loadMappedSigGens(self.engineName)
            self.logger('Found %s signal generators for TEngine: %s' %(len(siggenmap), self.engineName))
            for siggen in siggenmap:
                self.sigGens[siggen['SigGen']] = SignalTP.SignalTP(self.logger, self.conn, siggen['SigGen'])
        except:
            self.logger("Failed to load details for TEngine: %s" %(self.engineName))                               

    #===========================================================================
    # printEngine
    #===========================================================================
    def printEngine(self):
        self.logger('EngineName: %s, Instrument: %s' %(self.engineName,self.instrument.crossName))
        self.logger(self.instrument.printLastPrice())
        for siggen in self.sigGens: 
            self.sigGens[siggen].printSignal()

    #===========================================================================
    # refreshAllSignals
    #===========================================================================
    def refreshAllSignals(self):
        pass
        
    #.......................................................................................................................

