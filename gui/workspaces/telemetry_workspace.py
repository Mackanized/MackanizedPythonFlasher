"""
Presentation Layer - Live Telemetry & Performance Workspace

Workspace providing real-time hardware telemetry monitors:
- Battery Voltage (V) & Stability Graph
- Hardware Transfer Speed (KB/s)
- CAN Frame Rate (fps) & Bus Load (%)
- Host Workstation CPU & Memory Overhead
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QGroupBox, QGridLayout, QLabel, QVBoxLayout
)
from gui.components.voltage_meter import VoltageMeter


class TelemetryWorkspace(QFrame):
    """Real-Time Performance & Telemetry Workspace Widget."""

    def __init__(self, parent=None):
        super().__init__(parent)

        grid = QGridLayout()
        grid.setSpacing(16)

        # Card 1: Battery Health
        card_v = QGroupBox("Automotive Battery Health")
        box_v = QVBoxLayout(card_v)
        self._vm = VoltageMeter()
        self._v_desc = QLabel("Operational Safe Window: 12.4V – 14.5V\nProgramming is automatically inhibited if voltage drops below 11.4V.")
        self._v_desc.setStyleSheet("color: #A0AAB8; font-size: 11px;")
        box_v.addWidget(self._vm)
        box_v.addWidget(self._v_desc)
        grid.addWidget(card_v, 0, 0)

        # Card 2: CAN Throughput
        card_can = QGroupBox("CAN Bus Bandwidth & Throughput")
        box_can = QVBoxLayout(card_can)
        self._can_lbl = QLabel("Frame rate: Unknown\nBus utilization: Unknown\nSource: no adapter sample")
        self._can_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        box_can.addWidget(self._can_lbl)
        grid.addWidget(card_can, 0, 1)

        # Card 3: Transfer Speed
        card_speed = QGroupBox("Programming Transfer Rate")
        box_speed = QVBoxLayout(card_speed)
        self._speed_lbl = QLabel("Current rate: 0.0 KB/s\nSource: no active operation")
        self._speed_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        box_speed.addWidget(self._speed_lbl)
        grid.addWidget(card_speed, 1, 0)

        # Card 4: Host Workstation
        card_host = QGroupBox("Host System Overhead")
        box_host = QVBoxLayout(card_host)
        self._host_lbl = QLabel("Memory usage: Unknown\nCPU usage: Unknown")
        self._host_lbl.setStyleSheet("font-size: 12px; font-weight: 500;")
        box_host.addWidget(self._host_lbl)
        grid.addWidget(card_host, 1, 1)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.addLayout(grid)
        main_layout.addStretch()

    def update_telemetry(self, data: dict) -> None:
        v = data.get("voltage")
        v_stat = data.get("voltage_status", "unknown")
        self._vm.set_voltage(v, v_stat)

        fps = data.get("can_fps")
        load = data.get("can_bus_load")
        fps_text = "Unknown" if fps is None else f"{fps} fps"
        load_text = "Unknown" if load is None else f"{load:.1f}%"
        self._can_lbl.setText(f"Frame rate: {fps_text}\nBus utilization: {load_text}\nSource: {data.get('source', 'unavailable')}")

        rate = data.get("transfer_rate_kbs", 0.0)
        self._speed_lbl.setText(f"Current rate: {rate:.1f} KB/s\nSource: active operation progress")

        cpu = data.get("cpu_usage_pct")
        mem = data.get("memory_usage_mb")
        cpu_text = "Unknown" if cpu is None else f"{cpu:.1f}%"
        mem_text = "Unknown" if mem is None else f"{mem:.1f} MB"
        self._host_lbl.setText(f"Memory high-water mark: {mem_text}\nCPU usage: {cpu_text}")
