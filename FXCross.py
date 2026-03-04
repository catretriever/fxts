# FXCross.py - FX Cross Rate Instrument
import configparser
import os
import traceback
import numpy as np


def _get_price_elements():
    cfg = configparser.ConfigParser()
    cfg_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    cfg.read(cfg_path)
    return int(os.environ.get('FXTS_PRICE_ELEMENTS', cfg.get('fxcross', 'price_elements', fallback='2000')))


class FXCross():
    def __init__(self, log, dbconn, crossname):
        self.logger = log
        self.conn = dbconn
        self.crossName = crossname
        self.BaseCcy = ''
        self.QuoteCcy = ''
        self.Scalar = None
        self.IP = ''
        self.prices = []

        self.logger("Initialising FXCross: %s" % self.crossName)

        try:
            instrumentDetails = self.conn.loadFXCross(self.crossName)
            if instrumentDetails is None:
                raise ValueError("No DB record found for FXCross: %s" % self.crossName)

            self.BaseCcy = instrumentDetails['BaseCcy']
            self.QuoteCcy = instrumentDetails['QuoteCcy']
            self.Scalar = instrumentDetails['Scalar']
            self.IP = instrumentDetails['IP']

            self.reloadPrices(_get_price_elements())
            self.logger("Loaded %s price elements for %s" % (len(self.prices), self.crossName))
        except Exception as e:
            self.logger("Failed to initialise FXCross [%s]: %s\n%s" % (self.crossName, e, traceback.format_exc()))

    def getHighestHigh(self, numElements):
        if not self.prices:
            self.logger("getHighestHigh: no price data for %s" % self.crossName)
            return None
        highs = [row['High'] for row in self.prices[:numElements]]
        return max(highs)

    def getLowestLow(self, numElements):
        if not self.prices:
            self.logger("getLowestLow: no price data for %s" % self.crossName)
            return None
        lows = [row['Low'] for row in self.prices[:numElements]]
        return min(lows)

    def getLastTimestamp(self):
        if not self.prices:
            return None
        last = self.prices[-1]
        return "%s %s" % (last['Date'], last['Time'])

    def getPricesForPeriod(self, numElements):
        return self.prices[:numElements]

    def appendPrice(self, timestamp, O, H, L, C):
        pass

    def insertPrice(self, timestamp, O, H, L, C):
        pass

    def refresh(self):
        """Re-fetch prices from the data store using the configured element count."""
        self.reloadPrices(_get_price_elements())

    def reloadPrices(self, dataPeriod):
        self.logger("Reloading prices for: %s" % self.crossName)
        try:
            tmpPrices = self.conn.loadFXPrices(self.crossName, dataPeriod)
            self.prices = tmpPrices
        except Exception as e:
            self.logger("Failed to reload prices for [%s]: %s\n%s" % (self.crossName, e, traceback.format_exc()))

    def printLastPrice(self):
        if not self.prices:
            return "No price data available for %s" % self.crossName
        last = self.prices[-1]
        return "Latest Price, %s: %s %s O[%s], H[%s], L[%s], C[%s]" % (
            self.crossName, last['Date'], last['Time'],
            last['Open'], last['High'], last['Low'], last['Close'],
        )
