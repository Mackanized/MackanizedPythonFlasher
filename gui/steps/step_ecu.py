from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ecus import Motronic961, Motronic96, Trionic8, EDC16C39, EDC17C19
from .base_step import BaseStep


ECU_LIST = [
    (Motronic961, "Bosch ME9.6.1", "Saab 9-5 NG / GM Epsilon"),
    (Motronic96, "Bosch ME9.6", "Saab 9-3 SS / GM Epsilon"),
    (Trionic8, "Trionic 8", "Saab 9-3 B207 / B284"),
    (EDC16C39, "Bosch EDC16C39", "1.9 CDTI / Z19DTR"),
    (EDC17C19, "Bosch EDC17C19", "2.0 BiTurbo CDTI"),
]


class StepECU(BaseStep):
    """Step 2: Select target ECU."""

    ecu_selected = Signal(object)  # ECU class

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ecu_class = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("Select ECU")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        subtitle = QLabel("Choose the ECU you want to read or flash")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)
        self._cards = {}

        for ecu_cls, name, desc in ECU_LIST:
            btn = QPushButton(f"  {name}\n  {desc}")
            btn.setObjectName("cardBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            self._btn_group.addButton(btn)
            self._cards[ecu_cls] = btn
            btn.clicked.connect(lambda checked, c=ecu_cls: self._on_select(c))
            layout.addWidget(btn)

        layout.addStretch()

    def _on_select(self, ecu_class):
        self._ecu_class = ecu_class
        self.ecu_selected.emit(ecu_class)
        self.next_enabled.emit(True)

    def get_ecu_class(self):
        return self._ecu_class

    def on_enter(self):
        self.next_enabled.emit(self._ecu_class is not None)