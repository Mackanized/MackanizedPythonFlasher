"""
Presentation Layer - Memory & Hex Calibration Workspace

Workspace for viewing ECU memory maps, hex binary inspection, checksum recalculation,
and memory sector write-protection verification.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout
)
from gui.components.hex_editor_view import HexEditorView
from gui.components.oem_button import OEMButton
from domain.memory_map import MemoryMap


class MemoryWorkspace(QFrame):
    """Memory & Calibration Inspection Workspace Widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Left: Memory Sector Map Grid
        sector_group = QGroupBox("ECU Flash Memory Sector Map")
        sec_box = QVBoxLayout(sector_group)

        self._sec_table = QTableWidget(0, 5)
        self._sec_table.setHorizontalHeaderLabels(["Sector", "Start Addr", "End Addr", "Size (KB)", "Attributes"])
        self._sec_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self._sec_table.verticalHeader().setVisible(False)
        sec_box.addWidget(self._sec_table)

        self._sec_table.setToolTip("Select an ECU definition to load its declared memory regions.")

        left_widget = QFrame()
        left_widget.setLayout(sec_box)

        # Right: Virtual Hex Editor
        self._hex_view = HexEditorView()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(self._hex_view)
        splitter.setSizes([380, 540])

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.addWidget(splitter)

    def set_memory_map(self, memory_map: MemoryMap) -> None:
        self._sec_table.setRowCount(len(memory_map.regions))
        for row, region in enumerate(memory_map.regions):
            attributes = "Protected" if region.is_protected else "Read / Write" if region.is_writable else "Read-Only"
            self._sec_table.setItem(row, 0, QTableWidgetItem(region.name))
            self._sec_table.setItem(row, 1, QTableWidgetItem(region.hex_start))
            self._sec_table.setItem(row, 2, QTableWidgetItem(region.hex_end))
            self._sec_table.setItem(row, 3, QTableWidgetItem(f"{region.size_kb:g} KB"))
            self._sec_table.setItem(row, 4, QTableWidgetItem(attributes))
