'''
mesoSPIM Plotting Window
===================================

Allows simple plots of data
'''

import time
import numpy as np

import logging
logger = logging.getLogger(__name__)

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.uic import loadUi

''' mesoSPIM imports '''
from .mesoSPIM_State import mesoSPIM_StateSingleton

import pyqtgraph as pg

class mesoSPIM_PlottingWindow(QtWidgets.QWidget):

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent
        self.cfg = parent.cfg
        self.state = mesoSPIM_StateSingleton()
        ''' Change the PyQtGraph-Options in White Mode'''
        pg.setConfigOptions(imageAxisOrder='row-major')
        if self.cfg.dark_mode == False:
            pg.setConfigOptions(foreground='k')
            pg.setConfigOptions(background='w')
        else:
            '''Set background to #19232D'''
            background_color = pg.mkColor('#19232D')
            pg.setConfigOptions(background=background_color)
            pg.setConfigOptions(foreground='w')
            '''Set up the UI'''
        if __name__ == '__main__':
            loadUi('../gui/mesoSPIM_PlottingWindow.ui', self)
        else:
            loadUi('gui/mesoSPIM_PlottingWindow.ui', self)
        self.setWindowTitle('mesoSPIM-Control: Plotting Window')
        self.plot = self.graphicsLayoutWidget.addPlot()
        self.curve = self.plot.plot()
        self.plot.showGrid(True,True)
        self.data = []
        self.count = 0

        ''' Slightly hacky way to get an item display in the plot menu'''
        printAct = QtGui.QAction("Reset plot", self.plot.ctrlMenu)
        printAct.triggered.connect(self.reset_plot)
        self.plot.ctrlMenu.addAction(printAct)
        self.plot.ctrlMenu.printAct = printAct
        
    
    @QtCore.pyqtSlot()
    def generate_random_plot(self):
        self.data.append(np.random.normal(size=1) + np.sin(self.count * 0.1) * 5)
        if len(self.data) > 100:
            self.data.pop(0)
        self.curve.setData(np.hstack(self.data))
        self.count += 1

    #@QtCore.pyqtSlot(dict)
    def update_plot(self, autofocus_dict):
        #print(autofocus_dict)
        #print(type(autofocus_dict))
        #print(autofocus_dict['dcts_result'])
        #print(type(autofocus_dict['dcts_result']))
        #print(self.data)

        self.data.append(autofocus_dict['dcts_result'])

        if len(self.data) > 100:
            self.data.pop(0)

        self.curve.setData(np.hstack(self.data))
        #self.count += 1

    def reset_plot(self):
        self.data = []
        self.count = 0
        self.curve.clear()
    
    