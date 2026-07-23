"""
Presentation Layer - Automotive Voltage Meter Component

Displays real-time ECU battery voltage with color-coded safety thresholds:
- Normal (>12.4V): Green
- Acceptable / Warning (11.5V - 12.3V): Amber
- Critical (<11.4V): Red
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QProgressBar
from gui.design_system.tokens import ColorTokens


class VoltageMeter(QFrame):
    """Automotive battery voltage monitoring widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._val_label = QLabel("-- V")
        self._bar = QProgressBar()
        self._bar.setRange(90, 160)  # 9.0V to 16.0V (represented as uint * 10)
        self._bar.setValue(138)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)
        self._bar.setFixedWidth(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        lbl = QLabel("BATTERY")
        lbl.setStyleSheet("color: #6C7685; font-size: 10px; font-weight: 700;")
        layout.addWidget(lbl)
        layout.addWidget(self._bar)
        layout.addWidget(self._val_label)

        self.set_voltage(None, "unknown")

    def set_voltage(self, voltage: Optional[float], status: str = "unknown") -> None:
        if voltage is None:
            self._val_label.setText("-- V")
            self._bar.setValue(self._bar.minimum())
            self._val_label.setStyleSheet("color: #CBD5E1; font-weight: 700; font-size: 12px;")
            return
        self._val_label.setText(f"{voltage:.1f} V")
        int_val = int(min(max(voltage, 9.0), 16.0) * 10)
        self._bar.setValue(int_val)

        colors = ColorTokens()
        if status == "critical":
            bar_col = colors.danger_border
            txt_col = colors.danger_text
        elif status == "warning":
            bar_col = colors.warning_border
            txt_col = colors.warning_text
        else:
            bar_col = colors.success_text
            txt_col = colors.text_primary

        self._val_label.setStyleSheet(f"color: {txt_col}; font-weight: 700; font-size: 12px;")
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {colors.surface_control};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_col};
                border-radius: 2px;
            }}
        """)
