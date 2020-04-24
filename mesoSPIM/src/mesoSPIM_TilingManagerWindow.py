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

        self.viewBox = self.graphicsLayoutWidget.addViewBox(lockAspect=1.0)
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

        self.tileROI = EllipticalTileROI([0,0],[1000,2000])
        self.viewBox.addItem(self.tileROI)

        # self.myCrossHair = CrosshairROI([0,0], [1000,1000])
        # self.viewBox.addItem(self.myCrossHair)
        
        self.rois = []
        xmax = 3
        ymax = 4
        for i in range(1,xmax+1):
            for j in range(1,ymax+1):
                self.rois.append(pg.CircleROI([i*1000, j*1000], [1200, 1200], pen=(i+j,xmax+ymax)))

        for r in self.rois:
            self.viewBox.addItem(r)

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
            self.currentFOV.scale([scaling_factor,scaling_factor])

    def update_fov(self, pixelsize):
        ''' Because of the camera rotation by 90 degrees, x and y are interchanged.'''
        self.pixelsize = pixelsize
        self.x_fov = self.y_pixels * self.pixelsize
        self.y_fov = self.x_pixels * self.pixelsize

class EllipticalTileROI(pg.ROI):
    """
    Elliptical ROI subclass 

    ============== =============================================================
    **Arguments**
    pos            (length-2 sequence) The position of the ROI's center.
    size           (length-2 sequence) The size of the ROI's bounding rectangle.
    \**args        All extra keyword arguments are passed to ROI()
    ============== =============================================================
    
    """
    def __init__(self, pos, size, **args):
        self.path = None
        pg.ROI.__init__(self, pos, size, **args)
        self.sigRegionChanged.connect(self._clearPath)
        self.translatable = False
                   
    def _clearPath(self):
        self.path = None
        
    def paint(self, p, opt, widget):
        r = self.boundingRect()
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.currentPen)
        
        p.scale(r.width(), r.height())## workaround for GL bug
        r = QtCore.QRectF(r.x()/r.width(), r.y()/r.height(), 1,1)
        
        p.drawEllipse(r)
        
    def shape(self):
        if self.path is None:
            path = QtGui.QPainterPath()
            
            # Note: Qt has a bug where very small ellipses (radius <0.001) do
            # not correctly intersect with mouse position (upper-left and 
            # lower-right quadrants are not clickable).
            #path.addEllipse(self.boundingRect())
            
            # Workaround: manually draw the path.
            br = self.boundingRect()
            center = br.center()
            r1 = br.width() / 2.
            r2 = br.height() / 2.
            theta = np.linspace(0, 2*np.pi, 24)
            x = center.x() + r1 * np.cos(theta)
            y = center.y() + r2 * np.sin(theta)
            path.moveTo(x[0], y[0])
            for i in range(1, len(x)):
                path.lineTo(x[i], y[i])
            self.path = path
        
        return self.path

class CurrentFOV(pg.ROI):
    """A crosshair ROI whose position is at the center of the crosshairs. By default, it is scalable, rotatable and translatable."""
    
    def __init__(self, pos=None, size=None, **kargs):
        if size == None:
            size=[1,1]
        if pos == None:
            pos = [0,0] 
        size = [int(i/2) for i in size] # Divide size by 2 to convert FOV -> radius
        self._shape = None
        pg.ROI.__init__(self, pos, size, **kargs)
        
        self.sigRegionChanged.connect(self.invalidate)
        self.aspectLocked = True
        self.translatable = False

    def invalidate(self):
        self._shape = None
        self.prepareGeometryChange()
        
    def boundingRect(self):
        return self.shape().boundingRect()

    def shape(self):
        if self._shape is None:
            x_halfwidth = self.getState()['size'][0]
            y_halfwidth = self.getState()['size'][1]
            p = QtGui.QPainterPath()
            p.moveTo(pg.Point(0, -y_halfwidth))
            p.lineTo(pg.Point(0, y_halfwidth))
            p.moveTo(pg.Point(-x_halfwidth, 0))
            p.lineTo(pg.Point(x_halfwidth, 0))
            p.moveTo(pg.Point(-x_halfwidth, y_halfwidth))
            p.lineTo(pg.Point(x_halfwidth, y_halfwidth))
            p.lineTo(pg.Point(x_halfwidth, -y_halfwidth))
            p.lineTo(pg.Point(-x_halfwidth, -y_halfwidth))
            p.lineTo(pg.Point(-x_halfwidth, y_halfwidth))
            p = self.mapToDevice(p)
            stroker = QtGui.QPainterPathStroker()
            stroker.setWidth(10)
            outline = stroker.createStroke(p)
            self._shape = self.mapFromDevice(outline)
        
        return self._shape
    
    def paint(self, p, *args):
        ''' Defines in which region the shape is painted '''
        x_halfwidth = self.getState()['size'][0]
        y_halfwidth = self.getState()['size'][1]
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.currentPen)
        
        p.drawLine(pg.Point(0, -y_halfwidth), pg.Point(0, y_halfwidth))
        p.drawLine(pg.Point(-x_halfwidth, 0), pg.Point(x_halfwidth, 0))
        p.drawLine(pg.Point(-x_halfwidth, -y_halfwidth), pg.Point(-x_halfwidth, y_halfwidth))
        p.drawLine(pg.Point(-x_halfwidth, y_halfwidth), pg.Point(x_halfwidth, y_halfwidth))
        p.drawLine(pg.Point(x_halfwidth, y_halfwidth), pg.Point(x_halfwidth, -y_halfwidth))
        p.drawLine(pg.Point(x_halfwidth, -y_halfwidth), pg.Point(-x_halfwidth, -y_halfwidth))

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