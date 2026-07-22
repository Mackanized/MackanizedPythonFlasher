import logging

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class CANTracePanel(QWidget):
    """Collapsible panel showing live CAN bus frames."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._collapsed = True
        self._handler = None
        self._max_lines = 500
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._toggle_btn = QPushButton("CAN Trace  [+]")
        self._toggle_btn.setFixedHeight(36)
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self._toggle_btn)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setMaximumBlockCount(self._max_lines)
        self._text.setVisible(False)
        layout.addWidget(self._text)

    def _toggle(self):
        self._collapsed = not self._collapsed
        self._text.setVisible(not self._collapsed)
        self._toggle_btn.setText("CAN Trace  [-]" if not self._collapsed else "CAN Trace  [+]")

    def append_line(self, line: str):
        self._text.appendPlainText(line)

    def clear(self):
        self._text.clear()

    def install_logger(self):
        from logger import can_logger
        self._handler = _CANLogHandler(self.append_line)
        self._handler.setLevel(logging.INFO)
        can_logger.addHandler(self._handler)

    def remove_logger(self):
        from logger import can_logger
        if self._handler:
            can_logger.removeHandler(self._handler)
            self._handler = None


class _CANLogHandler(logging.Handler):
    """Pipes can_logger records into the CAN trace panel."""
    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def emit(self, record):
        try:
            self._callback(record.getMessage())
        except Exception:
            pass