"""
Presentation Layer - Property Inspector Panel (Visual Studio 2022 Style)

Visual Studio 2022 Property Grid style displaying object properties, metadata, and parameters.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout
)
from ecus.registry import EcuRegistry


class InspectorPanel(QFrame):
    """Visual Studio 2022 Style Property Inspector Widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(240)
        self.setStyleSheet("background-color: #181818; border-left: 1px solid rgba(255, 255, 255, 0.04);")

        title = QLabel("PROPERTY INSPECTOR")
        title.setStyleSheet("font-size: 10px; font-weight: 700; color: #A0A0A0; padding: 4px 8px; letter-spacing: 0.5px;")

        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Property", "Value"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(2)
        layout.addWidget(title)
        layout.addWidget(self._table)

        self.inspect_ecu_by_idx(0)

    def inspect_ecu_by_idx(self, idx: int) -> None:
        registered = EcuRegistry.list_ecus()
        if 0 <= idx < len(registered):
            key, _name = registered[idx]
            ecu = EcuRegistry.instantiate(key)
            metadata = ecu.protocol_metadata
            props = [
                ("Target ECU", ecu.NAME),
                ("Definition Key", key),
                ("Live Identity", "Not read"),
                ("Protocol", metadata.family.value.upper()),
                ("Addressing", metadata.addressing.value),
                ("Request / Response", f"0x{metadata.request_can_id:03X} / 0x{metadata.response_can_id:03X}"),
                ("Flash Memory", f"{ecu.TOTAL_FLASH_SIZE // 1024} KB"),
                ("Development Status", ecu.CAPABILITIES.development_status),
            ]
            self._populate(props)

    def inspect_ecu(self, name: str, vehicle: str, hw_no: str, sw_no: str) -> None:
        props = [
            ("Target ECU", name),
            ("Vehicle Platform", vehicle),
            ("Hardware No.", hw_no),
            ("Software No.", sw_no),
            ("Source", "Live diagnostic response"),
        ]
        self._populate(props)

    def _populate(self, items) -> None:
        self._table.setRowCount(len(items))
        for row, (k, v) in enumerate(items):
            item_k = QTableWidgetItem(k)
            item_k.setForeground(Qt.GlobalColor.gray)
            item_v = QTableWidgetItem(v)
            item_v.setToolTip(v)
            self._table.setItem(row, 0, item_k)
            self._table.setItem(row, 1, item_v)
