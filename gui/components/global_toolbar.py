"""
Presentation Layer - Zone 2 Global Toolbar Component

Houses primary action triggers:
- Connect / Disconnect Hardware Adapter
- Read ECU
- Write Flash
- Emergency Stop Action
- Workshop Mode Switch
- Global Settings Trigger
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit
from gui.components.oem_button import OEMButton


class GlobalToolbar(QFrame):
    """Zone 2 Workstation Toolbar Widget."""

    connect_requested = Signal()
    read_requested = Signal()
    write_requested = Signal()
    emergency_stop_requested = Signal()
    search_changed = Signal(str)
    workshop_mode_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)

        self._conn_btn = OEMButton("Connect Hardware", "primary")
        self._conn_btn.setToolTip("Open diagnostic session with selected hardware interface adapter")
        self._conn_btn.clicked.connect(self.connect_requested.emit)

        self._read_btn = OEMButton("Read ECU", "secondary")
        self._read_btn.setToolTip("Initiate safety backup read of target ECU flash memory")
        self._read_btn.clicked.connect(self.read_requested.emit)

        self._write_btn = OEMButton("Write Flash", "warning")
        self._write_btn.setToolTip("Initiate high-consequence ECU flash programming session")
        self._write_btn.clicked.connect(self.write_requested.emit)

        self._stop_btn = OEMButton("Emergency Stop", "destructive")
        self._stop_btn.setToolTip("Latch safety abort: Stop active flashing transfer and safely reset ECU bus")
        self._stop_btn.clicked.connect(self.emergency_stop_requested.emit)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search ECU parameters, DTCs, CAN IDs... (Ctrl+F)")
        self._search.setMaximumWidth(320)
        self._search.textChanged.connect(self.search_changed.emit)

        self._workshop_btn = OEMButton("Workshop Mode", "toggle")
        self._workshop_btn.toggled.connect(self.workshop_mode_toggled.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(10)
        layout.addWidget(self._conn_btn)
        layout.addWidget(self._read_btn)
        layout.addWidget(self._write_btn)
        layout.addWidget(self._stop_btn)
        layout.addStretch()
        layout.addWidget(self._search)
        layout.addWidget(self._workshop_btn)

    def set_connected_state(self, is_connected: bool) -> None:
        if is_connected:
            self._conn_btn.setText("Disconnect")
            self._conn_btn.setObjectName("secondaryBtn")
        else:
            self._conn_btn.setText("Connect Hardware")
            self._conn_btn.setObjectName("primaryBtn")
        self._conn_btn.setStyle(self._conn_btn.style())
