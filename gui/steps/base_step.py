from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class BaseStep(QWidget):
    """Base class for wizard steps. Subclasses emit next_enabled when validity changes."""
    next_enabled = Signal(bool)
    back_enabled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

    def on_enter(self):
        """Called when this step becomes active. Override in subclass."""
        pass

    def on_leave(self):
        """Called when navigating away. Override in subclass."""
        pass