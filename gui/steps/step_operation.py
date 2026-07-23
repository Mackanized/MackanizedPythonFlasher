from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .base_step import BaseStep


class StepOperation(BaseStep):
    """Step 3: Select operation (Read / Write / Info) and region/file."""

    operation_ready = Signal(str, str, str)  # operation, region, filename

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ecu = None
        self._operation = None
        self._region = None
        self._filename = ""
        self._setup_ui()

    def set_ecu(self, ecu):
        self._ecu = ecu
        self._refresh_regions()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("Select Operation")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        subtitle = QLabel("Choose what you want to do with the ECU")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        layout.addSpacing(12)

        self._btn_group = QButtonGroup(self)
        self._btn_group.setExclusive(True)

        ops = [
            ("Read ECU", "Read flash data from the ECU to a file", "read"),
            ("Write ECU", "Write a flash file to the ECU", "write"),
            ("ECU Info", "Read ECU identification data", "info"),
        ]

        for name, desc, key in ops:
            btn = QPushButton(f"  {name}\n  {desc}")
            btn.setObjectName("cardBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            self._btn_group.addButton(btn)
            btn.clicked.connect(lambda checked, k=key: self._on_op_select(k))
            layout.addWidget(btn)

        layout.addSpacing(12)

        # Region selector
        self._region_label = QLabel("Region:")
        self._region_label.setObjectName("statusLabel")
        layout.addWidget(self._region_label)

        self._region_combo = QComboBox()
        self._region_combo.setMinimumHeight(44)
        self._region_combo.currentTextChanged.connect(self._on_region_change)
        layout.addWidget(self._region_combo)

        # File picker (for write)
        self._file_label = QLabel("File:")
        self._file_label.setObjectName("statusLabel")
        self._file_label.setVisible(False)
        layout.addWidget(self._file_label)

        file_row = QHBoxLayout()
        self._file_edit = QLineEdit()
        self._file_edit.setMinimumHeight(40)
        self._file_edit.setVisible(False)
        self._file_edit.textChanged.connect(lambda _text: self._validate())
        file_row.addWidget(self._file_edit)

        self._browse_btn = QPushButton("Browse")
        self._browse_btn.setMinimumHeight(40)
        self._browse_btn.clicked.connect(self._browse_file)
        self._browse_btn.setVisible(False)
        file_row.addWidget(self._browse_btn)
        layout.addLayout(file_row)

        self._backup_verified = QCheckBox("Verified backup exists for this ECU before writing")
        self._backup_verified.setVisible(False)
        self._backup_verified.stateChanged.connect(lambda _state: self._validate())
        layout.addWidget(self._backup_verified)

        layout.addStretch()

    def _on_op_select(self, key: str):
        self._operation = key
        is_write = key == "write"
        self._file_label.setVisible(is_write)
        self._file_edit.setVisible(is_write)
        self._browse_btn.setVisible(is_write)
        self._backup_verified.setVisible(is_write)
        self._region_label.setVisible(key != "info")
        self._region_combo.setVisible(key != "info")
        self._validate()

    def _refresh_regions(self):
        self._region_combo.clear()
        if not self._ecu:
            return
        if self._operation == "write":
            regions = self._ecu.get_write_regions()
        else:
            regions = self._ecu.get_flash_regions()
        for name, (start, end, default_file) in regions.items():
            size_kb = (end - start) // 1024
            label = f"{name} (0x{start:06X} - 0x{end:06X}, {size_kb} KB)"
            self._region_combo.addItem(label, name)
            if self._region is None:
                self._region = name
        self._region_combo.setCurrentIndex(0)

    def _on_region_change(self):
        idx = self._region_combo.currentIndex()
        if idx >= 0:
            self._region = self._region_combo.itemData(idx)
        self._validate()

    def _browse_file(self):
        if not self._ecu:
            return
        regions = self._ecu.get_write_regions()
        if self._region in regions:
            _, _, default_file = regions[self._region]
        else:
            default_file = ""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select flash file", ".", "Binary files (*.bin);;All files (*.*)"
        )
        if filename:
            self._file_edit.setText(filename)
            self._validate()

    def _validate(self):
        ok = self._operation is not None
        if ok and self._operation == "write":
            ok = bool(self._file_edit.text().strip()) and self._backup_verified.isChecked()
        self.next_enabled.emit(ok)

    def get_operation(self) -> str:
        return self._operation

    def get_region(self) -> str:
        return self._region or ""

    def get_filename(self) -> str:
        return self._file_edit.text().strip()

    def is_backup_verified(self) -> bool:
        return self._backup_verified.isChecked()

    def on_enter(self):
        if self._ecu:
            self._refresh_regions()
        self._validate()
