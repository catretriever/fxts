#!/usr/bin/python
# mainwindow.py 

import sys
import time as tm
#import datetime as date
from PyQt4 import QtGui, QtCore
import DBConnector as db
import FXPortfolio as fxPf

#===============================================================================
# MainWindow: This is the main application, a simple GUI front end for the loading
#             and controlling the other Class Objects
#             FXPortfolio -> TEngine -> FXCross
#                                    -> SigGen
# 
#===============================================================================
class MainWindow(QtGui.QMainWindow):
    # init #.......................................................................................................................
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        #=======================================================================
        # SETUP THE MAIN GUI WINDOW ELEMENTS
        #Set up the Main Window with a grid for positioning widgets appropriately
        #self.resize(350, 250)
        self.resize(550, 850)
        self.setWindowTitle('FXTS')
        
        centreWidget = QtGui.QWidget()
        self.setCentralWidget(centreWidget)
        
        grid = QtGui.QGridLayout()
        centreWidget.setLayout(grid)
        
        # Set up widgets that will form the main subdivision of the window, and upper object display area, and a lower logging window
        self.textEdit = QtGui.QTextEdit()
        self.textLog =QtGui.QTextEdit()

        grid.addWidget(self.textEdit,0,0)
        grid.addWidget(self.textLog,1,0)

        # Set up menu and toolbars, first defining the actions, then attaching the actions to a menu button
        exitm = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Exit', self)
        exitm.setShortcut('Ctrl+Q')
        exitm.setStatusTip('Exit application')
        self.connect(exitm, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))

        view = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'View', self)
        view.setShortcut('Ctrl+W')
        view.setStatusTip('View Something')
        self.connect(view, QtCore.SIGNAL('triggered()'), QtCore.SLOT('close()'))
        
        #loadFX = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Load FX', self)
        #loadFX.setShortcut('Ctrl+F')
        #loadFX.setStatusTip('Load the FX daily data')
        #self.connect(loadFX, QtCore.SIGNAL('triggered()'), self.loadAllFX)

        printPfo = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Print Pfo', self)
        printPfo.setShortcut('Ctrl+F')
        printPfo.setStatusTip('Print Portfolio details')
        self.connect(printPfo, QtCore.SIGNAL('triggered()'), self.printPfoFull)

        
        testdb = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'TestDB', self)
        testdb.setShortcut('Ctrl+T')
        testdb.setStatusTip('Test DB Connection')
        self.connect(testdb, QtCore.SIGNAL('triggered()'), self.testDB)
        
        #run = QtGui.QAction(QtGui.QIcon('icons/exit.png'), 'Run TF', self)
        #run.setShortcut('Ctrl+R')
        #run.setStatusTip('Generate HOURLY signals for any new data')
        #self.connect(run, QtCore.SIGNAL('triggered()'), self.runTFSignals)

        #self.statusBar()
        menubar = self.menuBar()
        mfile = menubar.addMenu('&File')
        mfile.addAction(exitm)
        #mview = menubar.addMenu('&View')
        #mview.addAction(view)
        #mload = menubar.addMenu('&Load')
        #mload.addAction(loadFX)        
        #mload.addAction(testdb)
        mprint = menubar.addMenu('&Print')
        mprint.addAction(printPfo)        
        #mrun = menubar.addMenu('&Run')
        #mrun.addAction(run)

        #toolbar = self.addToolBar('Exit')
        #toolbar.addAction(exit)
        
        #=======================================================================
        # NOW THE GUI IS SET UP, START GETTING ON WITH LOADING THE PORTFOLIO(S)
        
        # Set up a log file
        try:
            print "opening log file"
            self.logfile  = open('./FXTS.log', "ab")        
        except:
            print "failed to open logfile"
            print "%s : %s" %(sys.exc_info()[0], sys.exc_info()[1])
            self.logfile = ''
            pass
        
        self.logger('Starting...')
        
        # Initialise Portfolio Data in memory, instantiating the portfolio object
        # will trigger the initialision of the TEngine object mapped to the portfolio
        # which in turn will trigger the initialisation of the FXCross and SigGen 
        # objects that are mapped to each TEngine, in a cascading fashion.
        #
        # Objects within the portfolio may then be accessed in the manner..
        #     Portfolio.TEngine['GBPJPY'].SigGen['MAV1'].entryLevel
        # ..which is not dissimilar to the way objects are accessed in VBA
        #
        dbconnection = db.FXDB(self.logger)      
        self.logger('Loading Portfolio...')
        self.portfolio = fxPf.FXPortfolio(self.logger,dbconnection,'FX Portfolio 1')
        #self.logger('Loading FX Crosses')
        #self.fxList = dbconnection.findActiveFXpairs()
        #self.logger('Loading FX Crosses...done')
        

    #===========================================================================
    # logger ; This is the generic logging function used throughout the app
    #          All classes are initialised with a reference to thsi function
    #          which will write log messages to both the GUI window and the log
    #          file
    #===========================================================================
    def logger(self,message, status='I'):
        timelog = tm.strftime('%Y%m%d.%H%M%S', tm.gmtime())
        msg = timelog + ' :-' + status + '-' + message + '\n'
        if 1==1: ##debug mode
            print msg[:-1]
        self.textLog.insertPlainText(msg)
        sb = self.textLog.verticalScrollBar()
        sb.setValue(sb.maximum())
        app.processEvents()
        try:
            self.logfile.write(msg)
            self.logfile.flush()
        except:
            print "%s : %s" %(sys.exc_info()[0], sys.exc_info()[1])

    #===========================================================================
    # printPfoFull:
    #        A simple utility to print the details of the portfolio and it's
    #        components to the log. Useful to debug the loading process.
    #===========================================================================
    def printPfoFull(self):
        self.portfolio.printPfo()

    #============================================================================
    # testDB
    #        A utility function to check database connections
    #============================================================================
    def testDB(self):
        print "instatiating dbconnection object"
        dbconnection = db.FXDB(self.logger)
        print "attempting to close db connection"
        dbconnection.closeConnection()
        print "attempting to open db connection"
        dbconnection.openConnection()
        print "attempting to open db connection second time"
        dbconnection.openConnection()
        print "attempting to close db connection"
        dbconnection.closeConnection()

    #===========================================================================
    # getFX
    #===========================================================================
    def getFX(self):
        return self.fxList
    #........................................................................................................................................
           
     
 

# ##########################################

app = QtGui.QApplication(sys.argv)
main = MainWindow()

main.show()
sys.exit(app.exec_())