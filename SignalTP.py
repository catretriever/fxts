#SignalTP.py - TP Signal Generator Class 

#import sys

#===============================================================================
# TEngine
#===============================================================================
class SignalTP():
    #===========================================================================
    # __init__
    #===========================================================================
    def __init__(self, log, dbconn,name):
        self.logger=log
        self.conn = dbconn
        self.signalName = name
        self.nMA6 = 0
        self.nMA6_1 = 0
        
        self.logger("Loading SignalTP: %s" %(self.signalName))
        
        try:
            signalDetails = self.conn.loadSigGen(self.signalName, 'TP')
            self.nMA6 = signalDetails['nMA6']
            self.nMA6_1 = signalDetails['nMA6_1']
            print  signalDetails['nMA6']
            print signalDetails['nMA6_1']
        except:
            self.logger("Failed to load details for SignalTP: %s" %(self.signalName))
                               

    #===========================================================================
    # printEngine
    #===========================================================================
    def printSignal(self):
        self.logger('SignalName: %s, nMA6: %s, nMA6_1: %s' %(self.signalName, self.nMA6, self.nMA6_1))
        

    #===========================================================================
    # refreshAllSignals
    #===========================================================================
    def refreshSignal(self):
        pass
        
    #.......................................................................................................................


