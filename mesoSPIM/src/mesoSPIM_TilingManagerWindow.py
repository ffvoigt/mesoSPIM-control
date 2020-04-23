'''
mesoSPIM TilingManagerWindow 

Displays an overview of 
'''

import sys
import numpy as np

import logging
logger = logging.getLogger(__name__)

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.uic import loadUi

import pyqtgraph as pg

from .mesoSPIM_State import mesoSPIM_StateSingleton

class mesoSPIM_TilingManagerWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super.__init__()

        self.parent = parent
        self.cfg = parent.cfg

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
            loadUi('../gui/mesoSPIM_TilingManagerWindow.ui', self)
        else:
            loadUi('gui/mesoSPIM_TilingManagerWindow.ui', self)
        self.setWindowTitle('mesoSPIM-Control: Tiling Manager')

        self.grid = pg.GridItem()

        self.graphicsLayoutWidget.addItem(self.grid)

    