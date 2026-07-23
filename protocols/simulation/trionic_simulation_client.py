"""Generation-aware semantic simulator for complete T5/T7/T8 workflows."""

from __future__ import annotations

from typing import Callable, Optional, Tuple

from adapters.base_adapter import BaseAdapter
from domain.cancellation import CancellationToken
from domain.errors import DiagnosticError
from domain.trionic import TrionicGeneration
from domain.trionic_firmware import inspect_t5_checksum, t8_last_used_address
from ecus.base_ecu import BaseECU
from firmware.trionic.checksums import (
    TrionicChecksumError,
    inspect_t7_checksums,
    inspect_t8_checksums,
)
from protocols.simulation.simulation_client import SimulationProtocolClient


class TrionicSimulationClient(SimulationProtocolClient):
    """Exact semantic phases without pretending the mock is a wire capture."""

    def __init__(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> None:
        super().__init__(adapter, ecu, cancellation_token=cancellation_token)
        self.generation = ecu.PROFILE.generation

    def _phase(self, name: str) -> None:
        self._call("simulation_trionic_phase", self.generation.value, name)

    def prepare_read_session(self) -> bool:
        self._phase("connect")
        if not super().prepare_read_session():
            return False
        if self.generation in {TrionicGeneration.T5_2, TrionicGeneration.T5_5}:
            self._phase("upload-sram-bootloader")
            self._phase("start-sram-bootloader")
        elif self.generation is TrionicGeneration.T7:
            self._phase("start-kwp-session")
            self._phase("security-access-05-06")
        else:
            self._phase("upload-sram-read-loader")
            self._phase("start-sram-loader")
        return True

    def prepare_programming_session(self) -> bool:
        self._phase("connect")
        if not super().prepare_programming_session():
            return False
        for phase in self.ecu.PROFILE.programming_phases[1:]:
            if phase in {
                "erase", "program-nonblank-blocks", "ecu-checksum", "reset",
                "validate-firmware-checksums", "erase-routine-52", "erase-routine-53",
                "download-primary-region", "download-footer-region", "readback-verify",
                "stop-session", "select-and-erase-partitions", "program-encoded-blocks",
                "md5-or-readback-verify", "loader-exit", "reconnect-and-identify",
            }:
                continue
            self._phase(phase)
        return True

    def enter_recovery_mode(self) -> bool:
        self._phase("connect")
        self._phase("recovery-session")
        self._phase(f"security-access-{self.ecu.PROFILE.security_seed_level:02x}-{self.ecu.PROFILE.security_key_level:02x}")
        return True

    def prepare_recovery_loader(self) -> bool:
        if self.generation is not TrionicGeneration.T8:
            self._phase("recovery-session-active")
            return True
        self._phase("upload-sram-recovery-loader")
        self._phase("start-sram-loader")
        return True

    def manages_programming_region(self, region_name: str) -> bool:
        return region_name == "full"

    def execute_managed_programming(
        self,
        *,
        region_name: str,
        region_start: int,
        data: bytes,
        progress_callback: Callable[[float, str], None],
    ) -> bool:
        if region_name != "full" or region_start != 0 or len(data) != self.ecu.TOTAL_FLASH_SIZE:
            raise ValueError("Trionic mock full programming requires one exact full image")
        self._validate_checksum(data)
        progress_callback(0.0, f"Preparing simulated {self.generation.value} programming")
        self.prepare_programming_session()
        with self._cancel.defer_interrupts():
            ranges, block_size, sparse = self._programming_contract(data)
            self._run_erase(ranges)
            total = sum(end - start for start, end in ranges)
            if not self._call("simulation_begin_download", total):
                raise DiagnosticError("Trionic mock rejected its download plan")
            programmed = 0
            for start, end in ranges:
                for address in range(start, end, block_size):
                    chunk = data[address:min(end, address + block_size)]
                    if sparse and all(value == 0xFF for value in chunk):
                        programmed += len(chunk)
                        continue
                    if not self._call("simulation_write_memory", address, chunk):
                        raise DiagnosticError(f"Trionic mock transfer failed at 0x{address:06X}")
                    programmed += len(chunk)
                    progress_callback(8.0 + 72.0 * programmed / max(1, total), f"Mock 0x{address:06X}")
            if not self._call("simulation_finalize_transfer"):
                raise DiagnosticError("Trionic mock transfer did not finalize")
            self._phase(self._verify_phase())
            verified = 0
            for start, end in ranges:
                for address in range(start, end, 0x80):
                    expected = data[address:min(end, address + 0x80)]
                    actual = bytes(self._call("simulation_read_memory", address, len(expected)))
                    if actual != expected:
                        raise DiagnosticError(f"Trionic mock readback mismatch at 0x{address:06X}")
                    verified += len(expected)
                    progress_callback(82.0 + 16.0 * verified / max(1, total), f"Mock verify 0x{address:06X}")
            if not self._call("simulation_verify"):
                raise DiagnosticError("Trionic mock verification failed")
            self._phase(self._exit_phase())
            if not self.return_to_normal_mode():
                raise DiagnosticError("Trionic mock reset/session exit failed")
            if self.generation is TrionicGeneration.T8:
                self._phase("reconnect-and-identify")
        progress_callback(100.0, f"Simulated {self.generation.value} programming complete")
        return True

    def _validate_checksum(self, data: bytes) -> None:
        if self.generation in {TrionicGeneration.T5_2, TrionicGeneration.T5_5}:
            result = inspect_t5_checksum(data)
        elif self.generation is TrionicGeneration.T7:
            try:
                result = inspect_t7_checksums(data)
            except TrionicChecksumError as exc:
                raise DiagnosticError(f"T7 mock checksum structure rejected: {exc}") from exc
        else:
            try:
                result = inspect_t8_checksums(data)
            except TrionicChecksumError as exc:
                raise DiagnosticError(f"T8 mock checksum structure rejected: {exc}") from exc
        if not result.valid:
            raise DiagnosticError(getattr(result, "reason", "Trionic checksum mismatch"))
        self._phase("validate-firmware-checksums")

    def _programming_contract(self, data: bytes) -> Tuple[Tuple[Tuple[int, int], ...], int, bool]:
        if self.generation in {TrionicGeneration.T5_2, TrionicGeneration.T5_5}:
            return ((0, len(data)),), 0x80, True
        if self.generation is TrionicGeneration.T7:
            return ((0, 0x7B000), (0x7FE00, 0x80000)), 0x80, False
        last_used = min(len(data), max(0x020000, t8_last_used_address(data)))
        program_end = min(
            len(data),
            0x020000 + (((last_used - 0x020000) // 0xEA) + 1) * 0xEA,
        )
        return ((0x020000, program_end),), 0xEA, False

    def _run_erase(self, ranges: Tuple[Tuple[int, int], ...]) -> None:
        if self.generation is TrionicGeneration.T7:
            self._phase("erase-routine-52")
            self._phase("erase-routine-53")
        elif self.generation is TrionicGeneration.T8:
            self._phase("select-and-erase-partitions")
        else:
            self._phase("erase")
        erase_ranges = ranges
        if self.generation is TrionicGeneration.T8:
            # Stock selector 6 erases every application partition even when
            # programming stops at the bounded last-used pointer.
            erase_ranges = ((0x020000, self.ecu.TOTAL_FLASH_SIZE),)
        for start, end in erase_ranges:
            self._call(
                "simulation_trionic_erase_range",
                self.generation.value,
                start,
                end - start,
            )

    def _verify_phase(self) -> str:
        if self.generation in {TrionicGeneration.T5_2, TrionicGeneration.T5_5}:
            return "ecu-checksum"
        if self.generation is TrionicGeneration.T7:
            return "readback-verify"
        return "md5-or-readback-verify"

    def _exit_phase(self) -> str:
        if self.generation in {TrionicGeneration.T5_2, TrionicGeneration.T5_5}:
            return "reset"
        if self.generation is TrionicGeneration.T7:
            return "stop-session"
        return "loader-exit"
