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
        super().__init__()

        self.parent = parent
        self.cfg = parent.cfg

        self.state = mesoSPIM_StateSingleton()
        self.state.sig_updated.connect(self.update)

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

        self.viewBox = self.graphicsLayoutWidget.addViewBox()
        self.viewBox.setRange(xRange=[-10000,10000], yRange=[-10000,10000])
        
        self.grid = pg.GridItem()
        self.viewBox.addItem(self.grid)

        self.old_x_pos = 0
        self.old_y_pos = 0

        self.old_zoom = self.state['zoom']
        self.zoom = self.state['zoom']

        self.pixelsize = self.state['pixelsize']
        self.x_pixels = self.cfg.camera_parameters['x_pixels']
        self.y_pixels = self.cfg.camera_parameters['y_pixels']

        self.update_fov(self.pixelsize)
        
        self.currentFOV = CurrentFOV([0,0],[self.x_fov, self.y_fov], pen='r')
        self.viewBox.addItem(self.currentFOV)

    def update(self):
        _position, _pixelsize = self.state.get_parameter_list(['position','pixelsize'])
        self.x_pos = _position['x_pos']
        self.y_pos = _position['y_pos']

        delta_x = self.x_pos - self.old_x_pos
        delta_y = self.y_pos - self.old_y_pos
        delta_pixelsize = _pixelsize - self.pixelsize

        if delta_x != 0:
            self.old_x_pos = self.x_pos
            self.currentFOV.moveBy(delta_x,0)

        if delta_y != 0:
            self.old_y_pos = self.y_pos
            self.currentFOV.moveBy(0,delta_y)

        if delta_pixelsize != 0:
            scaling_factor = _pixelsize/self.pixelsize
            self.update_fov(_pixelsize)
            self.currentFOV.scale([scaling_factor,scaling_factor], center=[0.5,0.5])

    def update_fov(self, pixelsize):
        ''' Because of the camera rotation by 90 degrees, x and y are interchanged.'''
        self.pixelsize = pixelsize
        self.x_fov = self.y_pixels * self.pixelsize
        self.y_fov = self.x_pixels * self.pixelsize

class CurrentFOV(pg.ROI):
    """
    Rectangular ROI subclass with a single scale handle at the top-right corner.
    
    ============== =============================================================
    **Arguments**
    pos            (length-2 sequence) The position of the ROI origin.
                   See ROI().
    size           (length-2 sequence) The size of the ROI. See ROI().
    centered       (bool) If True, scale handles affect the ROI relative to its
                   center, rather than its origin.
    sideScalers    (bool) If True, extra scale handles are added at the top and 
                   right edges.
    \**args        All extra keyword arguments are passed to ROI()
    ============== =============================================================
    
    """
    def __init__(self, pos, size, **args):
        x_pos = pos[0] - int(size[0]/2)
        y_pos = pos[1] - int(size[1]/2)
        pg.ROI.__init__(self, [x_pos, y_pos], size, **args)
        center = [0.5, 0.5]
        self.translatable = False

    def contextMenuEnabled(self):
        return True
    
    def raiseContextMenu(self, ev):
        if not self.contextMenuEnabled():
            return
        menu = self.getMenu()
        menu = self.scene().addParentContextMenus(self, menu, ev)
        pos = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))
    
    def getMenu(self):
        if self.menu is None:
            self.menu = QtGui.QMenu()
            self.menu.setTitle("ROI Menu")
            printAct = QtGui.QAction("Print Something", self.menu)
            printAct.triggered.connect(self.printClicked)
            self.menu.addAction(printAct)
            self.menu.printAct = printAct
        return self.menu
    
    def printClicked(self):
        print('I have been clicked')

class CrosshairROI(pg.ROI):
    """A crosshair ROI whose position is at the center of the crosshairs. By default, it is scalable, rotatable and translatable."""
    
    def __init__(self, pos=None, size=None, **kargs):
        if size == None:
            size=[1,1]
        if pos == None:
            pos = [0,0]
        self._shape = None
        pg.ROI.__init__(self, pos, size, **kargs)
        
        self.sigRegionChanged.connect(self.invalidate)
        self.addScaleRotateHandle(pg.Point(1, 0), pg.Point(0, 0))
        self.aspectLocked = True

    def invalidate(self):
        self._shape = None
        self.prepareGeometryChange()
        
    def boundingRect(self):
        return self.shape().boundingRect()
    
    def shape(self):
        if self._shape is None:
            radius = self.getState()['size'][1]
            p = QtGui.QPainterPath()
            p.moveTo(pg.Point(0, -radius))
            p.lineTo(pg.Point(0, radius))
            p.moveTo(pg.Point(-radius, 0))
            p.lineTo(pg.Point(radius, 0))
            p = self.mapToDevice(p)
            stroker = QtGui.QPainterPathStroker()
            stroker.setWidth(10)
            outline = stroker.createStroke(p)
            self._shape = self.mapFromDevice(outline)
            
        return self._shape
    
    def paint(self, p, *args):
        radius = self.getState()['size'][1]
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.currentPen)
        
        p.drawLine(pg.Point(0, -radius), pg.Point(0, radius))
        p.drawLine(pg.Point(-radius, 0), pg.Point(radius, 0))