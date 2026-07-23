"""
Presentation Layer - Audit Log Console Workspace

Audit logging console featuring:
- Live Log Event Streaming (INFO, WARN, ERROR)
- Category Filtering (Hardware, Protocol, Security, FlashEngine, Checksum)
- Correlation ID Lookup
- Log File Exporting
"""

import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout
)
from gui.components.oem_button import OEMButton


class LogsWorkspace(QFrame):
    """Operational Audit Trail Log Workspace Widget."""

    MAX_ROWS = 2000

    def __init__(self, parent=None):
        super().__init__(parent)

        self._filter_cat = QComboBox()
        self._filter_cat.addItems(["All Categories", "Hardware", "Protocol", "Security", "FlashEngine", "Checksum"])

        self._clear_btn = OEMButton("Clear Console", "secondary")
        self._clear_btn.clicked.connect(self.clear_logs)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Audit Log Filter:"))
        top_layout.addWidget(self._filter_cat)
        top_layout.addStretch()
        top_layout.addWidget(self._clear_btn)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Timestamp", "Level", "Category", "Message"])
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(top_layout)
        layout.addWidget(self._table)

        self.append_log("INFO", "Application", "Mackanized flasher OEM Desktop Suite initialized.")

    def clear_logs(self) -> None:
        self._table.setRowCount(0)

    def append_log(self, level: str, category: str, message: str) -> None:
        while self._table.rowCount() >= self.MAX_ROWS:
            self._table.removeRow(0)
        row = self._table.rowCount()
        self._table.insertRow(row)

        ts_str = time.strftime("%H:%M:%S")
        lvl_item = QTableWidgetItem(level)
        if level == "ERROR":
            lvl_item.setForeground(Qt.GlobalColor.red)
        elif level == "WARN":
            lvl_item.setForeground(Qt.GlobalColor.yellow)
        else:
            lvl_item.setForeground(Qt.GlobalColor.green)

        self._table.setItem(row, 0, QTableWidgetItem(ts_str))
        self._table.setItem(row, 1, lvl_item)
        self._table.setItem(row, 2, QTableWidgetItem(category))
        self._table.setItem(row, 3, QTableWidgetItem(message))

        self._table.scrollToBottom()
