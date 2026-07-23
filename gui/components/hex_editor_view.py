"""
Presentation Layer - Virtualized Hex Memory Viewer Component

High-density binary hex viewer displaying:
- Address Offsets (0x00000000 - 0x001FFFFF)
- 16-byte Hex Columns
- ASCII Character Map Preview
- Checksum highlight overlay
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel, QTableWidget,
    QTableWidgetItem, QVBoxLayout
)
from gui.components.oem_button import OEMButton


class HexEditorView(QFrame):
    """Hexadecimal Memory Matrix Viewer Widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._hdr_label = QLabel("FLASH MEMORY MAP (0x00000000 - 0x001FFFFF)")
        self._hdr_label.setObjectName("sectionTitle")

        self._calc_btn = OEMButton("Verify Checksum", "secondary")

        top_layout = QHBoxLayout()
        top_layout.addWidget(self._hdr_label)
        top_layout.addStretch()
        top_layout.addWidget(self._calc_btn)

        cols = ["Address"] + [f"{i:02X}" for i in range(16)] + ["ASCII"]
        self._table = QTableWidget(0, 18)
        self._table.setHorizontalHeaderLabels(cols)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(17, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)

        font = QFont("JetBrains Mono", 10)
        font.setStyleHint(QFont.Monospace)
        self._table.setFont(font)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(top_layout)
        layout.addWidget(self._table)

        self.load_binary_data(b"\x7F" * 512)

    def load_binary_data(self, data: bytes) -> None:
        self._table.setRowCount(0)
        num_rows = min(32, (len(data) + 15) // 16)
        self._table.setRowCount(num_rows)

        for row in range(num_rows):
            offset = row * 16
            chunk = data[offset:offset+16]

            # Address item
            addr_item = QTableWidgetItem(f"0x{offset:08X}")
            addr_item.setForeground(Qt.GlobalColor.cyan)
            self._table.setItem(row, 0, addr_item)

            # 16 Hex bytes
            ascii_chars = []
            for col in range(16):
                if col < len(chunk):
                    val = chunk[col]
                    b_item = QTableWidgetItem(f"{val:02X}")
                    ascii_chars.append(chr(val) if 32 <= val <= 126 else ".")
                else:
                    b_item = QTableWidgetItem("  ")
                    ascii_chars.append(" ")
                self._table.setItem(row, col + 1, b_item)

            # ASCII string item
            ascii_item = QTableWidgetItem("".join(ascii_chars))
            ascii_item.setForeground(Qt.GlobalColor.yellow)
            self._table.setItem(row, 17, ascii_item)
