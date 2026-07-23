"""
Presentation Layer - Status Badge Component

Semantic feedback badge displaying operational status (Connected, Disconnected, Flashing,
Warning, Danger, Verified) with color coding and icon indicator.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from gui.design_system.tokens import ColorTokens


class StatusBadge(QFrame):
    """Semantic status badge widget."""

    def __init__(self, text: str = "OFFLINE", status_level: str = "neutral", parent=None):
        super().__init__(parent)
        self._label = QLabel(text)
        self._dot = QLabel("●")
        self._status_level = status_level

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(6)
        layout.addWidget(self._dot)
        layout.addWidget(self._label)

        self.set_status(text, status_level)

    def set_status(self, text: str, level: str = "neutral") -> None:
        self._status_level = level
        self._label.setText(text)

        colors = ColorTokens()

        if level == "success":
            bg = colors.success_soft
            fg = colors.success_text
            border = colors.success_border
        elif level == "warning":
            bg = colors.warning_soft
            fg = colors.warning_text
            border = colors.warning_border
        elif level == "danger":
            bg = colors.danger_soft
            fg = colors.danger_text
            border = colors.danger_border
        elif level == "info":
            bg = colors.accent_soft
            fg = colors.text_primary
            border = colors.accent_border
        else:  # neutral
            bg = colors.surface_control
            fg = colors.text_secondary
            border = colors.border_subtle

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 4px;
            }}
            QLabel {{
                color: {fg};
                font-size: 11px;
                font-weight: 600;
                background: transparent;
                border: none;
            }}
        """)
