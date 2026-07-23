"""
Presentation Layer - System Settings Workspace

Configuration workspace for:
- Theme Selection (Dark Theme, Light Theme, High-Contrast Workshop Mode)
- UI Density Mode (Compact, Standard, Comfortable)
- Hardware PassThru DLL Configuration
- Log Persistence Preferences
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QFrame, QGroupBox, QFormLayout, QLineEdit, QVBoxLayout
)
from gui.components.oem_button import OEMButton


class SettingsWorkspace(QFrame):
    """System Settings & Preferences Workspace Widget."""

    theme_changed = Signal(str)      # theme_name
    density_changed = Signal(str)    # density_name

    def __init__(self, parent=None):
        super().__init__(parent)

        # UI Appearance Group
        ui_group = QGroupBox("Interface & Visual Theme")
        ui_form = QFormLayout(ui_group)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Dark Theme (Default)", "High-Contrast Workshop Mode", "Light Theme"])
        self._theme_combo.currentIndexChanged.connect(self._on_theme_change)

        self._density_combo = QComboBox()
        self._density_combo.addItems(["Standard Density", "Compact Engineering", "Comfortable"])
        self._density_combo.currentIndexChanged.connect(self._on_density_change)

        ui_form.addRow("Visual Theme:", self._theme_combo)
        ui_form.addRow("UI Information Density:", self._density_combo)

        # Hardware PassThru Group
        hw_group = QGroupBox("J2534 PassThru Configuration")
        hw_form = QFormLayout(hw_group)

        self._j2534_dll_path = QLineEdit("/usr/local/lib/libj2534.dylib")
        self._j2534_browse = OEMButton("Browse DLL...", "secondary")

        hw_form.addRow("J2534 Driver DLL:", self._j2534_dll_path)
        hw_form.addRow("", self._j2534_browse)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(ui_group)
        layout.addWidget(hw_group)
        layout.addStretch()

    def _on_theme_change(self, idx: int) -> None:
        names = ["dark", "workshop", "light"]
        self.theme_changed.emit(names[idx])

    def _on_density_change(self, idx: int) -> None:
        modes = ["standard", "compact", "comfortable"]
        self.density_changed.emit(modes[idx])
