# TEngine.py - Trading Engine Class
# A Trading Engine combines one market instrument with 1-n signal generators.
import traceback
import FXCross
import SignalTP


class TEngine():
    def __init__(self, log, dbconn, name):
        self.logger = log
        self.conn = dbconn
        self.engineName = name
        self.instrument = None
        self.sigGens = dict()

        self.logger("Loading TEngine: %s" % self.engineName)

        try:
            engineDetails = self.conn.loadTEngine(self.engineName)
            if engineDetails is None:
                raise ValueError("No DB record found for TEngine: %s" % self.engineName)

            self.instrument = FXCross.FXCross(self.logger, self.conn, engineDetails['Instrument'])

            siggenmap = self.conn.loadMappedSigGens(self.engineName)
            self.logger("Found %s signal generators for TEngine: %s" % (len(siggenmap), self.engineName))
            for siggen in siggenmap:
                self.sigGens[siggen['SigGen']] = SignalTP.SignalTP(self.logger, self.conn, siggen['SigGen'])
        except Exception as e:
            self.logger("Failed to load TEngine [%s]: %s\n%s" % (self.engineName, e, traceback.format_exc()))

    def printEngine(self):
        if self.instrument is None:
            self.logger("TEngine [%s] has no instrument loaded" % self.engineName)
            return
        self.logger("EngineName: %s, Instrument: %s" % (self.engineName, self.instrument.crossName))
        self.logger(self.instrument.printLastPrice())
        for siggen in self.sigGens:
            self.sigGens[siggen].printSignal()

    def refreshAllSignals(self):
        pass
