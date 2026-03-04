# SignalTP.py - TP Signal Generator Class
import traceback


class SignalTP():
    def __init__(self, log, dbconn, name):
        self.logger = log
        self.conn = dbconn
        self.signalName = name
        self.nMA6 = 0
        self.nMA6_1 = 0
        # Signal state — populated by refreshSignal()
        self.signal   = 0      # +1 = long, -1 = short, 0 = flat/insufficient data
        self.fast_ma  = None   # SMA(nMA6)   of recent closes
        self.slow_ma  = None   # SMA(nMA6_1) of recent closes

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
        label = {1: 'LONG', -1: 'SHORT', 0: 'FLAT'}.get(self.signal, '?')
        self.logger("SignalName: %s, nMA6: %s, nMA6_1: %s, signal: %s"
                    % (self.signalName, self.nMA6, self.nMA6_1, label))

    def refreshSignal(self, prices):
        """Calculate a dual simple-MA crossover signal.

        Args:
            prices: list of OHLC dicts newest-first, as returned by
                    DBConnector.loadFXPrices().  Each dict must have 'Close'.

        Sets self.signal (+1=long, -1=short, 0=flat), self.fast_ma, self.slow_ma.
        Returns a dict with those three values.
        """
        n_fast = int(self.nMA6)
        n_slow = int(self.nMA6_1)

        if not prices or len(prices) < n_slow:
            self.signal, self.fast_ma, self.slow_ma = 0, None, None
            return {'signal': 0, 'fast_ma': None, 'slow_ma': None}

        # prices[0] is the most recent bar; take the n_slow most-recent closes
        closes = [float(r['Close']) for r in prices[:n_slow]]

        fast_ma = sum(closes[:n_fast]) / n_fast
        slow_ma = sum(closes)          / n_slow

        if fast_ma > slow_ma:
            sig = 1
        elif fast_ma < slow_ma:
            sig = -1
        else:
            sig = 0

        self.signal  = sig
        self.fast_ma = round(fast_ma, 5)
        self.slow_ma = round(slow_ma, 5)

        return {'signal': sig, 'fast_ma': self.fast_ma, 'slow_ma': self.slow_ma}
