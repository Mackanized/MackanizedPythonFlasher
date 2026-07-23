"""
Presentation Layer - Workflow-First ECU Programming Workstation
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QHeaderView, QLabel, QRadioButton, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout
)
from gui.components.oem_button import OEMButton
from gui.components.progress_gauge import ProgressGauge
from ecus.registry import EcuRegistry


class FlashWorkspace(QFrame):
    """Workflow-First ECU Programming Workspace Widget."""

    read_clicked = Signal(str)            # region_name
    write_clicked = Signal(str, str, bool)  # file_path, region_name, backup_verified
    info_clicked = Signal()
    adapter_changed = Signal(str)
    ecu_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #181A20;")
        self._selected_file_path = ""

        # ── 1. Operator Guidance Banner ───────────────────────────────
        guide_card = QFrame()
        guide_card.setStyleSheet("background-color: #20232B; border: none; border-radius: 8px;")
        guide_layout = QVBoxLayout(guide_card)
        guide_layout.setContentsMargins(16, 12, 16, 12)
        guide_layout.setSpacing(6)

        title_lbl = QLabel("⚡ ECU Programming & Memory Backup Workspace")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #F1F5F9;")

        self._hint_lbl = QLabel("💡 Recommended Next Step: Select your calibration file below, then click 'Read ECU Flash' to create a safety backup before programming.")
        self._hint_lbl.setStyleSheet("font-size: 12px; color: #3B82F6; font-weight: 500;")

        guide_layout.addWidget(title_lbl)
        guide_layout.addWidget(self._hint_lbl)

        # ── 2. Workflow Phase Timeline Stepper ────────────────────────
        flow_frame = QFrame()
        flow_frame.setStyleSheet("background-color: #20232B; border: none; border-radius: 8px;")
        flow_layout = QHBoxLayout(flow_frame)
        flow_layout.setContentsMargins(12, 8, 12, 8)
        flow_layout.setSpacing(6)

        self._pipeline_nodes = [
            "1. Connect", "2. Identify", "3. Validate", "4. Read",
            "5. Modify", "6. Verify", "7. Flash", "8. Reset", "9. Complete"
        ]
        self._node_labels = []

        for idx, step_name in enumerate(self._pipeline_nodes):
            lbl = QLabel(step_name)
            lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; padding: 3px 8px; border-radius: 4px;")
            flow_layout.addWidget(lbl)
            self._node_labels.append(lbl)

            if idx < len(self._pipeline_nodes) - 1:
                arr = QLabel("›")
                arr.setStyleSheet("color: #475569; font-weight: bold;")
                flow_layout.addWidget(arr)

        flow_layout.addStretch()

        # ── 3. Middle Splitter: Configuration & Progress Gauge ─────────
        cfg_card = QFrame()
        cfg_card.setStyleSheet("background-color: #20232B; border: none; border-radius: 8px;")
        cfg_grid = QGridLayout(cfg_card)
        cfg_grid.setContentsMargins(16, 12, 16, 12)
        cfg_grid.setSpacing(8)

        cfg_grid.addWidget(QLabel("Hardware Adapter:"), 0, 0)
        self._adapter_combo = QComboBox()
        self._adapter_combo.addItems(["MockAdapter (Offline Simulator)", "Kvaser CAN (CANlib)", "J2534 PassThru (DLL)"])
        self._adapter_combo.currentIndexChanged.connect(
            lambda idx: self.adapter_changed.emit(("mock", "kvaser", "j2534")[idx])
        )
        cfg_grid.addWidget(self._adapter_combo, 0, 1)

        cfg_grid.addWidget(QLabel("Target ECU Definition:"), 1, 0)
        self._ecu_combo = QComboBox()
        for ecu_key, ecu_name in EcuRegistry.list_ecus():
            self._ecu_combo.addItem(ecu_name, ecu_key)
        self._ecu_combo.currentIndexChanged.connect(
            lambda idx: self.ecu_changed.emit(str(self._ecu_combo.itemData(idx)))
        )
        cfg_grid.addWidget(self._ecu_combo, 1, 1)

        cfg_grid.addWidget(QLabel("Memory Target Region:"), 2, 0)
        reg_box = QHBoxLayout()
        self._radio_full = QRadioButton("Full Flash (2048 KB)")
        self._radio_cal = QRadioButton("Calibration (512 KB)")
        self._radio_eeprom = QRadioButton("EEPROM (2 KB)")
        self._radio_full.setChecked(True)
        reg_box.addWidget(self._radio_full)
        reg_box.addWidget(self._radio_cal)
        reg_box.addWidget(self._radio_eeprom)
        cfg_grid.addLayout(reg_box, 2, 1)

        cfg_grid.addWidget(QLabel("Calibration Source File:"), 3, 0)
        file_box = QHBoxLayout()
        self._file_lbl = QLabel("No file selected (*.bin only)")
        self._file_lbl.setStyleSheet("color: #94A3B8;")
        self._browse_btn = OEMButton("Browse...", "secondary")
        self._browse_btn.clicked.connect(self._on_browse)
        file_box.addWidget(self._file_lbl, stretch=1)
        file_box.addWidget(self._browse_btn)
        cfg_grid.addLayout(file_box, 3, 1)

        cfg_grid.addWidget(QLabel("Backup Verification:"), 4, 0)
        self._backup_verified = QCheckBox("I have verified a readable backup for this ECU before writing")
        self._backup_verified.setStyleSheet("font-size: 12px; color: #E2E8F0;")
        self._backup_verified.stateChanged.connect(self._refresh_write_enablement)
        cfg_grid.addWidget(self._backup_verified, 4, 1)

        # Right Operation Controls & Progress Gauge Card
        op_card = QFrame()
        op_card.setStyleSheet("background-color: #20232B; border: none; border-radius: 8px;")
        op_box = QVBoxLayout(op_card)
        op_box.setContentsMargins(16, 12, 16, 12)
        op_box.setSpacing(8)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(8)
        self._btn_info = OEMButton("Read ECU Info", "secondary")
        self._btn_info.clicked.connect(self.info_clicked.emit)

        self._btn_read = OEMButton("Read ECU Flash", "secondary")
        self._btn_read.clicked.connect(self._on_read)

        self._btn_write = OEMButton("Write Flash Memory", "warning")
        self._btn_write.clicked.connect(self._on_write)
        self._btn_write.setToolTip("Select a firmware file and confirm backup verification before writing.")

        btn_box.addWidget(self._btn_info)
        btn_box.addWidget(self._btn_read)
        btn_box.addWidget(self._btn_write)
        op_box.addLayout(btn_box)

        self._gauge = ProgressGauge()
        op_box.addWidget(self._gauge)

        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.addWidget(cfg_card)
        top_splitter.addWidget(op_card)
        top_splitter.setSizes([480, 520])

        # ── 4. Bottom Splitter: Address Tracker & Sector Matrix ───────
        tracker_card = QFrame()
        tracker_card.setStyleSheet("background-color: #20232B; border: none; border-radius: 8px;")
        tracker_grid = QGridLayout(tracker_card)
        tracker_grid.setContentsMargins(16, 12, 16, 12)
        tracker_grid.setSpacing(8)

        self._lbl_curr_addr = QLabel("Current Address: 0x00000000")
        self._lbl_curr_block = QLabel("Block Index: #0 / 512")
        self._lbl_bytes_written = QLabel("Bytes Processed: 0 B")
        self._lbl_elapsed = QLabel("Elapsed Time: 00:00")
        self._lbl_remaining = QLabel("ETA: --:--")
        self._lbl_crc = QLabel("Live CRC32: 0x00000000")

        for lbl in [self._lbl_curr_addr, self._lbl_curr_block, self._lbl_bytes_written,
                    self._lbl_elapsed, self._lbl_remaining, self._lbl_crc]:
            lbl.setStyleSheet("font-family: monospace; font-size: 11px; font-weight: 600; color: #F1F5F9;")

        tracker_grid.addWidget(self._lbl_curr_addr, 0, 0)
        tracker_grid.addWidget(self._lbl_curr_block, 0, 1)
        tracker_grid.addWidget(self._lbl_bytes_written, 1, 0)
        tracker_grid.addWidget(self._lbl_elapsed, 1, 1)
        tracker_grid.addWidget(self._lbl_remaining, 2, 0)
        tracker_grid.addWidget(self._lbl_crc, 2, 1)

        sec_card = QFrame()
        sec_card.setStyleSheet("background-color: #20232B; border: none; border-radius: 8px;")
        sec_box = QVBoxLayout(sec_card)
        sec_box.setContentsMargins(8, 8, 8, 8)

        self._sec_table = QTableWidget(0, 5)
        self._sec_table.setHorizontalHeaderLabels(["Sector", "Range", "Size", "State", "Verification CRC"])
        for col_idx in range(4):
            self._sec_table.horizontalHeader().setSectionResizeMode(col_idx, QHeaderView.ResizeToContents)
        self._sec_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._sec_table.verticalHeader().setVisible(False)
        sec_box.addWidget(self._sec_table)
        self._populate_sector_matrix({})

        bottom_splitter = QSplitter(Qt.Horizontal)
        bottom_splitter.addWidget(tracker_card)
        bottom_splitter.addWidget(sec_card)
        bottom_splitter.setSizes([360, 640])

        # Main Layout Assembly
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        main_layout.addWidget(guide_card)
        main_layout.addWidget(flow_frame)
        main_layout.addWidget(top_splitter)
        main_layout.addWidget(bottom_splitter, stretch=1)

        self.set_active_pipeline_step(0)
        self._refresh_write_enablement()

    def set_active_pipeline_step(self, step_idx: int) -> None:
        for idx, lbl in enumerate(self._node_labels):
            step_name = self._pipeline_nodes[idx]
            if idx == step_idx:
                lbl.setText(f"▶ {step_name}")
                lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #FFFFFF; background-color: #2563EB; padding: 3px 8px; border-radius: 4px;")
            elif idx < step_idx:
                lbl.setText(f"✓ {step_name}")
                lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #6EE7B7; background-color: #064E3B; padding: 3px 8px; border-radius: 4px;")
            else:
                lbl.setText(step_name)
                lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B; padding: 3px 8px; border-radius: 4px;")

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Raw Binary Calibration", "", "Raw Binary Files (*.bin)"
        )
        if path:
            self._selected_file_path = path
            self._file_lbl.setText(path.split("/")[-1])
            self._file_lbl.setStyleSheet("color: #F1F5F9; font-weight: 600;")
            self._refresh_write_enablement()

    def _on_read(self) -> None:
        region = "calibration" if self._radio_cal.isChecked() else ("eeprom" if self._radio_eeprom.isChecked() else "full")
        self.read_clicked.emit(region)

    def _on_write(self) -> None:
        region = "calibration" if self._radio_cal.isChecked() else ("eeprom" if self._radio_eeprom.isChecked() else "full")
        self.write_clicked.emit(self._selected_file_path, region, self._backup_verified.isChecked())

    def _refresh_write_enablement(self) -> None:
        if hasattr(self, "_btn_write"):
            self._btn_write.setEnabled(bool(self._selected_file_path) and self._backup_verified.isChecked())

    def update_progress(self, pct: int, speed: float, details: str) -> None:
        self._gauge.set_progress(pct, speed, details)
        self._lbl_curr_addr.setText("Current Address: reported in operation details")
        self._lbl_curr_block.setText("Block Index: reported by protocol engine")
        self._lbl_bytes_written.setText(f"Confirmed Progress: {pct}%")

    def update_phase(self, phase_name: str) -> None:
        self._gauge.set_phase(phase_name)
        if "Connect" in phase_name:
            self.set_active_pipeline_step(0)
        elif "Ident" in phase_name:
            self.set_active_pipeline_step(1)
        elif "Security" in phase_name:
            self.set_active_pipeline_step(2)
        elif "Reading" in phase_name:
            self.set_active_pipeline_step(3)
        elif "Erase" in phase_name:
            self.set_active_pipeline_step(5)
        elif "Program" in phase_name or "Write" in phase_name:
            self.set_active_pipeline_step(6)
        elif "Verify" in phase_name:
            self.set_active_pipeline_step(7)

    def _populate_sector_matrix(self, regions) -> None:
        self._sec_table.setRowCount(len(regions))
        for row, (name, (start, end, _filename)) in enumerate(regions.items()):
            self._sec_table.setItem(row, 0, QTableWidgetItem(name))
            self._sec_table.setItem(row, 1, QTableWidgetItem(f"0x{start:06X} - 0x{end:06X}"))
            self._sec_table.setItem(row, 2, QTableWidgetItem(f"{(end - start) / 1024:.1f} KB"))
            self._sec_table.setItem(row, 3, QTableWidgetItem("Declared read region"))
            self._sec_table.setItem(row, 4, QTableWidgetItem("Not measured"))

    def configure_ecu(self, ecu, simulation: bool) -> None:
        regions = ecu.get_flash_regions()
        for name, radio in (
            ("full", self._radio_full),
            ("calibration", self._radio_cal),
            ("eeprom", self._radio_eeprom),
        ):
            radio.setVisible(name in regions)
            radio.setEnabled(name in regions)
            if name in regions:
                start, end, _ = regions[name]
                radio.setText(f"{name.title()} ({(end - start) / 1024:.1f} KB)")
        if not any(radio.isChecked() and radio.isEnabled() for radio in (
            self._radio_full, self._radio_cal, self._radio_eeprom
        )):
            for radio in (self._radio_full, self._radio_cal, self._radio_eeprom):
                if radio.isEnabled():
                    radio.setChecked(True)
                    break
        self._populate_sector_matrix(regions)

    def set_selection_enabled(self, enabled: bool) -> None:
        self._adapter_combo.setEnabled(enabled)
        self._ecu_combo.setEnabled(enabled)
