"""GUI backend"""

import json
import re
import subprocess
import os
import shutil
import atexit
import time
import logging
from typing import Callable

from PySide6.QtCore import QObject, Property, Slot, Signal
from PySide6.QtGui import QCursor
from PySide6.QtQml import qmlRegisterType
from PySide6.QtWidgets import QApplication
from netifaces import interfaces, ifaddresses, AF_INET

from .display import DisplayProperty
from .xrandr import XRandR
from .process import AsyncSubprocess, SubprocessWrapper
from .path import (DATA_PATH, CONFIG_PATH, DEFAULT_CONFIG_PATH,
                  X11VNC_PASSWORD_PATH, X11VNC_LOG_PATH)


class Backend(QObject):
    """ Backend class for QML frontend """

    class VNCState:
        """ Enum to indicate a state of the VNC server """
        OFF = 0
        ERROR = 1
        WAITING = 2
        CONNECTED = 3

    # Signals
    onVirtScreenCreatedChanged = Signal(bool)
    onVncUsePasswordChanged = Signal(bool)
    onVncStateChanged = Signal(int)
    onDisplaySettingClosed = Signal()
    onError = Signal(str)
    onSettingsChanged = Signal()

    def __init__(self, parent=None, logger=logging.info, error_logger=logging.error):
        super(Backend, self).__init__(parent)
        # Virtual screen properties
        self.xrandr: XRandR = XRandR()
        self._virtScreenCreated: bool = False
        # VNC server properties
        self._vncUsePassword: bool = False
        self._vncState: self.VNCState = self.VNCState.OFF
        # Primary screen and mouse posistion
        self.vncServer: AsyncSubprocess
        # Info/error logger
        self.log: Callable[[str], None] = logger
        self.log_error: Callable[[str], None] = error_logger
        # Check config file 
        # and initialize if needed
        need_init = False
        if not os.path.exists(CONFIG_PATH):
            shutil.copy(DEFAULT_CONFIG_PATH, CONFIG_PATH)
            need_init = True
        # Version check
        file_match = True
        with open(CONFIG_PATH, 'r') as f_config, open(DATA_PATH, 'r') as f_data:
            config = json.load(f_config)
            data = json.load(f_data)
            if config['version'] != data['version']:
                file_match = False
        # Override config with default when version doesn't match
        if not file_match:
            shutil.copy(DEFAULT_CONFIG_PATH, CONFIG_PATH)
            need_init = True
        # initialize config file
        if need_init:
            # 1. Available x11vnc options
            # Get available x11vnc options from x11vnc first
            p = SubprocessWrapper()
            arg = 'x11vnc -opts'
            ret = p.run(arg)
            options = tuple(m.group(1) for m in re.finditer(r"\s*(-\w+)\s+", ret))
            # Set/unset available x11vnc options flags in config
            with open(CONFIG_PATH, 'r') as f, open(DATA_PATH, 'r') as f_data:
                config = json.load(f)
                data = json.load(f_data)
                for key, value in config["x11vncOptions"].items():
                    if key in options:
                        value["available"] = True
                    else:
                        value["available"] = False
                # Default Display settings app for a Desktop Environment
                desktop_environ = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
                for key, value in data['displaySettingApps'].items():
                    if desktop_environ in value['XDG_CURRENT_DESKTOP']:
                        config["displaySettingApp"] = key
            # Save the new config
            with open(CONFIG_PATH, 'w') as f:
                f.write(json.dumps(config, indent=4, sort_keys=True))

    def promptError(self, msg):
        self.log_error(msg)
        self.onError.emit(msg)

    # Qt properties
    def _get_settings(self):
        with open(CONFIG_PATH, "r") as f:
            return f.read()

    def _set_settings(self, json_str):
        with open(CONFIG_PATH, "w") as f:
            f.write(json_str)
        # notify QML that settings changed
        try:
            self.onSettingsChanged.emit()
        except Exception:
            pass
    settings = Property(str, _get_settings, _set_settings, notify=onSettingsChanged)

    # Expose VNCState enum values as instance-level constant properties
    @Property(int, constant=True)
    def OFF(self):
        return self.VNCState.OFF

    @Property(int, constant=True)
    def ERROR(self):
        return self.VNCState.ERROR

    @Property(int, constant=True)
    def WAITING(self):
        return self.VNCState.WAITING

    @Property(int, constant=True)
    def CONNECTED(self):
        return self.VNCState.CONNECTED

    @Property(bool, notify=onVirtScreenCreatedChanged)
    def virtScreenCreated(self):
        return self._virtScreenCreated

    @virtScreenCreated.setter
    def virtScreenCreated(self, value):
        self._virtScreenCreated = value
        self.onVirtScreenCreatedChanged.emit(value)

    @Property(list, constant=True)
    def screens(self):
        try:
            # Cache DisplayProperty objects as QObjects with self as parent
            try:
                self._screen_props = [DisplayProperty(x, self) for x in self.xrandr.screens]
            except Exception:
                # fallback without parent
                self._screen_props = [DisplayProperty(x) for x in self.xrandr.screens]
            return self._screen_props
        except RuntimeError as e:
            self.promptError(str(e))
            return []

    @Property(bool, notify=onVncUsePasswordChanged)
    def vncUsePassword(self):
        if os.path.isfile(X11VNC_PASSWORD_PATH):
            self._vncUsePassword = True
        else:
            if self._vncUsePassword:
                self.vncUsePassword = False
        return self._vncUsePassword

    @vncUsePassword.setter
    def vncUsePassword(self, use):
        self._vncUsePassword = use
        self.onVncUsePasswordChanged.emit(use)

    @Property(int, notify=onVncStateChanged)
    def vncState(self):
        return self._vncState

    @vncState.setter
    def vncState(self, state):
        self._vncState = state
        self.onVncStateChanged.emit(self._vncState)

    # Qt Slots
    @Slot(str, int, int, bool, bool)
    def createVirtScreen(self, device, width, height, portrait, hidpi, pos=''):
        self.xrandr.virt_name = device
        self.log("Creating a Virtual Screen...")
        try:
            self.xrandr.create_virtual_screen(width, height, portrait, hidpi, pos)
        except subprocess.CalledProcessError as e:
            self.promptError(str(e.cmd) + '\n' + e.stdout.decode('utf-8'))
            return
        except RuntimeError as e:
            self.promptError(str(e))
            return
        self.virtScreenCreated = True
        self.log("The Virtual Screen successfully created.")

    @Slot()
    def deleteVirtScreen(self):
        self.log("Deleting the Virtual Screen...")
        if self.vncState is not self.VNCState.OFF:
            self.promptError("Turn off the VNC server first")
            self.virtScreenCreated = True
            return
        try:
            self.xrandr.delete_virtual_screen()
        except RuntimeError as e:
            self.promptError(str(e))
            return
        self.virtScreenCreated = False

    @Slot(str)
    def createVNCPassword(self, password):
        if password:
            password += '\n' + password + '\n\n'  # verify + confirm
            p = SubprocessWrapper()
            try:
                p.run(f"x11vnc -storepasswd {X11VNC_PASSWORD_PATH}", input=password, check=True)
            except subprocess.CalledProcessError as e:
                self.promptError(str(e.cmd) + '\n' + e.stdout.decode('utf-8'))
                return
            self.vncUsePassword = True
        else:
            self.promptError("Empty password")

    @Slot()
    def deleteVNCPassword(self):
        if os.path.isfile(X11VNC_PASSWORD_PATH):
            os.remove(X11VNC_PASSWORD_PATH)
            self.vncUsePassword = False
        else:
            self.promptError("Failed deleting the password file")

    @Slot(int)
    def startVNC(self, port):
        # Check if a virtual screen created
        if not self.virtScreenCreated:
            self.promptError("Virtual Screen not crated.")
            return
        if self.vncState is not self.VNCState.OFF:
            self.promptError("VNC Server is already running.")
            return
        # regex used in callbacks
        patter_connected = re.compile(r"^.*Got connection from client.*$", re.M)
        patter_disconnected = re.compile(r"^.*client_count: 0*$", re.M)

        # define callbacks
        def _connected():
            self.log(f"VNC started. Now connect a VNC client to port {port}.")
            self.vncState = self.VNCState.WAITING

        def _received(data):
            data = data.decode("utf-8")
            if (self._vncState is not self.VNCState.CONNECTED) and patter_connected.search(data):
                self.log("VNC connected.")
                self.vncState = self.VNCState.CONNECTED
            if (self._vncState is self.VNCState.CONNECTED) and patter_disconnected.search(data):
                self.log("VNC disconnected.")
                self.vncState = self.VNCState.WAITING

        def _ended(exitCode):
            if exitCode != 0:
                self.vncState = self.VNCState.ERROR
                self.promptError('X11VNC: Error occurred.\n'
                                  'Double check if the port is already used.')
                self.vncState = self.VNCState.OFF  # TODO: better handling error state
            else:
                self.vncState = self.VNCState.OFF
            self.log("VNC Exited.")
            atexit.unregister(self.stopVNC)
        # load settings
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        options = ''
        if config['customX11vncArgs']['enabled']:
            options = config['customX11vncArgs']['value']
        else:
            for key, value in config['x11vncOptions'].items():
                if value['available'] and value['enabled']:
                    options += key + ' '
                    if value['arg'] is not None:
                        options += str(value['arg']) + ' '
        # Sart x11vnc, turn settings object into VNC arguments format
        logfile = open(X11VNC_LOG_PATH, "wb")
        self.vncServer = AsyncSubprocess(_connected, _received, _received, _ended, logfile)
        try:
            virt = self.xrandr.get_virtual_screen()
        except RuntimeError as e:
            self.promptError(str(e))
            return
        clip = f"{virt.width}x{virt.height}+{virt.x_offset}+{virt.y_offset}"
        arg = f"x11vnc -rfbport {port} -clip {clip} {options}"
        if self.vncUsePassword:
            arg += f" -rfbauth {X11VNC_PASSWORD_PATH}"
        self.vncServer.run(arg)
        # auto stop on exit
        atexit.register(self.stopVNC, force=True)

    @Slot(str)
    def openDisplaySetting(self, app: str = "arandr"):
        # define callbacks
        def _connected():
            self.log("External Display Setting opened.")

        def _received(data):
            pass

        def _ended(exitCode):
            self.log("External Display Setting closed.")
            self.onDisplaySettingClosed.emit()
            if exitCode != 0:
                self.promptError(f'Error opening "{running_program}".')
        with open(DATA_PATH, 'r') as f:
            data = json.load(f)['displaySettingApps']
            if app not in data:
                self.promptError('Wrong display settings program')
                return
        program_list = [data[app]['args'], "arandr"]
        program = AsyncSubprocess(_connected, _received, _received, _ended, None)
        running_program = ''
        for arg in program_list:
            if not shutil.which(arg.split()[0]):
                continue
            running_program = arg
            program.run(arg)
            return
        self.promptError('Failed to find a display settings program.\n'
                         'Please install ARandR package.\n'
                         '(e.g. sudo apt-get install arandr)\n'
                         'Please issue a feature request\n'
                         'if you wish to add a display settings\n'
                         'program for your Desktop Environment.')

    @Slot()
    def stopVNC(self, force=False):
        if force:
            # Usually called from atexit().
            self.vncServer.close()
            time.sleep(3)  # Make sure X11VNC shutdown before execute next atexit().
        if self._vncState in (self.VNCState.WAITING, self.VNCState.CONNECTED):
            self.vncServer.close()
        else:
            self.promptError("stopVNC called while it is not running")

    @Slot()
    def clearCache(self):
        # engine.clearComponentCache()
        pass

    @Slot()
    def quitProgram(self):
        self.blockSignals(True)  # This will prevent invoking auto-restart or etc.
        QApplication.instance().quit()


class Cursor(QObject):
    """ Global mouse cursor position """

    def __init__(self, parent=None):
        super(Cursor, self).__init__(parent)

    @Property(int)
    def x(self):
        cursor = QCursor().pos()
        return cursor.x()

    @Property(int)
    def y(self):
        cursor = QCursor().pos()
        return cursor.y()


class Network(QObject):
    """ Backend class for network interfaces """
    onIPAddressesChanged = Signal()

    def __init__(self, parent=None):
        super(Network, self).__init__(parent)

    @Property(list, notify=onIPAddressesChanged)
    def ipAddresses(self):
        result = []
        for interface in interfaces():
            if interface == 'lo':
                continue
            addresses = ifaddresses(interface).get(AF_INET, None)
            if addresses is None:
                continue
            for link in addresses:
                if link is not None:
                    result.append(link['addr'])
        return result
