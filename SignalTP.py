# SignalTP.py - TP Signal Generator Class
import traceback


class SignalTP():
    def __init__(self, log, dbconn, name):
        self.logger = log
        self.conn = dbconn
        self.signalName = name
        self.nMA6 = 0
        self.nMA6_1 = 0

        self.logger("Loading SignalTP: %s" % self.signalName)

        try:
            signalDetails = self.conn.loadSigGen(self.signalName, 'TP')
            if signalDetails is None:
                raise ValueError("No DB record found for SignalTP: %s" % self.signalName)
            self.nMA6 = signalDetails['nMA6']
            self.nMA6_1 = signalDetails['nMA6_1']
        except Exception as e:
            self.logger("Failed to load SignalTP [%s]: %s\n%s" % (self.signalName, e, traceback.format_exc()))

    def printSignal(self):
        self.logger("SignalName: %s, nMA6: %s, nMA6_1: %s" % (self.signalName, self.nMA6, self.nMA6_1))

    def refreshSignal(self):
        pass
