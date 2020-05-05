'''
mesoSPIM TilingManagerWindow 

Displays an overview of tile positions.
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
        self.state.sig_updated.connect(self.check_for_state_changes)

        self.model = self.parent.model
        self.model.dataChanged.connect(self.update_acquisition_view)
        self.model.modelReset.connect(self.update_acquisition_view)
        self.model.dataChanged.connect(self.update_rotation_combobox)
        self.model.modelReset.connect(self.update_rotation_combobox)

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
        self.setWindowTitle('mesoSPIM-Control: Tiling Viewer')

        self.viewBox = self.graphicsLayoutWidget.addViewBox(lockAspect=1.0)
        self.viewBox.setRange(xRange=[-10000,10000], yRange=[-10000,10000])

        self.position = self.state['position']
        self.displayed_rotation = self.position['theta_pos']
        self.current_rotation = self.position['theta_pos']

        self.RotationSelectionComboBox.currentTextChanged.connect(self.update_displayed_rotation)
        
        self.grid = pg.GridItem()
        self.viewBox.addItem(self.grid)

        self.old_zoom = self.state['zoom']
        self.zoom = self.state['zoom']

        self.fovPen = pg.mkPen({'color':"F00", 'width':2})
        self.roiPen = pg.mkPen({'color':"#C0C0C0", 'width':2})

        self.pixelsize = self.state['pixelsize']
        self.x_pixels = self.cfg.camera_parameters['x_pixels']
        self.y_pixels = self.cfg.camera_parameters['y_pixels']
        self.x_fov = self.y_pixels * self.pixelsize
        self.y_fov = self.x_pixels * self.pixelsize
        
        self.currentFOV = CurrentFOV([0,0],[self.x_fov, self.y_fov], pen=self.fovPen)
        self.viewBox.addItem(self.currentFOV)

        self.rois = []
        
    def check_for_state_changes(self):
        ''' Checks if there are changes in the state that require redrawing of parts of the 
        Tiling Manager Window and initiates updates when necessary. '''

        _position, _pixelsize = self.state.get_parameter_list(['position','pixelsize'])
        if self.position != _position:
            self.position = _position
            if self.RotationSelectionComboBox.currentText() == 'Current':
                if self.displayed_rotation != self.position['theta_pos']:
                    self.displayed_rotation = self.position['theta_pos']
                    self.current_rotation = self.position['theta_pos']

            self.update_acquisition_view()
            self.update_current_fov()

        if self.pixelsize != _pixelsize:
            self.pixelsize = _pixelsize
            self.update_acquisition_view()
            self.update_current_fov()

    def update_current_fov(self):
        self.x_pos = self.position['x_pos']
        self.y_pos = self.position['y_pos']
        self.current_rotation = self.position['theta_pos']
        
        if abs(self.displayed_rotation - self.current_rotation) < 0.1:
            if self.currentFOV not in self.viewBox.addedItems:
                self.viewBox.addItem(self.currentFOV)
      
        else:
            if self.currentFOV in self.viewBox.addedItems:
                self.viewBox.removeItem(self.currentFOV)

        self.currentFOV.setPos((self.x_pos, self.y_pos), update=False)
        self.x_fov = self.y_pixels * self.pixelsize
        self.y_fov = self.x_pixels * self.pixelsize
        self.currentFOV.setSize((self.x_fov, self.y_fov))

    def update_rotation_combobox(self):
        self.RotationSelectionComboBox.blockSignals(True)
        self.RotationSelectionComboBox.clear()
        self.RotationSelectionComboBox.addItem('Current')
        list_of_rotations = self.model.getUniqueRotationList()
        list_of_rotations.sort() # Display rotations in ascending order
        list_of_rotations = [str(round(item, 2)) for item in list_of_rotations]
        self.RotationSelectionComboBox.addItems(list_of_rotations)
        self.RotationSelectionComboBox.blockSignals(False)

    @QtCore.pyqtSlot(str)     
    def update_displayed_rotation(self, new_rotation_string):
        if new_rotation_string == 'Current':
            self.displayed_rotation = self.current_rotation
        else:
            self.displayed_rotation = float(new_rotation_string)
        
        self.update_acquisition_view()
        self.update_current_fov()

    def update_selection(self, new_selection, old_selection):
        if new_selection.indexes() != []:
            new_row = new_selection.indexes()[0].row()
            for roi in self.rois:
                if roi.rowID == new_row:
                    roi.setSelected(True)
                        
        if old_selection.indexes() != []:
            old_row = old_selection.indexes()[0].row()
            for roi in self.rois:
                if roi.rowID == old_row:
                    roi.setSelected(False)
    
    def update_acquisition_view(self):
        ''' Goes through the acquisition model and updates the view '''

        for r in self.rois:
            self.viewBox.removeItem(r)

        self.rois = []
        
        row_count = self.model.rowCount()

        for row in range(row_count):
            rotation = self.model.getRotationPosition(row)
            ''' Only display stacks with rotations close to the displayed rotation '''
            if abs(self.displayed_rotation - rotation) <= 0.5:
                xpos = self.model.getXPosition(row)
                ypos = self.model.getYPosition(row)
                zoom = self.model.getZoom(row)
                shutterconfig = self.model.getShutterconfig(row)

                pixelsize = self.cfg.pixelsize[zoom]
                x_fov = self.y_pixels * pixelsize
                y_fov = self.x_pixels * pixelsize

                self.rois.append(AcquisitionROI([xpos, ypos], [x_fov, y_fov], rowID=row, shutterconfig=shutterconfig, pen=self.roiPen))

        for r in self.rois:
            self.viewBox.addItem(r)

class AcquisitionROI(pg.ROI):
    """
    Elliptical ROI subclass 

    ============== =============================================================
    **Arguments**
    pos            (length-2 sequence) The position of the ROI's center.
    size           (length-2 sequence) The size of the ROI's bounding rectangle.
    \**args        All extra keyword arguments are passed to ROI()
    ============== =============================================================
    
    """
    def __init__(self, pos, size, rowID, shutterconfig, **args):
        self.path = None
        ''' Shift the position so that the center is the middle'''
        pos = (pos[0]-int(size[0]/2),pos[1]-int(size[1]/2))

        pg.ROI.__init__(self, pos, size, **args)
        self.sigRegionChanged.connect(self._clearPath)
        self.translatable = False

        self.rowID = rowID

        self.roiSelectedPen = pg.mkPen({'color':"#FF0", 'width':2})
        self.roiPen = pg.mkPen({'color':"#C0C0C0", 'width':2})

        self.stdPen = self.currentPen
        self.shutterconfig = shutterconfig
                   
    def _clearPath(self):
        self.path = None

    def hoverEvent(self, ev):
        hover = False
        if not ev.isExit():
            if self.translatable and ev.acceptDrags(QtCore.Qt.LeftButton):
            #if ev.acceptDrags(QtCore.Qt.LeftButton):
                hover=True
                
            for btn in [QtCore.Qt.LeftButton, QtCore.Qt.RightButton, QtCore.Qt.MidButton]:
                if int(self.acceptedMouseButtons() & btn) > 0 and ev.acceptClicks(btn):
                    hover=True
            if self.contextMenuEnabled():
                ev.acceptClicks(QtCore.Qt.RightButton)
                
        if hover:
            self.setMouseHover(True)
            ev.acceptClicks(QtCore.Qt.LeftButton)  ## If the ROI is hilighted, we should accept all clicks to avoid confusion.
            ev.acceptClicks(QtCore.Qt.RightButton)
            ev.acceptClicks(QtCore.Qt.MidButton)
            self.sigHoverEvent.emit(self)
        else:
            self.setMouseHover(False)

    def setMouseHover(self, hover):
        ## Inform the ROI that the mouse is(not) hovering over it
        if self.mouseHovering == hover:
            return
        self.mouseHovering = hover
        self._updateHoverColor()
        
    def _updateHoverColor(self):
        pen = self._makePen()
        if self.currentPen != pen:
            self.currentPen = pen
            self.update()

    def setSelected(self, boolean):
        if boolean:
            self.currentPen = self.roiSelectedPen
            self.update()
        else:
            self.currentPen = self.stdPen
            self.update()
        
    def _makePen(self):
        # Generate the pen color for this ROI based on its current state.
        if self.mouseHovering:
            return pg.functions.mkPen(255, 255, 0)
        else:
            return self.pen

    def contextMenuEnabled(self):
        # return self.removable
        return True

    def paint(self, p, opt, widget):
        r = self.boundingRect()
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setPen(self.currentPen)
        
        p.scale(r.width(), r.height())## workaround for GL bug
        r = QtCore.QRectF(r.x()/r.width(), r.y()/r.height(), 1,1)
        
        # p.drawEllipse(r)
        #pen0 = pg.mkPen({'color':"#C0C0C0", 'width':3})
        #pen1 = pg.mkPen({'color':"#C0C0C0", 'width':1})

        if self.shutterconfig == 'Left':
            pen = p.pen()
            pen.setWidth(3)
            p.setPen(pen)
            p.drawArc(r,90*16,180*16)
            pen = p.pen()
            pen.setWidth(1)
            p.setPen(pen)
            p.drawArc(r,-90*16,180*16)
        elif self.shutterconfig == 'Right':
            pen = p.pen()
            pen.setWidth(1)
            p.setPen(pen)
            p.drawArc(r,90*16,180*16)
            pen = p.pen()
            pen.setWidth(3)
            p.setPen(pen)
            p.drawArc(r,-90*16,180*16)
        else:
            pen = p.pen()
            pen.setWidth(3)
            p.setPen(pen)
            p.drawArc(r,90*16,180*16)
            p.drawArc(r,-90*16,180*16)
        
        
        
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
        # size = [int(i/2) for i in size] # Divide size by 2 to convert FOV -> radius
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

    def setSize(self, size, center=None, centerLocal=None, snap=False, update=True, finish=True):
        """
        Set the ROI's size.
        
        =============== ==========================================================================
        **Arguments**
        size            (Point | QPointF | sequence) The final size of the ROI
        center          (None | Point) Optional center point around which the ROI is scaled,
                        expressed as [0-1, 0-1] over the size of the ROI.
        centerLocal     (None | Point) Same as *center*, but the position is expressed in the
                        local coordinate system of the ROI
        snap            (bool) If True, the final size is snapped to the nearest increment (see
                        ROI.scaleSnapSize)
        update          (bool) See setPos()
        finish          (bool) See setPos()
        =============== ==========================================================================
        """
        if update not in (True, False):
            raise TypeError("update argument must be bool")
        size = [int(i/2) for i in size] # Divide size by 2 to convert FOV -> radius
        size = pg.Point(size)
        if snap:
            size[0] = round(size[0] / self.scaleSnapSize) * self.scaleSnapSize
            size[1] = round(size[1] / self.scaleSnapSize) * self.scaleSnapSize

        if centerLocal is not None:
            oldSize = pg.Point(self.state['size'])
            oldSize[0] = 1 if oldSize[0] == 0 else oldSize[0]
            oldSize[1] = 1 if oldSize[1] == 0 else oldSize[1]
            center = pg.Point(centerLocal) / oldSize

        if center is not None:
            center = pg.Point(center)
            c = self.mapToParent(pg.Point(center) * self.state['size'])
            c1 = self.mapToParent(pg.Point(center) * size)
            newPos = self.state['pos'] + c - c1
            self.setPos(newPos, update=False, finish=False)
        
        self.prepareGeometryChange()
        self.state['size'] = size
        if update:
            self.stateChanged(finish=finish)