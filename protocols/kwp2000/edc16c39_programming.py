"""Multi-phase flash programming sequence for EDC16C39.

The order and address ranges are defined by the diagnostic profile specification.
"""

from __future__ import annotations

from contextlib import ExitStack
from typing import Callable

from domain.edc16c39 import (
    EDC16C39_FULL_PROGRAMMING_PLAN,
    Edc16Area,
    Edc16PhaseKind,
)
from domain.errors import OperationCancelled, RecoveryRequiredError
from protocols.base_protocol import DownloadParameters


class Edc16C39ProgrammingCoordinator:
    """Mixin implementing the full-image phase machine."""

    _edc16_destructive_started: bool

    def manages_programming_region(self, region_name: str) -> bool:
        return region_name in {"full", "calibration"}

    def execute_managed_programming(
        self,
        *,
        region_name: str,
        region_start: int,
        data: bytes,
        progress_callback: Callable[[float, str], None],
    ) -> bool:
        if region_name not in {"full", "calibration"}:
            raise ValueError("EDC16C39 managed programming supports 'full' or 'calibration' regions")
        if not self.adapter.is_connected():
            raise RuntimeError("EDC16 programming requires an already-connected adapter")

        total_programmed = sum(
            phase.area.size
            for phase in EDC16C39_FULL_PROGRAMMING_PLAN
            if phase.kind is Edc16PhaseKind.PROGRAM and phase.area is not None
        )
        completed_bytes = 0
        self._edc16_destructive_started = False

        try:
            with ExitStack() as unsafe_phase:
                for phase_index, phase in enumerate(EDC16C39_FULL_PROGRAMMING_PLAN, start=1):
                    if self._cancel.should_interrupt:
                        raise OperationCancelled(
                            f"EDC16 programming cancelled before phase {phase_index}: {phase.kind.value}"
                        )
                    area_label = f" {phase.area.name}" if phase.area else ""
                    progress_callback(
                        completed_bytes / max(1, total_programmed) * 99.0,
                        f"EDC16 phase {phase_index}/19: {phase.kind.value}{area_label}",
                    )

                    if phase.kind is Edc16PhaseKind.CONNECT:
                        if not self.adapter.is_connected():
                            raise RuntimeError("adapter disconnected before EDC16 programming")
                    elif phase.kind is Edc16PhaseKind.SECURITY:
                        if not self.authenticate():
                            raise RuntimeError("EDC16 SecurityAccess was not acknowledged")
                    elif phase.kind is Edc16PhaseKind.START_PROGRAMMING_SESSION:
                        if not self.enter_programming_mode():
                            raise RuntimeError("EDC16 programming session was not acknowledged")
                        if not self.send_tester_present():
                            raise RuntimeError("EDC16 initial TesterPresent was not acknowledged")
                    elif phase.kind is Edc16PhaseKind.ERASE:
                        if not self._edc16_destructive_started:
                            unsafe_phase.enter_context(self._cancel.defer_interrupts())
                            self._edc16_destructive_started = True
                        if phase.area is None or not self._edc16_erase_area(phase.area):
                            raise RuntimeError("EDC16 erase acknowledgement failed")
                    elif phase.kind is Edc16PhaseKind.PROGRAM:
                        if phase.area is None:
                            raise RuntimeError("EDC16 program phase has no destination area")
                        self._edc16_program_area(phase.area, data, completed_bytes, total_programmed, progress_callback)
                        completed_bytes += phase.area.size
                    elif phase.kind is Edc16PhaseKind.VERIFY:
                        if phase.area is None or not self._edc16_verify_area(phase.area, data):
                            raise RuntimeError("EDC16 byte-for-byte verification failed")
                    elif phase.kind is Edc16PhaseKind.RESET:
                        if not self.return_to_normal_mode():
                            raise RuntimeError("EDC16 reset was not acknowledged")
                    elif phase.kind is Edc16PhaseKind.WAIT_RECONNECT:
                        if not self._edc16_wait_reconnect():
                            raise RuntimeError("EDC16 did not return after reset")
                    else:  # pragma: no cover - enum/plan evolution guard
                        raise RuntimeError(f"unsupported EDC16 programming phase {phase.kind!r}")
        except OperationCancelled:
            if self._edc16_destructive_started:
                raise RecoveryRequiredError(
                    "EDC16 cancellation occurred after erase; preserve power for recovery.",
                    last_known_state="edc16_programming",
                )
            raise
        except RecoveryRequiredError:
            raise
        except Exception as exc:
            if self._edc16_destructive_started:
                raise RecoveryRequiredError(
                    f"EDC16 {phase.kind.value} failed after erase; automatic restart is forbidden.",
                    last_known_state=f"edc16_{phase.kind.value}",
                ) from exc
            raise

        progress_callback(100.0, "EDC16 full-image programming and readback verification complete")
        return True

    def _edc16_program_area(
        self,
        area: Edc16Area,
        image: bytes,
        completed_before: int,
        total_programmed: int,
        progress_callback: Callable[[float, str], None],
    ) -> None:
        parameters = self._edc16_request_download_area(area)
        if not isinstance(parameters, DownloadParameters):
            raise RuntimeError("EDC16 RequestDownload did not return transfer parameters")
        block_size = min(
            self.ecu.WRITE_BLOCK_SIZE,
            parameters.max_data_bytes(self.ecu.TRANSFER_REQUEST_OVERHEAD),
        )
        if block_size <= 0:
            raise RuntimeError("EDC16 negotiated an unusable TransferData size")

        address = area.start
        while address < area.end:
            length = min(block_size, area.end - address)
            chunk = image[address:address + length]
            if len(chunk) != length:
                raise RuntimeError(f"EDC16 image is short at 0x{address:08X}")
            if not self.write_memory_block(address, chunk):
                raise RuntimeError(f"EDC16 TransferData failed at 0x{address:08X}")
            address += length
            done = completed_before + address - area.start
            progress_callback(
                done / max(1, total_programmed) * 90.0,
                f"EDC16 programming {area.name}: 0x{address:08X}",
            )
        if not self.finalize_transfer():
            raise RuntimeError(f"EDC16 RequestTransferExit failed for {area.name}")

    def _edc16_verify_area(self, area: Edc16Area, image: bytes) -> bool:
        address = area.start
        while address < area.end:
            length = min(self.ecu.READ_HIGH_SPEED_CHUNK, area.end - address)
            actual = self.read_memory_by_address(address, length, timeout_s=5.0)
            if actual != image[address:address + length]:
                return False
            address += length
        return True

    def _edc16_erase_area(self, area: Edc16Area) -> bool:
        raise NotImplementedError

    def _edc16_request_download_area(self, area: Edc16Area) -> DownloadParameters:
        raise NotImplementedError

    def _edc16_wait_reconnect(self) -> bool:
        raise NotImplementedError
