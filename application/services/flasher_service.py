"""Qt signal facade over the UI-independent :mod:`flasher_runtime` service."""

import os
import threading
import uuid
from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, Signal
from application.state.app_state import ApplicationState
from application.workers.flash_worker import AsyncFlashWorker
from adapters.base_adapter import BaseAdapter
from application.ports.adapter_factory import AdapterFactory
from application.services.flasher_runtime import FlasherRuntime
from ecus.base_ecu import BaseECU
from flasher import ECUFlasher
from application.validation.programming_preflight import ProgrammingRequest, VoltageEvidence
from domain.clock import Clock, SystemClock


class FlasherService(QObject):
    """Presentation adapter that maps runtime/worker events to Qt signals."""

    operation_started = Signal(str)            # op_type ("read", "write", "info")
    operation_progress = Signal(int, float, str)
    operation_phase = Signal(str)
    operation_completed = Signal(bool, str)

    def __init__(
        self,
        state: ApplicationState,
        parent=None,
        *,
        adapter_factory: Optional[AdapterFactory] = None,
        initial_ecu: Optional[BaseECU] = None,
        clock: Optional[Clock] = None,
    ):
        super().__init__(parent)
        if adapter_factory is None:
            from infrastructure.adapter_factory import DefaultAdapterFactory
            adapter_factory = DefaultAdapterFactory()
        if initial_ecu is None:
            from ecus.motronic961 import Motronic961
            initial_ecu = Motronic961()
        self._state = state
        self._clock = clock or SystemClock()
        self._runtime = FlasherRuntime(adapter_factory, initial_ecu)
        self.disable_preflight: bool = False
        self._active_worker: Optional[AsyncFlashWorker] = None
        self._pending_completion = None
        self._status_lock = threading.RLock()
        self._operation_status: Dict[str, Any] = self._idle_status()

    @property
    def adapter(self) -> BaseAdapter:
        return self._runtime.adapter

    @property
    def ecu(self) -> BaseECU:
        return self._runtime.ecu

    @property
    def is_connected(self) -> bool:
        return bool(
            self.adapter
            and self._state.is_connected
            and self._runtime.is_connected
        )

    @property
    def adapter_key(self) -> str:
        return self._runtime.adapter_key

    @property
    def operation_active(self) -> bool:
        return self._operation_is_active()

    # Compatibility aliases for older in-process integrations. New code must
    # use the public adapter/ECU properties and factory injection.
    @property
    def _active_adapter(self) -> BaseAdapter:
        return self._runtime.adapter

    @_active_adapter.setter
    def _active_adapter(self, adapter: BaseAdapter) -> None:
        self._runtime.adapter = adapter

    @property
    def _active_adapter_key(self) -> str:
        return self._runtime.adapter_key

    @_active_adapter_key.setter
    def _active_adapter_key(self, key: str) -> None:
        self._runtime.adapter_key = key

    def set_adapter(self, adapter_key: str, dll_path: str = "") -> bool:
        if self._operation_is_active():
            self._state.log_error("Hardware", "Cannot replace adapter during an active operation.")
            return False
        try:
            adapter_key = adapter_key.lower().strip()
            self._runtime.replace_adapter(adapter_key, dll_path)
            self._state.set_adapter_state(adapter_key.upper(), False)
            return True
        except (ValueError, OSError, RuntimeError) as e:
            self._state.log_error("Hardware", f"Failed to instantiate adapter {adapter_key}: {str(e)}")
            return False

    def connect_adapter(self) -> bool:
        if self._operation_is_active():
            self._state.log_error("Hardware", "Cannot connect adapter during an active operation.")
            return False
        try:
            res = self._runtime.connect()
            self._state.set_adapter_state(self.adapter_key.upper(), res)
            return res
        except (OSError, RuntimeError) as e:
            self._state.log_error("Hardware", f"Connection exception: {str(e)}")
            self._state.set_adapter_state(self._state.adapter_name, False)
            return False

    def disconnect_adapter(self) -> bool:
        if self._operation_is_active():
            self._state.log_error("Hardware", "Cannot disconnect while an ECU operation is active.")
            return False
        try:
            self._runtime.disconnect()
        except (OSError, RuntimeError) as exc:
            self._state.log_error("Hardware", f"Disconnect failed: {exc}")
            return False
        self._state.set_adapter_state(self.adapter_key.upper(), False)
        return True

    def set_ecu(self, ecu: BaseECU, ecu_id: str) -> bool:
        if self._operation_is_active():
            self._state.log_error("ECU", "Cannot change ECU during an active operation.")
            return False
        self._runtime.select_ecu(ecu)
        self._state.set_ecu(ecu_id, ecu.NAME)
        return True

    def read_connected_ecu_info(self) -> Dict[str, str]:
        """Read live identifiers without taking ownership of the open adapter."""
        if not self.is_connected:
            raise RuntimeError("Connect to the ECU before reading identification.")
        if self._operation_is_active():
            raise RuntimeError("Cannot identify ECU while another operation is active.")
        flasher = ECUFlasher(self.adapter, self.ecu)
        if not flasher.connect():
            raise RuntimeError("Connected adapter became unavailable.")
        return flasher.read_ecu_info()

    def start_read_operation(self, region_name: str = "full") -> bool:
        if not self._can_start_operation("read"):
            return False
        if not self.adapter.is_simulation:
            read_capability = (
                self.ecu.CAPABILITIES.supports_full_read
                if region_name == "full"
                else self.ecu.CAPABILITIES.supports_calibration_read
            )
            if not read_capability:
                self._state.log_error("Safety", f"Read capability is not verified for region: {region_name}")
                return False
        if region_name not in self.ecu.get_flash_regions():
            self._state.log_error("Validation", f"Unsupported read region: {region_name}")
            return False

        operation_id = self._begin_status("read", f"Preparing read ({region_name})")
        self._active_worker = AsyncFlashWorker(
            adapter=self.adapter,
            ecu=self.ecu,
            operation="read",
            region_name=region_name,
            operation_id=operation_id,
        )

        self._connect_worker_signals()
        self.operation_started.emit("read")
        self._active_worker.start()
        return True

    def start_write_operation(
        self,
        file_path: str,
        region_name: str = "full",
        operator_confirmed: bool = False,
        backup_verified: bool = False,
    ) -> bool:
        if not self._can_start_operation("write"):
            return False
        if not operator_confirmed:
            self._state.log_error("Safety", "Flash write requires explicit operator confirmation.")
            return False
        if not file_path:
            self._state.log_error("Validation", "No firmware file was selected.")
            return False
        available_write_regions = (
            self.ecu.get_simulation_write_regions()
            if self.adapter.is_simulation
            else self.ecu.get_write_regions()
        )
        if region_name not in available_write_regions:
            self._state.log_error("Validation", f"Unsupported write region: {region_name}")
            return False
        if not os.path.isfile(file_path):
            self._state.log_error("Validation", f"Firmware file does not exist: {file_path}")
            return False

        voltage = self._voltage_evidence()
        request = ProgrammingRequest(
            region_name=region_name,
            file_path=file_path,
            voltage=voltage,
            operator_authorized=operator_confirmed,
            backup_verified=backup_verified,
        )
        operation_id = self._begin_status("write", f"Preparing flash ({region_name})")
        self._active_worker = AsyncFlashWorker(
            adapter=self.adapter,
            ecu=self.ecu,
            operation="write",
            region_name=region_name,
            file_path=file_path,
            programming_request=request,
            operation_id=operation_id,
        )

        self._connect_worker_signals()
        self.operation_started.emit("write")
        self._active_worker.start()
        return True

    def start_info_operation(self) -> bool:
        if not self._can_start_operation("info"):
            return False
        if not self.adapter.is_simulation and not self.ecu.CAPABILITIES.supports_identification:
            self._state.log_error("Safety", "Identification capability is not verified for this ECU definition.")
            return False

        operation_id = self._begin_status("info", "Preparing ECU identification")
        self._active_worker = AsyncFlashWorker(
            adapter=self.adapter,
            ecu=self.ecu,
            operation="info",
            operation_id=operation_id,
        )

        self._connect_worker_signals()
        self.operation_started.emit("info")
        self._active_worker.start()
        return True

    def start_recovery_operation(
        self,
        operator_confirmed: bool = False,
        backup_verified: bool = False,
    ) -> bool:
        if not self._can_start_operation("recovery"):
            return False
        if not operator_confirmed:
            self._state.log_error("Safety", "Recovery preparation requires explicit operator confirmation.")
            return False
        if not backup_verified:
            self._state.log_error("Safety", "Recovery preparation requires a verified backup.")
            return False
        if not self.ecu.CAPABILITIES.supports_recovery:
            self._state.log_error("Safety", "Recovery capability is not released for this ECU definition.")
            return False

        from domain.trionic import TrionicGeneration

        profile = getattr(self.ecu, "PROFILE", None)
        if profile is None or profile.generation is not TrionicGeneration.T8:
            self._state.log_error("Safety", "The dedicated recovery-loader flow is currently only implemented for Trionic 8.")
            return False

        operation_id = self._begin_status("recovery", "Preparing T8 recovery session and loader")
        self._active_worker = AsyncFlashWorker(
            adapter=self.adapter,
            ecu=self.ecu,
            operation="recovery",
            operation_id=operation_id,
        )

        self._connect_worker_signals()
        self.operation_started.emit("recovery")
        self._active_worker.start()
        return True

    def cancel_operation(self) -> bool:
        if self._active_worker and self._active_worker.isRunning():
            self._active_worker.cancel()
            with self._status_lock:
                self._operation_status["phase"] = "Cancellation requested"
                self._operation_status["details"] = (
                    "Cancellation is latched. If erase has started, programming will continue "
                    "through readback verification and reset rather than abandoning the ECU."
                )
            return True
        return False

    def get_operation_status(self) -> Dict[str, Any]:
        with self._status_lock:
            return dict(self._operation_status)

    def _connect_worker_signals(self) -> None:
        if not self._active_worker:
            return

        self._active_worker.progress_changed.connect(self._on_worker_progress)
        self._active_worker.phase_changed.connect(self._on_worker_phase)
        self._active_worker.log_emitted.connect(self._on_worker_log)
        self._active_worker.operation_result.connect(self._on_worker_finished)
        self._active_worker.finished.connect(self._on_worker_thread_stopped)

    def _on_worker_progress(self, pct: int, speed: float, details: str) -> None:
        with self._status_lock:
            self._operation_status.update(
                percent=pct,
                speedKbps=speed,
                details=details,
            )
        self._state.set_phase(self._state.current_phase, pct, details)
        self.operation_progress.emit(pct, speed, details)

    def _on_worker_phase(self, phase_name: str) -> None:
        with self._status_lock:
            self._operation_status["phase"] = phase_name
        self._state.set_phase(phase_name, self._state.phase_progress)
        self.operation_phase.emit(phase_name)

    def _on_worker_log(self, level: str, category: str, message: str) -> None:
        if level == "ERROR":
            self._state.log_error(category, message)
        elif level == "WARN":
            self._state.log_warn(category, message)
        else:
            self._state.log_info(category, message)

    def _on_worker_finished(self, success: bool, summary: str, terminal_state: str) -> None:
        self._pending_completion = (success, summary, terminal_state)
        with self._status_lock:
            self._operation_status.update(
                active=True,
                state="running",
                phase="Finalizing worker cleanup",
                percent=100 if success else self._operation_status["percent"],
                success=success,
                message=summary,
                details=summary,
            )
        if success:
            self._state.set_phase("Idle / Completed", 100, summary)
            self._state.log_info("FlashEngine", f"Operation completed: {summary}")
        else:
            self._state.set_phase("Recovery Required" if terminal_state == "recovery_required" else "Failed", 0, summary)
            self._state.log_error("FlashEngine", f"Operation failed: {summary}")

    def _on_worker_thread_stopped(self) -> None:
        result = self._pending_completion or (
            False,
            "Worker stopped without a terminal result.",
            "failed",
        )
        success, summary, terminal_state = result
        with self._status_lock:
            self._operation_status.update(
                active=False,
                state=terminal_state,
                phase=terminal_state.replace("_", " ").title(),
            )
        worker = self._active_worker
        self._active_worker = None
        self._pending_completion = None
        if worker is not None:
            worker.deleteLater()
        self.operation_completed.emit(success, summary)

    def _can_start_operation(self, operation: str) -> bool:
        if self._operation_is_active():
            self._state.log_error("FlashEngine", "An operation is already in progress.")
            return False
        if not self.is_connected:
            self._state.log_error(
                "Safety",
                f"Cannot start {operation}: connect to the ECU first.",
            )
            return False
        return True

    def _operation_is_active(self) -> bool:
        return bool(self._active_worker and self._active_worker.isRunning())

    def _begin_status(self, operation: str, details: str) -> str:
        operation_id = uuid.uuid4().hex
        with self._status_lock:
            self._operation_status = {
                "operationId": operation_id,
                "operation": operation,
                "active": True,
                "state": "running",
                "phase": "Starting",
                "percent": 0,
                "speedKbps": 0.0,
                "details": details,
                "success": None,
                "message": "",
            }
        return operation_id

    @staticmethod
    def _idle_status() -> Dict[str, Any]:
        return {
            "operationId": "",
            "operation": "",
            "active": False,
            "state": "idle",
            "phase": "Idle",
            "percent": 0,
            "speedKbps": 0.0,
            "details": "Connect to an ECU to begin.",
            "success": None,
            "message": "",
        }

    def _voltage_evidence(self) -> VoltageEvidence:
        if self.adapter.is_simulation:
            return VoltageEvidence(
                value=getattr(self.adapter, "supply_voltage", None),
                source="MockAdapter simulated supply",
                measured_at=self._clock.wall_time(),
            )
        return VoltageEvidence(
            value=self._state.voltage,
            source=self._state.voltage_source,
            measured_at=self._state.voltage_measured_at,
        )
