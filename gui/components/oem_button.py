"""
Presentation Layer - OEM Custom Button Component

Standardized button component adhering to design system rules:
Variants: Primary, Secondary, Destructive, Icon, Toggle
Supports accessibility focus rings, tooltips, and state styling.
"""

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import QPushButton
from gui.design_system.tokens import ColorTokens


class OEMButton(QPushButton):
    """Production OEM desktop button widget."""

    def __init__(
        self,
        text: str = "",
        variant: str = "secondary",  # "primary", "secondary", "destructive", "toggle"
        icon_name: str = "",
        parent=None
    ):
        super().__init__(text, parent)
        self.variant = variant
        self._setup_variant()

    def _setup_variant(self) -> None:
        self.setFocusPolicy(Qt.TabFocus)
        self.setCursor(Qt.PointingHandCursor)

        if self.variant == "primary":
            self.setObjectName("primaryBtn")
            self.setMinimumHeight(32)
        elif self.variant == "warning":
            self.setObjectName("warningBtn")
            self.setMinimumHeight(32)
        elif self.variant == "destructive":
            self.setObjectName("dangerBtn")
            self.setMinimumHeight(32)
        elif self.variant == "toggle":
            self.setCheckable(True)
            self.setMinimumHeight(28)
        else:
            self.setMinimumHeight(28)

    def set_busy_state(self, busy: bool, busy_text: str = "Processing...") -> None:
        if busy:
            self.setEnabled(False)
            self.setText(busy_text)
        else:
            self.setEnabled(True)
