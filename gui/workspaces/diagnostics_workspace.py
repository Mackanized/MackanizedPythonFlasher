"""
Presentation Layer - UDS Diagnostics & CAN Trace Workspace

Diagnostics workspace featuring:
- Diagnostic Trouble Code (DTC) Read & Clear
- UDS Diagnostic Session Control (0x10)
- Security Access Authentication (0x27)
- Live High-Speed CAN Trace Panel with packet transmission
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout
)
from gui.components.can_trace_panel import CANTracePanel
from gui.components.oem_button import OEMButton


class DiagnosticsWorkspace(QFrame):
    """UDS & CAN Diagnostics Workspace Widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Left: DTC & UDS Service Actions
        dtc_group = QGroupBox("DTC Fault Memory Management")
        dtc_box = QVBoxLayout(dtc_group)

        dtc_btn_box = QHBoxLayout()
        self._btn_read_dtc = OEMButton("Read DTCs (0x19)", "primary")
        self._btn_clear_dtc = OEMButton("Clear DTCs (0x14)", "destructive")
        self._btn_read_dtc.setEnabled(False)
        self._btn_clear_dtc.setEnabled(False)
        self._btn_read_dtc.setToolTip("Unavailable until a trace-backed ECU diagnostic strategy is implemented.")
        self._btn_clear_dtc.setToolTip("Unavailable until a trace-backed ECU diagnostic strategy is implemented.")
        dtc_btn_box.addWidget(self._btn_read_dtc)
        dtc_btn_box.addWidget(self._btn_clear_dtc)
        dtc_box.addLayout(dtc_btn_box)

        self._dtc_table = QTableWidget(0, 3)
        self._dtc_table.setHorizontalHeaderLabels(["DTC Code", "Status", "Description"])
        self._dtc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._dtc_table.verticalHeader().setVisible(False)
        dtc_box.addWidget(self._dtc_table)

        # UDS Services Toolbar
        uds_group = QGroupBox("UDS Protocol Direct Commands")
        uds_box = QHBoxLayout(uds_group)
        btn_session = OEMButton("Session 0x10", "secondary")
        btn_sec = OEMButton("Security 0x27", "secondary")
        btn_reset = OEMButton("Reset 0x11", "secondary")
        for button in (btn_session, btn_sec, btn_reset):
            button.setEnabled(False)
            button.setToolTip("Direct diagnostic commands are not implemented in this workspace.")
        uds_box.addWidget(btn_session)
        uds_box.addWidget(btn_sec)
        uds_box.addWidget(btn_reset)

        left_layout = QVBoxLayout()
        left_layout.addWidget(dtc_group)
        left_layout.addWidget(uds_group)

        left_widget = QFrame()
        left_widget.setLayout(left_layout)

        # Right: CAN Trace Monitor
        self._can_panel = CANTracePanel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(self._can_panel)
        splitter.setSizes([420, 500])

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.addWidget(splitter)
