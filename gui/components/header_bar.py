"""
Presentation Layer - Quiet Desktop Context Header Component

Header displaying active vehicle, ECU definition, security status, and hardware badge.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from gui.components.status_badge import StatusBadge


class HeaderBar(QFrame):
    """Quiet Context Header Widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet("background-color: #181A20; border-bottom: 1px solid rgba(255, 255, 255, 0.04);")

        self._app_title = QLabel("Mackanized flasher")
        self._app_title.setStyleSheet("font-weight: 800; font-size: 13px; color: #3B82F6; letter-spacing: 1.5px;")

        self._session_lbl = QLabel("Saab 9-3 2.8T V6  •  Bosch ME9.6.1")
        self._session_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; font-weight: 500;")

        self._conn_badge = StatusBadge("OFFLINE", "neutral")
        self._sec_badge = StatusBadge("LOCKED (0x00)", "warning")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(16)
        layout.addWidget(self._app_title)
        layout.addWidget(self._session_lbl)
        layout.addStretch()
        layout.addWidget(self._sec_badge)
        layout.addWidget(self._conn_badge)

    def update_session(self, vehicle: str, ecu: str) -> None:
        self._session_lbl.setText(f"{vehicle}  •  {ecu}")

    def update_connection(self, adapter_name: str, is_connected: bool) -> None:
        if is_connected:
            self._conn_badge.set_status(f"CONNECTED [{adapter_name}]", "success")
        else:
            self._conn_badge.set_status("OFFLINE", "neutral")

    def update_security(self, level_str: str) -> None:
        if "Unlocked" in level_str:
            self._sec_badge.set_status(level_str, "success")
        else:
            self._sec_badge.set_status(level_str, "warning")
