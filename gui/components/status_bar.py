"""
Presentation Layer - High-Density Persistent Desktop Status Bar Component

Displays 13 persistent telemetry status items:
Vehicle | ECU | Session | Security | Voltage | CAN Bitrate | Bus Load % | TX/RX fps | CPU % | Memory MB | Adapter | Clock
"""

import time
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QStatusBar


class StationStatusBar(QStatusBar):
    """High-density 13-item desktop telemetry status bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setContentsMargins(8, 0, 8, 0)
        self.setFixedHeight(26)

        # 13 Telemetry Items
        self._lbl_veh = QLabel("Vehicle: Saab 9-3 2.8T")
        self._lbl_veh.setToolTip("Target Vehicle Platform")
        self._lbl_ecu = QLabel("ECU: ME9.6.1")
        self._lbl_ecu.setToolTip("Target Controller Family")
        self._lbl_session = QLabel("Session: Default")
        self._lbl_session.setToolTip("Active UDS / GMLAN Diagnostic Session Mode")
        self._lbl_sec = QLabel("Security: Locked (0x00)")
        self._lbl_sec.setToolTip("ECU SecurityAccess Seed-Key Lock Status")
        
        self._lbl_v = QLabel("⚡ -- V")
        self._lbl_v.setToolTip("Live Vehicle Battery Voltage (Normal ≥12.5V, Warning 11.8-12.4V, Critical <11.8V)")
        self._lbl_v.setStyleSheet("font-size: 11px; font-family: monospace; font-weight: 700; color: #6EE7B7; background-color: #064E3B; padding: 2px 6px; border-radius: 4px;")
        
        self._lbl_can = QLabel("CAN: 500k")
        self._lbl_can.setToolTip("High-Speed CAN Bus Baud Rate")
        self._lbl_load = QLabel("Load: 18.4%")
        self._lbl_load.setToolTip("Real-Time CAN Bus Channel Load Percentage")
        self._lbl_txrx = QLabel("TX: 182 fps | RX: 214 fps")
        self._lbl_txrx.setToolTip("Transmitted and Received Frames Per Second")
        self._lbl_cpu = QLabel("CPU: 3.2%")
        self._lbl_cpu.setToolTip("Application Process CPU Utilization")
        self._lbl_mem = QLabel("RAM: 142MB")
        self._lbl_mem.setToolTip("Resident Memory Allocation")
        self._lbl_adapter = QLabel("Adapter: MockAdapter")
        self._lbl_adapter.setToolTip("Active PassThru / CAN Hardware Bus Interface")
        self._lbl_clock = QLabel(time.strftime("%H:%M:%S"))

        items = [
            self._lbl_veh, self._lbl_ecu, self._lbl_session, self._lbl_sec,
            self._lbl_v, self._lbl_can, self._lbl_load, self._lbl_txrx,
            self._lbl_cpu, self._lbl_mem, self._lbl_adapter, self._lbl_clock
        ]

        for idx, item in enumerate(items):
            if item != self._lbl_v:
                item.setStyleSheet("font-size: 11px; font-family: monospace; color: #A0AAB8;")
            self.addPermanentWidget(item)
            if idx < len(items) - 1:
                sep = QLabel("|")
                sep.setStyleSheet("color: #3C4455; font-size: 11px;")
                self.addPermanentWidget(sep)

        # Clock Timer
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(lambda: self._lbl_clock.setText(time.strftime("%H:%M:%S")))
        self._timer.start()

    def update_telemetry(self, data: dict) -> None:
        v = data.get("voltage")
        v_stat = data.get("voltage_status", "unknown")
        self._lbl_v.setText(f"⚡ {v:.2f}V" if v is not None else "⚡ -- V")
        if v_stat == "critical":
            self._lbl_v.setStyleSheet("font-size: 11px; font-family: monospace; font-weight: 700; color: #FCA5A5; background-color: #7F1D1D; padding: 2px 6px; border-radius: 4px;")
        elif v_stat == "warning":
            self._lbl_v.setStyleSheet("font-size: 11px; font-family: monospace; font-weight: 700; color: #FDE68A; background-color: #78350F; padding: 2px 6px; border-radius: 4px;")
        elif v_stat == "normal":
            self._lbl_v.setStyleSheet("font-size: 11px; font-family: monospace; font-weight: 700; color: #6EE7B7; background-color: #064E3B; padding: 2px 6px; border-radius: 4px;")
        else:
            self._lbl_v.setStyleSheet("font-size: 11px; font-family: monospace; font-weight: 700; color: #CBD5E1; background-color: #334155; padding: 2px 6px; border-radius: 4px;")

        load = data.get("can_bus_load")
        tx_fps = data.get("tx_fps")
        rx_fps = data.get("rx_fps")
        self._lbl_load.setText("Load: Unknown" if load is None else f"Load: {load:.1f}%")
        tx_text = "Unknown" if tx_fps is None else f"{tx_fps} fps"
        rx_text = "Unknown" if rx_fps is None else f"{rx_fps} fps"
        self._lbl_txrx.setText(f"TX: {tx_text} | RX: {rx_text}")

        cpu = data.get("cpu_usage_pct")
        mem = data.get("memory_usage_mb")
        self._lbl_cpu.setText("CPU: Unknown" if cpu is None else f"CPU: {cpu:.1f}%")
        self._lbl_mem.setText("RAM: Unknown" if mem is None else f"RAM: {int(mem)}MB")

    def update_session(self, veh: str, ecu: str) -> None:
        self._lbl_veh.setText(f"Vehicle: {veh}")
        self._lbl_ecu.setText(f"ECU: {ecu}")

    def update_adapter(self, name: str, is_connected: bool) -> None:
        state = "Connected" if is_connected else "Disconnected"
        self._lbl_adapter.setText(f"Adapter: {name} [{state}]")

    def set_status_text(self, text: str) -> None:
        pass  # Preserves high-density telemetry layout
