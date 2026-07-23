from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .base_step import BaseStep


ADAPTERS = [
    ("Simulator", "Offline ECU simulator", "mock"),
    ("Kvaser", "Kvaser CANlib", "kvaser"),
    ("J2534", "J2534 PassThru", "j2534"),
]


class StepAdapter(BaseStep):
    """Step 1: Select CAN adapter and connect."""

    adapter_selected = Signal(str)  # "kvaser" or "j2534"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._choice = None
        self._j2534_dll = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("Select CAN Adapter")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        subtitle = QLabel("Choose your CAN interface device")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._cards = {}

        for name, desc, key in ADAPTERS:
            btn = QPushButton(f"  {name}\n  {desc}")
            btn.setObjectName("cardBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            self._btn_group.addButton(btn)
            self._cards[key] = btn
            btn.clicked.connect(lambda checked, k=key: self._on_select(k))
            layout.addWidget(btn)

        # J2534 device selector (hidden until J2534 selected)
        self._j2534_label = QLabel("J2534 Device:")
        self._j2534_label.setObjectName("statusLabel")
        self._j2534_label.setVisible(False)
        layout.addWidget(self._j2534_label)

        self._j2534_combo = QComboBox()
        self._j2534_combo.setMinimumHeight(44)
        self._j2534_combo.setVisible(False)
        self._j2534_combo.currentIndexChanged.connect(self._on_j2534_device_change)
        layout.addWidget(self._j2534_combo)

        layout.addStretch()

    def _on_select(self, key: str):
        self._choice = key
        if key in self._cards:
            self._cards[key].setChecked(True)
        is_j2534 = key == "j2534"
        self._j2534_label.setVisible(is_j2534)
        self._j2534_combo.setVisible(is_j2534)

        if is_j2534:
            self._refresh_j2534_devices()
        else:
            self._j2534_dll = None

        self.adapter_selected.emit(key)
        self.next_enabled.emit(self._can_continue())

    def _refresh_j2534_devices(self):
        self._j2534_combo.clear()
        self._j2534_dll = None
        try:
            from adapters.j2534 import get_installed_j2534_devices
            devices = get_installed_j2534_devices()
            if devices:
                for dev in devices:
                    label = f"{dev['name']}"
                    self._j2534_combo.addItem(label, dev["dll"])
            else:
                self._j2534_combo.addItem("No devices found", None)
        except Exception:
            self._j2534_combo.addItem("Error scanning registry", None)

        self._on_j2534_device_change(self._j2534_combo.currentIndex())

    def _on_j2534_device_change(self, index=None):
        idx = self._j2534_combo.currentIndex()
        if idx >= 0:
            self._j2534_dll = self._j2534_combo.itemData(idx)
        else:
            self._j2534_dll = None
        if self._choice == "j2534":
            self.next_enabled.emit(self._j2534_dll is not None)

    def get_adapter_key(self) -> str:
        return self._choice or "mock"

    def get_j2534_dll(self):
        return self._j2534_dll

    def on_enter(self):
        self.next_enabled.emit(self._can_continue())

    def _can_continue(self) -> bool:
        return self._choice is not None and (
            self._choice != "j2534" or self._j2534_dll is not None
        )
