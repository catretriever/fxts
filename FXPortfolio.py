# FXPortfolio.py - FX Portfolio Class
import traceback
import TEngine as te
import FXFetcher


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
        """Fetch latest hourly bars from Yahoo Finance and reload in-memory prices.

        For each TEngine instrument:
          1. Look up the latest timestamp already stored in HourlyData.csv.
          2. Ask FXFetcher for any bars newer than that timestamp.
          3. Append new bars to HourlyData.csv via DBConnector.
          4. Reload the instrument's in-memory price list.
        """
        seen = set()   # avoid double-fetching the same cross
        for eng_name, eng in self.tEngines.items():
            fx = eng.instrument
            if fx is None or fx.crossName in seen:
                continue
            seen.add(fx.crossName)
            try:
                since_dt = self.conn.loadLastHourlyTimestamp(fx.crossName)
                new_bars  = FXFetcher.fetch_hourly(fx.crossName,
                                                   since_dt=since_dt,
                                                   log=self.logger)
                if new_bars:
                    self.conn.storeHourlyBars(fx.crossName, new_bars)
                    self.logger("Stored %d new bar(s) for %s" % (len(new_bars), fx.crossName))
                fx.refresh()
                self.logger("Prices reloaded for %s (%d bars)" % (fx.crossName, len(fx.prices)))
            except Exception as e:
                self.logger("refreshAllPrices failed for %s: %s\n%s"
                            % (fx.crossName, e, traceback.format_exc()), 'E')

    def refreshAllEntrySignals(self):
        """Recalculate all entry signals across all TEngines."""
        for eng_name, eng in self.tEngines.items():
            eng.refreshAllSignals()

    def refreshAllExitSignals(self):
        pass

    def processPositions(self):
        pass
