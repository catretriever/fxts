# FXPortfolio.py - FX Portfolio Class
import traceback
import TEngine as te


class FXPortfolio():
    def __init__(self, log, dbconn, name):
        self.logger = log
        self.conn = dbconn
        self.portfolioName = name
        self.tEngines = dict()

        self.logger("Loading Portfolio: [%s]" % self.portfolioName)

        try:
            self.logger("Fetching mapped TEngines")
            engineMap = self.conn.loadMappedTEngines(self.portfolioName)
            self.logger("Found %s TEngines in Portfolio: %s" % (len(engineMap), self.portfolioName))
            for engine in engineMap:
                self.logger("Mapped Engine found: %s" % engine['TEngine'])
                self.tEngines[engine['TEngine']] = te.TEngine(self.logger, self.conn, engine['TEngine'])
        except Exception as e:
            self.logger("Failed to load TEngines for Portfolio [%s]: %s\n%s" % (
                self.portfolioName, e, traceback.format_exc()))

        self.logger("Finished loading Portfolio: [%s]" % self.portfolioName)

    def printPfo(self):
        self.logger("Pfo Name: %s" % self.portfolioName)
        for engine in self.tEngines:
            self.tEngines[engine].printEngine()

    def refreshAllPrices(self):
        pass

    def refreshAllEntrySignals(self):
        pass

    def refreshAllExitSignals(self):
        pass

    def processPositions(self):
        pass
