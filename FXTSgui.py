#!/usr/bin/python3
# FXTSgui.py - Main GUI application

import sys
import os
import configparser
import time as tm
import traceback

from PyQt5 import QtCore
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QGridLayout,
    QTextEdit, QAction, QMessageBox,
)
from PyQt5.QtGui import QIcon

import DBConnector as db
import FXPortfolio as fxPf


def _get_portfolio_name():
    cfg = configparser.ConfigParser()
    cfg_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    cfg.read(cfg_path)
    return os.environ.get('FXTS_PORTFOLIO', cfg.get('portfolio', 'name', fallback='FX Portfolio 1'))


#===============================================================================
# MainWindow
#===============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.resize(550, 850)
        self.setWindowTitle('FXTS')

        centreWidget = QWidget()
        self.setCentralWidget(centreWidget)

        grid = QGridLayout()
        centreWidget.setLayout(grid)

        self.textEdit = QTextEdit()
        self.textLog = QTextEdit()
        grid.addWidget(self.textEdit, 0, 0)
        grid.addWidget(self.textLog, 1, 0)

        # Actions
        exitm = QAction(QIcon('icons/exit.png'), 'Exit', self)
        exitm.setShortcut('Ctrl+Q')
        exitm.setStatusTip('Exit application')
        exitm.triggered.connect(self.close)

        printPfo = QAction(QIcon('icons/exit.png'), 'Print Pfo', self)
        printPfo.setShortcut('Ctrl+F')
        printPfo.setStatusTip('Print Portfolio details')
        printPfo.triggered.connect(self.printPfoFull)

        testdb = QAction(QIcon('icons/exit.png'), 'TestDB', self)
        testdb.setShortcut('Ctrl+T')
        testdb.setStatusTip('Test DB Connection')
        testdb.triggered.connect(self.testDB)

        menubar = self.menuBar()
        mfile = menubar.addMenu('&File')
        mfile.addAction(exitm)
        mprint = menubar.addMenu('&Print')
        mprint.addAction(printPfo)

        # Open log file
        try:
            self.logfile = open('./FXTS.log', 'a')
        except Exception as e:
            print("Failed to open logfile: %s" % e)
            self.logfile = None

        self.logger('Starting...')

        # Initialise portfolio — show an error dialog on failure rather than crashing
        self.portfolio = None
        try:
            dbconnection = db.FXDB(self.logger)
            self.logger('Loading Portfolio...')
            self.portfolio = fxPf.FXPortfolio(self.logger, dbconnection, _get_portfolio_name())
        except Exception as e:
            msg = "Failed to initialise portfolio:\n%s\n\n%s" % (e, traceback.format_exc())
            self.logger(msg, status='E')
            QMessageBox.critical(self, "Startup Error", msg)

    #===========================================================================
    # logger
    #===========================================================================
    def logger(self, message, status='I'):
        timelog = tm.strftime('%Y%m%d.%H%M%S', tm.gmtime())
        msg = "%s :-%-1s-%s\n" % (timelog, status, message)
        print(msg.rstrip())
        self.textLog.insertPlainText(msg)
        sb = self.textLog.verticalScrollBar()
        sb.setValue(sb.maximum())
        app.processEvents()
        if self.logfile:
            try:
                self.logfile.write(msg)
                self.logfile.flush()
            except Exception as e:
                print("Log write failed: %s" % e)

    #===========================================================================
    # printPfoFull
    #===========================================================================
    def printPfoFull(self):
        if self.portfolio is None:
            self.logger("No portfolio loaded", status='W')
            return
        self.portfolio.printPfo()

    #===========================================================================
    # testDB
    #===========================================================================
    def testDB(self):
        self.logger("Testing DB connection...")
        try:
            dbconnection = db.FXDB(self.logger)
            dbconnection.closeConnection()
            dbconnection.openConnection()
            dbconnection.closeConnection()
            self.logger("DB connection test passed")
        except Exception as e:
            self.logger("DB connection test failed: %s\n%s" % (e, traceback.format_exc()), status='E')

    #===========================================================================
    # getFX
    #===========================================================================
    def getFX(self):
        return getattr(self, 'fxList', [])


# ##########################################

app = QApplication(sys.argv)
main = MainWindow()
main.show()
sys.exit(app.exec_())
