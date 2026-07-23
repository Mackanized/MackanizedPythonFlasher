"""
Presentation Layer - High-Performance CAN Bus Trace Viewer Component

Provides high-frequency CAN packet rendering, message ID filtering, payload hex view,
packet transmit trigger, and log export.
"""

import time
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QVBoxLayout
)
from gui.components.oem_button import OEMButton


class CANTracePanel(QFrame):
    """CAN Bus Trace Table and Packet Injector Widget."""

    MAX_ROWS = 5000

    def __init__(self, parent=None):
        super().__init__(parent)

        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("Filter CAN ID (e.g. 0x7E8)...")

        self._pause_btn = OEMButton("Pause Trace", "toggle")
        self._clear_btn = OEMButton("Clear", "secondary")
        self._clear_btn.clicked.connect(self.clear_trace)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("CAN Bus Monitor"))
        top_layout.addStretch()
        top_layout.addWidget(self._filter_input)
        top_layout.addWidget(self._pause_btn)
        top_layout.addWidget(self._clear_btn)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(["Timestamp", "Dir", "CAN ID", "Type", "DLC", "Data Payload"])
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Transmit bar
        self._tx_id = QLineEdit("0x7E0")
        self._tx_id.setFixedWidth(80)
        self._tx_data = QLineEdit("02 10 03 00 00 00 00 00")
        self._send_btn = OEMButton("Transmit Frame", "primary")
        self._send_btn.setEnabled(False)
        self._send_btn.setToolTip("Raw transmission is disabled until routed through the adapter transaction service.")

        tx_layout = QHBoxLayout()
        tx_layout.addWidget(QLabel("TX ID:"))
        tx_layout.addWidget(self._tx_id)
        tx_layout.addWidget(QLabel("Data (Hex):"))
        tx_layout.addWidget(self._tx_data)
        tx_layout.addWidget(self._send_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        layout.addLayout(top_layout)
        layout.addWidget(self._table)
        layout.addLayout(tx_layout)


    def clear_trace(self) -> None:
        self._table.setRowCount(0)

    def append_frame(self, direction: str, can_id: int, data: bytes) -> None:
        if self._pause_btn.isChecked():
            return

        while self._table.rowCount() >= self.MAX_ROWS:
            self._table.removeRow(0)
        row = self._table.rowCount()
        self._table.insertRow(row)

        ts_str = f"{time.time():.3f}"
        dir_item = QTableWidgetItem(direction)
        dir_item.setForeground(Qt.GlobalColor.green if direction == "TX" else Qt.GlobalColor.cyan)

        id_item = QTableWidgetItem(f"0x{can_id:03X}")
        type_item = QTableWidgetItem("STD")
        dlc_item = QTableWidgetItem(str(len(data)))
        hex_str = " ".join([f"{b:02X}" for b in data])
        data_item = QTableWidgetItem(hex_str)
        data_item.setFont(self.font())

        self._table.setItem(row, 0, QTableWidgetItem(ts_str))
        self._table.setItem(row, 1, dir_item)
        self._table.setItem(row, 2, id_item)
        self._table.setItem(row, 3, type_item)
        self._table.setItem(row, 4, dlc_item)
        self._table.setItem(row, 5, data_item)

        # Auto-scroll
        self._table.scrollToBottom()
