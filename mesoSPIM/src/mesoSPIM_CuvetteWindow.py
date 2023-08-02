'''
mesoSPIM Cuvette Window
'''
import sys
import numpy as np
import logging
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.uic import loadUi
from .mesoSPIM_State import mesoSPIM_StateSingleton

logger = logging.getLogger(__name__)

class mesoSPIM_CuvetteWindow(QtWidgets.QWidget):
    sig_update_roi = QtCore.pyqtSignal(tuple)
    sig_update_status = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent # the mesoSPIM_MainWindow() instance
        self.cfg = parent.cfg
        self.state = mesoSPIM_StateSingleton()

        loadUi('gui/mesoSPIM_CuvetteWindow.ui', self)
        self.setWindowTitle('mesoSPIM-Optimizer')
        self.show()

        self.cuvettePlusButton.pressed.connect(lambda: self.move_relative({'c_rel': -self.cuvetteIncrementSpinbox.value()}))
        self.cuvetteMinusButton.pressed.connect(lambda: self.move_relative({'c_rel': self.cuvetteIncrementSpinbox.value()}))
        self.cuvetteSaveButton.pressed.connect(self.save_current_cuvette_position)

    def move_relative(self, pos_dict):
        self.parent.move_relative(pos_dict)

    def pos2str(self, position):
        """ Little helper method for converting positions to strings """
        return '%.1f' % position

    @QtCore.pyqtSlot(dict)
    def update_position_indicators(self, dict):
        for key, pos_dict in dict.items():
            if key == 'position':
                if pos_dict['c_pos']:
                    self.c_position = pos_dict['c_pos']
                    self.Cuvette_Position_Indicator.setText(self.pos2str(self.c_position)+' µm')

    def save_current_cuvette_position(self):
        current_zoom = self.state['zoom']
        current_cuvette_position = self.state['position']['c_pos']

        self.state['extra_info']['zoom_cuvette_dict'][current_zoom] = current_cuvette_position
        logger.info('Extra info in mesoSPIM_State for zoom: '+ current_zoom + 
                    ' updated to ' + str(current_cuvette_position) + ' um')
                    

        

    