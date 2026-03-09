"""Display information data classes"""

from PySide6.QtCore import QObject, Signal, Property


class Display(object):
    """Display information"""
    __slots__ = ['name', 'primary', 'connected', 'active', 'width', 'height',
                 'x_offset', 'y_offset']

    def __init__(self):
        self.name: str = None
        self.primary: bool = False
        self.connected: bool = False
        self.active: bool = False
        self.width: int = 0
        self.height: int = 0
        self.x_offset: int = 0
        self.y_offset: int = 0

    def __str__(self) -> str:
        ret = f"{self.name}"
        if self.connected:
            ret += " connected"
        else:
            ret += " disconnected"
        if self.primary:
            ret += " primary"
        if self.active:
            ret += f" {self.width}x{self.height}+{self.x_offset}+{self.y_offset}"
        else:
            ret += f" not active {self.width}x{self.height}"
        return ret


class DisplayProperty(QObject):
    """Wrapper around Display class for Qt"""
    def __init__(self, display: Display, parent=None):
        super(DisplayProperty, self).__init__(parent)
        self._display = display

    # Notify signals for QML bindings
    nameChanged = Signal()
    primaryChanged = Signal()
    connectedChanged = Signal()
    activeChanged = Signal()
    widthChanged = Signal()
    heightChanged = Signal()
    xOffsetChanged = Signal()
    yOffsetChanged = Signal()

    @property
    def display(self):
        return self._display

    def _get_name(self):
        return self._display.name

    def _set_name(self, name):
        if self._display.name != name:
            self._display.name = name
            self.nameChanged.emit()

    name = Property(str, _get_name, _set_name, notify=nameChanged)

    def _get_primary(self):
        return self._display.primary

    def _set_primary(self, value):
        if self._display.primary != value:
            self._display.primary = value
            self.primaryChanged.emit()

    primary = Property(bool, _get_primary, _set_primary, notify=primaryChanged)

    def _get_connected(self):
        return self._display.connected

    def _set_connected(self, value):
        if self._display.connected != value:
            self._display.connected = value
            self.connectedChanged.emit()

    connected = Property(bool, _get_connected, _set_connected, notify=connectedChanged)

    def _get_active(self):
        return self._display.active

    def _set_active(self, value):
        if self._display.active != value:
            self._display.active = value
            self.activeChanged.emit()

    active = Property(bool, _get_active, _set_active, notify=activeChanged)

    def _get_width(self):
        return self._display.width

    def _set_width(self, value):
        if self._display.width != value:
            self._display.width = value
            self.widthChanged.emit()

    width = Property(int, _get_width, _set_width, notify=widthChanged)

    def _get_height(self):
        return self._display.height

    def _set_height(self, value):
        if self._display.height != value:
            self._display.height = value
            self.heightChanged.emit()

    height = Property(int, _get_height, _set_height, notify=heightChanged)

    def _get_x_offset(self):
        return self._display.x_offset

    def _set_x_offset(self, value):
        if self._display.x_offset != value:
            self._display.x_offset = value
            self.xOffsetChanged.emit()

    x_offset = Property(int, _get_x_offset, _set_x_offset, notify=xOffsetChanged)

    def _get_y_offset(self):
        return self._display.y_offset

    def _set_y_offset(self, value):
        if self._display.y_offset != value:
            self._display.y_offset = value
            self.yOffsetChanged.emit()

    y_offset = Property(int, _get_y_offset, _set_y_offset, notify=yOffsetChanged)
