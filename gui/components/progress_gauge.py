"""
Presentation Layer - Multi-Stage Progress Gauge Component

Displays high-resolution operation progress with phase breakdown:
- Phase Timeline (Prepare -> Unlock -> Erase -> Write -> Verify -> Complete)
- Progress Bar with Percentage
- Transfer Speed (KB/s) & Estimated Time Remaining (ETA)
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QVBoxLayout
)
from gui.design_system.tokens import ColorTokens


class ProgressGauge(QFrame):
    """Multi-stage progress gauge widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._phase_label = QLabel("Phase: Ready")
        self._phase_label.setStyleSheet("font-weight: 600; font-size: 13px;")

        self._details_label = QLabel("No active transfer")
        self._details_label.setStyleSheet("color: #A0AAB8; font-size: 11px;")

        self._speed_label = QLabel("0.0 KB/s")
        self._speed_label.setStyleSheet("font-weight: 700; color: #007ACC; font-size: 12px;")

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(18)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header row
        hdr_layout = QHBoxLayout()
        hdr_layout.addWidget(self._phase_label)
        hdr_layout.addStretch()
        hdr_layout.addWidget(self._speed_label)
        layout.addLayout(hdr_layout)

        # Progress bar
        layout.addWidget(self._bar)

        # Footer row
        layout.addWidget(self._details_label)

    def set_progress(self, percent: int, speed_kbs: float = 0.0, details: str = "") -> None:
        self._bar.setValue(percent)
        self._speed_label.setText(f"{speed_kbs:.1f} KB/s" if speed_kbs > 0 else "")
        if details:
            self._details_label.setText(details)

    def set_phase(self, phase_name: str) -> None:
        self._phase_label.setText(f"Phase: {phase_name}")
