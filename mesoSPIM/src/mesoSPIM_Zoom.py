"""
mesoSPIM Module for controlling a discrete zoom changer

Authors: Fabian Voigt, Nikita Vladimirov
"""

import time
import logging
from PyQt5 import QtCore
from .devices.servos.dynamixel.dynamixel import Dynamixel
import serial
logger = logging.getLogger(__name__)

class DemoZoom(QtCore.QObject):
    def __init__(self, zoomdict):
        super().__init__()
        self.zoomdict = zoomdict

    def set_zoom(self, zoom, wait_until_done=False):
        if zoom in self.zoomdict:
            if wait_until_done:
                time.sleep(1)
   

class DynamixelZoom(Dynamixel):
    def __init__(self, zoomdict, COMport, identifier=1, baudrate=115200):
        super().__init__(COMport, identifier, baudrate)
        self.zoomdict = zoomdict

    def set_zoom(self, zoom, wait_until_done=False):
        """Changes zoom after checking that the commanded value exists"""
        if zoom in self.zoomdict:
            self._move(self.zoomdict[zoom], wait_until_done)
            self.zoomvalue = zoom
        else:
            raise ValueError('Zoom designation not in the configuration')


class MitutoyoZoom(QtCore.QObject):
    def __init__(self, zoomdict, COMport, baudrate=9600):
        super().__init__()
        self.port = COMport
        self.baudrate = baudrate
        self.zoomdict = zoomdict
        try:
            self.revolver_connection = serial.Serial(self.port, self.baudrate, parity=serial.PARITY_EVEN, timeout=5,
                                                stopbits=serial.STOPBITS_ONE)
            self._initialize()
        except Exception as error:
            msg = f"Serial connection to Mitutoyo revolver failed, error: {error}"
            logger.error(msg)
            print(msg)

    def _initialize(self):
        response = self._send_command(b'RRDSTU\r')
        if response[:9] != 'ROK000001':
            msg = f"Error in Mitutoyo revolver initialization, response: {response} \nIf response is empty, check if the revolver is connected."
            logger.error(msg)
            print(msg)
        else:
            logger.info("Mitutoyo revolver initialized")

    def _send_command(self, command: bytes):
        try:
            self._reset_buffers()
            self.revolver_connection.write(command)
            message = self.revolver_connection.readline().decode("ascii")
            logger.debug(f"Serial received: {message} ")
            return message
        except Exception as error:
            logger.error(f"Serial exception of the Mitutoyo revolver: command {command.decode('ascii')}, error: {error}")

    def _reset_buffers(self):
        if self.revolver_connection is not None:
            self.revolver_connection.reset_input_buffer()
            self.revolver_connection.reset_output_buffer()
        else:
            logger.error("Serial port not initialized")

    def set_zoom(self, zoom, wait_until_done=False):
        if zoom in self.zoomdict:
            position = self.zoomdict[zoom]
            assert position in ('A', 'B', 'C', 'D', 'E'), "Revolver position must be one of ('A', 'B', 'C', 'D', 'E')"
            command = 'RWRMV' + position + '\r'
            message = self._send_command(command.encode('ascii'))
            if message != 'ROK\r\n':
                msg = f"Error in Mitutoyo revolver command, response:{message}."
                logger.error(msg)
                print(msg)
        else:
            return ValueError(f"Zoom {zoom} not in 'zoomdict', check your config file")
        
class PI_TurretZoom(QtCore.QObject):
    def __init__(self, parent, zoomdict, pi_parameters):
        super().__init__()
        self.parent = parent
        self.zoomdict = zoomdict
        self.pi_parameters = pi_parameters
        try:
            self._initialize()
        except Exception as error:
            msg = f"Serial connection to PI Turret controller, error: {error}"
            logger.error(msg)
            print(msg)

    def _initialize(self):
        from pipython import GCSDevice, pitools
        self.pitools = pitools

        self.controllername = self.pi_parameters['controllername']
        self.pi_stages = (self.pi_parameters['stages'])
        self.refmode = self.pi_parameters['refmode']
        self.serialnum = self.pi_parameters['serialnum']
        self.pidevice = GCSDevice(self.controllername)
        self.pidevice.ConnectUSB(serialnum=self.serialnum)

        pitools.startup(self.pidevice, stages=self.pi_stages)

        ''' Report reference status of all stages '''
        for ii in range(1, len(self.pi_stages) + 1):
            tStage = self.pi_stages[ii - 1]
            if tStage == 'NOSTAGE':
                continue

            tState = self.pidevice.qFRF(ii)
            if tState[ii]:
                msg = 'referenced'
            else:
                msg = '*UNREFERENCED*'

            logger.info("Turret axis: %d (%s) reference status: %s" % (ii, tStage, msg))
        logger.info("PI turret initialized")
        print("PI turret initialized")

    def __del__(self):
        try:
            self.pidevice.unload()
        except:
            pass

    def set_zoom(self, zoom, wait_until_done=False):
        if zoom in self.zoomdict:
            # Read current rotation stage position
            target_rotation = self.zoomdict[zoom]
            current_rotation = self.pidevice.qPOS(1)[1]
            print(f"Target: {target_rotation} Current: {current_rotation}")
            if current_rotation < target_rotation+0.1 and current_rotation > target_rotation-0.1:
                # Do not move the focus stage when you are already at the correct zoom
                msg = f"Zoom already set to correct value ({zoom} equivalent to {self.zoomdict[zoom]} degree rotation)."
                logger.info(msg)
                print(msg)
            else:
                # Record current focus position
                self.current_focus = self.parent.state['position']['f_pos']
                self.pi_parameters['safe_rotation_focus']
                # Go to save position to rotate the turret and wait until done
                self.parent.move_absolute({'f_pos':self.pi_parameters['safe_rotation_focus']}, wait_until_done = True)

                # Rotate turret to target position and wait until done 
                self.pidevice.MOV({1: self.zoomdict[zoom]})
                self.pitools.waitontarget(self.pidevice)
                
                # Move back to saved focus position and wait until done
                self.parent.move_absolute({'f_pos': self.current_focus}, wait_until_done = True)

                msg = f"Zoom set to {zoom} equivalent to {self.zoomdict[zoom]} degree rotation."
                logger.info(msg)
                print(msg)
        else:
            return ValueError(f"Zoom {zoom} not in 'zoomdict', check your config file")