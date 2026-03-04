#FXPortfolio.py - FX Portfolio Class

#import sys
import TEngine as te

# ##### FXPortfolio ###############################
class FXPortfolio():
    # init #.......................................................................................................................
    def __init__(self, log, dbconn,name):
        self.logger=log
        self.conn = dbconn
        self.portfolioName = name
        self.logger("Loading Portfolio: [%s]" %(self.portfolioName))
        self.tEngines = dict()
        
        try:
        #if 1==1:    # fetch list of engines
            self.logger('calling loadMapped TEngines')
            engineMap = self.conn.loadMappedTEngines(self.portfolioName)
            self.logger('Found %s TEngines in Portfolio : %s'%(len(engineMap), self.portfolioName))
            # Initialise engine object for each engine in the list
            for engine in engineMap:
                self.logger('Mapped Engine found: %s' %engine['TEngine'])
                self.tEngines[engine['TEngine']] = te.TEngine(self.logger,self.conn,engine['TEngine'])

        #self.engines = nothing
        except:
            self.logger("Failed to load TSystems for Portfolio: [%s]" %(self.portfolioName))
            
        self.logger("Finished Portfolio: [%s]" %(self.portfolioName))
        
                               
    #.......................................................................................................................

    # refreshAllPrices #.......................................................................................................................
    def printPfo(self):
        self.logger('Pfo Name: %s' %self.portfolioName)
        for engine in self.tEngines:
            self.tEngines[engine].printEngine()
            
        
    #.......................................................................................................................
    
    
    # refreshAllPrices #.......................................................................................................................
    def refreshAllPrices(self):
        pass
        
    #.......................................................................................................................

    # refreshAllEntrySignals #.......................................................................................................................
    def refreshAllEntrySignals(self):
        pass
        
    #.......................................................................................................................

    # refreshAllExitSignals #.......................................................................................................................
    def refreshAllExitSignals(self):
        pass
        
    #.......................................................................................................................

    # processPositions #.......................................................................................................................
    def processPositions(self):
        pass
        
    #.......................................................................................................................

