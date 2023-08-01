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

class mesoSPIM_CameraWindow(QtWidgets.QWidget):
    sig_update_roi = QtCore.pyqtSignal(tuple)
    sig_update_status = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        self.parent = parent # the mesoSPIM_MainWindow() instance
        self.cfg = parent.cfg
        self.state = mesoSPIM_StateSingleton()

        self.cuvettePlusButton.pressed.connect(lambda: self.move_relative({'c_rel': -self.cuvetteIncrementSpinbox.value()}))
        self.cuvetteMinusButton.pressed.connect(lambda: self.move_relative({'c_rel': self.cuvetteIncrementSpinbox.value()}))

    def move_relative(self, pos_dict):
        self.parent.move_relative(self, pos_dict)

    