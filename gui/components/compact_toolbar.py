"""
Presentation Layer - Microsoft Fluent 2 Desktop Command Bar Component

Fluent 2 Command Bar (Visual Studio 2022 & JetBrains Rider Style):
- 24px Desktop Height
- Split Action Triggers (Connect ▾, Write Flash ▾)
- Pill Search Field (Ctrl+Shift+P)
- Restrained Dividers
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QToolButton, QWidget


class CompactCommandBar(QFrame):
    """Microsoft Fluent 2 Desktop Command Bar Widget."""

    connect_requested = Signal()
    disconnect_requested = Signal()
    read_requested = Signal()
    write_requested = Signal()
    verify_requested = Signal()
    recover_requested = Signal()
    security_requested = Signal()
    session_requested = Signal()
    dtc_requested = Signal()
    telemetry_requested = Signal()
    memory_requested = Signal()
    export_requested = Signal()
    search_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(34)
        self.setStyleSheet("background-color: #181818; border-bottom: 1px solid #2D2D2D;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(4)

        def add_btn(label: str, signal: Signal, is_primary: bool = False, is_danger: bool = False):
            btn = QToolButton()
            btn.setText(label)
            btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
            btn.setFixedHeight(24)
            if is_primary:
                btn.setObjectName("primaryBtn")
            elif is_danger:
                btn.setObjectName("dangerBtn")
            btn.clicked.connect(signal.emit)
            layout.addWidget(btn)
            return btn

        self._btn_conn = add_btn("Connect ▾", self.connect_requested, is_primary=True)
        self._btn_disconn = add_btn("Disconnect", self.disconnect_requested)
        add_btn("Read ECU", self.read_requested)
        add_btn("Write Flash ▾", self.write_requested, is_primary=True)
        add_btn("Verify", self.verify_requested)
        add_btn("Recover", self.recover_requested, is_danger=True)

        layout.addWidget(self._create_separator())

        add_btn("Security 0x27", self.security_requested)
        add_btn("Session 0x10", self.session_requested)
        add_btn("Read DTCs", self.dtc_requested)

        layout.addWidget(self._create_separator())

        add_btn("Telemetry", self.telemetry_requested)
        add_btn("Hex Map", self.memory_requested)
        add_btn("Export Log", self.export_requested)

        layout.addStretch()

        self._search = QLineEdit()
        self._search.setPlaceholderText("Filter parameters, DTCs, CAN IDs... (Ctrl+Shift+P)")
        self._search.setFixedWidth(260)
        self._search.setFixedHeight(22)
        self._search.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self._search)

    def _create_separator(self) -> QWidget:
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setFixedHeight(16)
        sep.setStyleSheet("background-color: #2D2D2D;")
        return sep

    def set_connected_state(self, is_connected: bool) -> None:
        self._btn_conn.setEnabled(not is_connected)
        self._btn_disconn.setEnabled(is_connected)
