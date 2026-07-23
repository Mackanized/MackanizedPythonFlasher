"""
Presentation Layer - Zone 3 Navigation Rail Component

Persistent vertical navigation bar exposing top-level module workspaces:
1. Flashing Workspace (Ctrl+1)
2. UDS & CAN Diagnostics (Ctrl+2)
3. Memory & Hex Viewer (Ctrl+3)
4. Telemetry Dashboard (Ctrl+4)
5. Audit Logs (Ctrl+5)
6. System Settings (Ctrl+6)
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout
from gui.design_system.tokens import ColorTokens


class NavRail(QFrame):
    """Zone 3 Persistent Vertical Navigation Rail Widget."""

    workspace_selected = Signal(int, str)  # index, name

    WORKSPACES = [
        ("Flashing", "⚡ ECU Flashing"),
        ("Diagnostics", "🔍 UDS & CAN"),
        ("Memory", "🧩 Memory & Hex"),
        ("Telemetry", "📈 Telemetry"),
        ("Logs", "📋 Audit Logs"),
        ("Settings", "⚙️ Settings"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(160)

        self._buttons = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 12, 6, 12)
        layout.setSpacing(6)

        for idx, (key, label) in enumerate(self.WORKSPACES):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding-left: 12px;
                    font-weight: 600;
                    font-size: 12px;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:checked {
                    background-color: #007ACC;
                    color: #FFFFFF;
                }
            """)
            btn.clicked.connect(lambda checked=False, i=idx, k=key: self._on_clicked(i, k))
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()
        self.set_active_workspace(0)

    def _on_clicked(self, idx: int, key: str) -> None:
        self.set_active_workspace(idx, emit_signal=True)

    def set_active_workspace(self, active_idx: int, emit_signal: bool = True) -> None:
        if 0 <= active_idx < len(self._buttons):
            for idx, btn in enumerate(self._buttons):
                btn.setChecked(idx == active_idx)
            if emit_signal:
                key = self.WORKSPACES[active_idx][0]
                self.workspace_selected.emit(active_idx, key)
