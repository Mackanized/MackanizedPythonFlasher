"""
Application Layer - Async Flasher QThread Worker

Performs non-blocking real flash operations (Read, Write, Info, Recovery) in a dedicated background QThread
using ECUFlasher. Sends high-resolution progress updates via PySide6 signals.
"""

import time
from typing import Optional
from PySide6.QtCore import QThread, Signal
from adapters.base_adapter import BaseAdapter
from ecus.base_ecu import BaseECU
from flasher import ECUFlasher
from domain.cancellation import CancellationToken
from domain.errors import (
    OperationCancelled,
    ProgrammingPreflightError,
    PythonFlasherError,
    RecoveryRequiredError,
)
from application.validation.programming_preflight import ProgrammingPreflight, ProgrammingRequest
from logger import app_logger, operation_log_context


class AsyncFlashWorker(QThread):
    """Non-blocking QThread worker managing real automotive flash sequences via ECUFlasher."""

    progress_changed = Signal(int, float, str)
    phase_changed = Signal(str)
    log_emitted = Signal(str, str, str)
    operation_result = Signal(bool, str, str)  # success, summary, terminal state

    def __init__(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        operation: str,
        region_name: str = "full",
        file_path: Optional[str] = None,
        programming_request: Optional[ProgrammingRequest] = None,
        operation_id: str = "",
        parent=None
    ):
        super().__init__(parent)
        self._adapter = adapter
        self._ecu = ecu
        self._operation = operation
        self._region_name = region_name
        self._file_path = file_path
        self._programming_request = programming_request
        self._operation_id = operation_id
        self._cancel_token = CancellationToken()
        self._flasher: Optional[ECUFlasher] = None
        self._start_time = 0.0

    def cancel(self) -> None:
        """Signal emergency stop to background operation."""
        self._cancel_token.cancel()
        self.log_emitted.emit(
            "WARN",
            "FlashEngine",
            "Cancellation requested. Destructive phases will continue through verified reset before stopping.",
        )

    def run(self) -> None:
        """Main QThread execution body invoking real ECUFlasher engine."""
        self._start_time = time.monotonic()
        with operation_log_context(self._operation_id):
            self._run_guarded()

    def _run_guarded(self) -> None:
        """Map the complete correlated operation to a stable terminal result."""
        try:
            with self._adapter.exclusive_channel():
                self._run_with_channel_lease()
        except RecoveryRequiredError as exc:
            summary = f"Recovery required: {exc}. Keep ECU power stable and do not disconnect the adapter."
            self.log_emitted.emit("ERROR", "Recovery", summary)
            self.operation_result.emit(False, summary, "recovery_required")
        except OperationCancelled:
            self.log_emitted.emit("WARN", "FlashEngine", "Operation cancelled before the destructive phase.")
            self.operation_result.emit(False, "Operation cancelled before erase.", "cancelled")
        except ProgrammingPreflightError as exc:
            self.log_emitted.emit("ERROR", "Safety", str(exc))
            self.operation_result.emit(False, str(exc), "failed")
        except PythonFlasherError as exc:
            summary = f"{type(exc).__name__}: {exc}"
            self.log_emitted.emit("ERROR", "FlashEngine", summary)
            self.operation_result.emit(False, summary, "failed")
        except Exception as exc:
            app_logger.error(f"[AsyncFlashWorker] Exception: {exc}")
            self.log_emitted.emit("ERROR", "FlashEngine", f"Flash worker exception: {str(exc)}")
            self.operation_result.emit(False, str(exc), "failed")
        finally:
            if self._flasher:
                try:
                    self._flasher.disconnect()
                except (OSError, RuntimeError) as e:
                    app_logger.debug(f"Worker disconnect cleanup: {e}")

    def _run_with_channel_lease(self) -> None:
        """Run against the service-owned, already-open adapter channel."""
        self._flasher = ECUFlasher(
            adapter=self._adapter,
            ecu=self._ecu,
            progress_callback=self._on_flasher_progress,
            cancellation_token=self._cancel_token,
        )

        self.phase_changed.emit("Attaching to Hardware Channel")
        self.log_emitted.emit("INFO", "Hardware", f"Using open {type(self._adapter).__name__} channel for {self._ecu.NAME}...")

        if not self._adapter.is_connected() or not self._flasher.connect():
            self.operation_result.emit(False, "Hardware adapter channel is not connected.", "failed")
            return

        if self._operation == "info":
            self.phase_changed.emit("Querying ECU Identifiers")
            info = self._flasher.read_ecu_info()
            vin = info.get("vin", "Unknown")
            main_os = info.get("main_os", "Unknown")
            summary = f"ECU Info Read OK. VIN: {vin}, OS: {main_os}"
            self.operation_result.emit(True, summary, "completed")

        elif self._operation == "read":
            self.phase_changed.emit(f"Reading Memory ({self._region_name})")
            out_file = self._file_path or "."
            saved_path = self._flasher.read_to_file(self._region_name, output_dir=out_file)
            self.operation_result.emit(
                True,
                f"Read finished. Artifact and mandatory provenance manifest saved: {saved_path}",
                "completed",
            )

        elif self._operation == "write":
            if not self._programming_request:
                self.operation_result.emit(False, "No approved programming request was supplied.", "failed")
                return
            self.phase_changed.emit("Programming Preflight")
            live_identity = self._flasher.read_ecu_info()
            plan = ProgrammingPreflight.evaluate(
                adapter=self._adapter,
                ecu=self._ecu,
                region_name=self._programming_request.region_name,
                file_path=self._programming_request.file_path,
                live_identity=live_identity,
                voltage=self._programming_request.voltage,
                operator_authorized=self._programming_request.operator_authorized,
                backup_verified=self._programming_request.backup_verified,
                physical_evidence_report=self._programming_request.physical_evidence_report,
                disable_preflight=getattr(self._flasher, "disable_preflight", False),
            )
            self.log_emitted.emit(
                "INFO",
                "Safety",
                f"Programming preflight approved ({plan.authorization_id}); SHA-256 {plan.sha256}.",
            )
            self.phase_changed.emit(f"Flashing Memory ({self._region_name})")
            success = self._flasher.write_from_plan(plan)
            if success:
                self.operation_result.emit(True, "Write operation completed successfully. ECU reset and readback verified.", "completed")
            else:
                self.operation_result.emit(False, "Flash write operation failed.", "failed")

        elif self._operation == "recovery":
            self.phase_changed.emit("Preparing T8 Recovery Session")
            success = self._flasher.prepare_recovery()
            if success:
                self.operation_result.emit(
                    True,
                    "T8 recovery session and loader are prepared. Keep ECU power stable; no erase or image transfer was performed.",
                    "completed",
                )
            else:
                self.operation_result.emit(False, "Recovery session preparation failed.", "failed")

        else:
            self.operation_result.emit(False, f"Unsupported operation: {self._operation}", "failed")

    def _on_flasher_progress(self, percent: float, message: str) -> None:
        pct = int(percent)
        elapsed = max(0.001, time.monotonic() - self._start_time)
        regions = self._ecu.get_flash_regions()
        start, end, _ = regions.get(self._region_name, (0, self._ecu.TOTAL_FLASH_SIZE, ""))
        region_size_kb = (end - start) / 1024.0
        if self._operation == "write":
            transfer_fraction = max(0.0, min(1.0, (percent - 5.0) / 85.0))
        elif self._operation == "read":
            transfer_fraction = max(0.0, min(1.0, percent / 100.0))
        elif self._operation == "recovery":
            transfer_fraction = max(0.0, min(1.0, percent / 100.0))
        else:
            transfer_fraction = 0.0
        bytes_transferred_kb = transfer_fraction * region_size_kb
        speed_kbs = round(bytes_transferred_kb / elapsed, 1)
        self.progress_changed.emit(pct, speed_kbs, message)
