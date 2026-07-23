"""
Application Layer - Observable Application State Engine

Centralized observable application state using PySide6 signals.
Stores current vehicle, active ECU, connected hardware adapter, voltage level,
flash phase, and active workspace state across the application.
"""

import time
from typing import Optional, Any, Dict
from PySide6.QtCore import QObject, Signal


class ApplicationState(QObject):
    """Central observable state manager emitting PySide6 signals on state change."""

    adapter_changed = Signal(str, bool)  # adapter_name, is_connected
    ecu_changed = Signal(str, str)        # ecu_id, ecu_name
    vehicle_changed = Signal(str)         # vehicle_name
    voltage_changed = Signal(object, str)  # voltage (float|None), status_level
    phase_changed = Signal(str, int, str) # phase_name, progress_pct, details
    workspace_changed = Signal(int, str)  # workspace_index, workspace_name
    security_level_changed = Signal(str)  # level_str ("Locked", "Unlocked 0x01", etc)
    log_emitted = Signal(str, str, str)   # level, category, message

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._adapter_name = "None"
        self._is_connected = False
        self._ecu_id = "motronic961"
        self._ecu_name = "Bosch Motronic ME9.6.1"
        self._vehicle_name = "Saab 9-3 2.8T V6 / Opel Vectra C"
        self._voltage: Optional[float] = None
        self._voltage_status = "unknown"
        self._voltage_source = ""
        self._voltage_measured_at = 0.0
        self._current_phase = "Idle"
        self._phase_progress = 0
        self._active_workspace_idx = 0
        self._active_workspace_name = "Flashing"
        self._security_level = "Locked (0x00)"

    # Getters & Setters with Signal Notifications

    @property
    def adapter_name(self) -> str:
        return self._adapter_name

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def set_adapter_state(self, name: str, is_connected: bool) -> None:
        self._adapter_name = name
        self._is_connected = is_connected
        self.adapter_changed.emit(name, is_connected)
        self.log_info("Hardware", f"Adapter {name} state changed: Connected={is_connected}")

    @property
    def ecu_id(self) -> str:
        return self._ecu_id

    @property
    def ecu_name(self) -> str:
        return self._ecu_name

    def set_ecu(self, ecu_id: str, ecu_name: str) -> None:
        self._ecu_id = ecu_id
        self._ecu_name = ecu_name
        self.ecu_changed.emit(ecu_id, ecu_name)
        self.log_info("ECU", f"Active ECU set to: {ecu_name} [{ecu_id}]")

    @property
    def vehicle_name(self) -> str:
        return self._vehicle_name

    def set_vehicle(self, vehicle_name: str) -> None:
        self._vehicle_name = vehicle_name
        self.vehicle_changed.emit(vehicle_name)

    @property
    def voltage(self) -> Optional[float]:
        return self._voltage

    @property
    def voltage_status(self) -> str:
        return self._voltage_status

    @property
    def voltage_source(self) -> str:
        return self._voltage_source

    @property
    def voltage_measured_at(self) -> float:
        return self._voltage_measured_at

    def set_voltage(self, voltage: Optional[float], status: str, source: str = "") -> None:
        self._voltage = voltage
        self._voltage_status = status
        self._voltage_source = source
        self._voltage_measured_at = time.time() if voltage is not None else 0.0
        self.voltage_changed.emit(voltage, status)

    @property
    def current_phase(self) -> str:
        return self._current_phase

    @property
    def phase_progress(self) -> int:
        return self._phase_progress

    def set_phase(self, phase_name: str, progress: int, details: str = "") -> None:
        self._current_phase = phase_name
        self._phase_progress = progress
        self.phase_changed.emit(phase_name, progress, details)

    @property
    def active_workspace_idx(self) -> int:
        return self._active_workspace_idx

    @property
    def active_workspace_name(self) -> str:
        return self._active_workspace_name

    def set_workspace(self, idx: int, name: str) -> None:
        self._active_workspace_idx = idx
        self._active_workspace_name = name
        self.workspace_changed.emit(idx, name)

    @property
    def security_level(self) -> str:
        return self._security_level

    def set_security_level(self, level_str: str) -> None:
        self._security_level = level_str
        self.security_level_changed.emit(level_str)

    # Central Logging Helpers
    def log_info(self, category: str, message: str) -> None:
        self.log_emitted.emit("INFO", category, message)

    def log_warn(self, category: str, message: str) -> None:
        self.log_emitted.emit("WARN", category, message)

    def log_error(self, category: str, message: str) -> None:
        self.log_emitted.emit("ERROR", category, message)
