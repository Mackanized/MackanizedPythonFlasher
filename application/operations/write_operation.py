"""
Application Layer - Write Operation.

State-machine-like flash write with erase, transfer, ECU verification, and
readback verification.  Extracted from the former ECUFlasher.write_region.
"""

from typing import Callable, Optional, Tuple
from protocols.base_protocol import ManagedProgrammingClient, ProtocolClient
from ecus.base_ecu import BaseECU
from domain.cancellation import CancellationToken
from domain.clock import Clock, SystemClock
from domain.errors import OperationCancelled, NotConnectedError, RecoveryRequiredError
from application.operations.session_manager import SessionManager
from logger import app_logger
from application.validation.programming_preflight import ApprovedProgrammingPlan
from domain.errors import ProgrammingPreflightError
from domain.physical_write_readiness import assess_physical_write_readiness


class WriteOperation:
    """Writes data to an ECU flash region with full verification."""

    REQUIRED_PREFLIGHT_CHECKS = frozenset({
        "adapter_connected",
        "operator_authorization",
        "ecu_write_capability",
        "programming_strategy",
        "region_declared",
        "physical_write_readiness",
        "live_identity",
        "identity_compatibility",
        "supply_voltage",
        "backup_policy",
        "ecu_checksum_strategy",
        "file_format",
        "file_exists",
        "file_readable",
        "mapped_length",
        "address_bounds",
        "address_alignment",
        "payload_readable",
        "nonblank_payload",
        "ecu_checksum_valid",
        "writable_segments",
        "protected_ranges",
    })

    def __init__(
        self,
        protocol: ProtocolClient,
        ecu: BaseECU,
        session: SessionManager,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancellation_token: Optional[CancellationToken] = None,
        clock: Optional[Clock] = None,
    ):
        self._protocol = protocol
        self._ecu = ecu
        self._session = session
        self._progress_cb = progress_callback or (lambda pct, msg: None)
        self._cancel = cancellation_token or CancellationToken()
        self._clock = clock or SystemClock()

    def execute(self, plan: ApprovedProgrammingPlan) -> bool:
        if not self._protocol:
            raise NotConnectedError("Protocol client not connected.")
        if plan.ecu_name != self._ecu.NAME or not plan.authorization_id:
            raise ProgrammingPreflightError("Write operation received an invalid or mismatched approval plan.")
        adapter_simulation = getattr(self._protocol.adapter, "is_simulation", None)
        if isinstance(adapter_simulation, bool) and plan.simulation != adapter_simulation:
            raise ProgrammingPreflightError("Write approval transport type does not match the active adapter.")
        if not plan.simulation:
            readiness = assess_physical_write_readiness(self._ecu, plan.region_name)
            if not readiness.ready:
                raise ProgrammingPreflightError(
                    f"Physical write is not released: {readiness.summary}"
                )
            capability = (
                self._ecu.CAPABILITIES.supports_full_write
                if plan.region_name == "full"
                else self._ecu.CAPABILITIES.supports_calibration_write
            )
            if not capability:
                raise ProgrammingPreflightError("Physical write capability is not released for this ECU and region.")
        check_names = {check.name for check in plan.checks}
        if not plan.checks or not all(check.passed for check in plan.checks):
            raise ProgrammingPreflightError("Write operation received an unapproved safety plan.")
        if "preflight_bypass" not in check_names and not self.REQUIRED_PREFLIGHT_CHECKS.issubset(check_names):
            missing = ", ".join(sorted(self.REQUIRED_PREFLIGHT_CHECKS - check_names))
            raise ProgrammingPreflightError(
                f"Write operation received an incomplete safety plan; missing checks: {missing}"
            )

        if (
            isinstance(self._protocol, ManagedProgrammingClient)
            and self._protocol.manages_programming_region(plan.region_name)
        ):
            return self._execute_managed(plan)

        start, end, data = plan.start, plan.end, plan.data
        writable_segments = plan.writable_segments

        app_logger.info(f"Writing region 0x{start:06X} - 0x{end:06X}")

        if self._cancel.should_interrupt:
            raise OperationCancelled("Write cancelled before programming-session entry.")
        if not writable_segments:
            raise ValueError("Approved programming plan contains no writable segments.")
        if not self._session.enter_write_session():
            app_logger.error("Mandatory programming-session preparation failed; erase blocked.")
            self._session.return_to_normal()
            return False
        if self._cancel.should_interrupt:
            self._session.return_to_normal()
            raise OperationCancelled("Write cancelled before erase.")

        # Once RequestDownload is sent, interruption is unsafe. Cancellation is
        # latched and the operation proceeds through verification and reset.
        with self._cancel.defer_interrupts():
            self._progress_cb(0.0, "Erasing flash...")
            try:
                erase_ok = self._erase_flash(writable_segments)
            except Exception as exc:
                raise RecoveryRequiredError(
                    f"RequestDownload/erase raised {type(exc).__name__}; outcome is unknown.",
                    last_known_state="request_download",
                ) from exc
            if not erase_ok:
                raise RecoveryRequiredError(
                    "RequestDownload/erase outcome is unknown; automatic retry is forbidden.",
                    last_known_state="request_download",
                )

            self._progress_cb(5.0, "Writing blocks...")
            try:
                transfer_ok = self._write_blocks(start, data, writable_segments)
            except Exception as exc:
                raise RecoveryRequiredError(
                    f"Transfer raised {type(exc).__name__} after erase; ECU image may be incomplete.",
                    last_known_state="transferring",
                ) from exc
            if not transfer_ok:
                raise RecoveryRequiredError(
                    "Transfer failed after erase; ECU image may be incomplete.",
                    last_known_state="transferring",
                )

            self._progress_cb(90.0, "Finalizing transfer...")
            try:
                finalized = self._protocol.finalize_transfer()
            except Exception as exc:
                raise RecoveryRequiredError(
                    f"Transfer finalization raised {type(exc).__name__}; ECU state is uncertain.",
                    last_known_state="exiting_transfer",
                ) from exc
            if not finalized:
                raise RecoveryRequiredError(
                    "Transfer finalization was not acknowledged.",
                    last_known_state="exiting_transfer",
                )

            self._progress_cb(92.0, "Verifying post-flash state (ECU routine)...")
            try:
                ecu_verified = self._protocol.verify_flash_routine()
            except Exception as exc:
                raise RecoveryRequiredError(
                    f"ECU verification raised {type(exc).__name__} after programming.",
                    last_known_state="ecu_verification",
                ) from exc
            if not ecu_verified:
                raise RecoveryRequiredError(
                    "ECU verification failed after programming; automatic erase retry is forbidden.",
                    last_known_state="ecu_verification",
                )

            self._progress_cb(94.0, "Readback verification...")
            try:
                readback_ok = self._readback_verify(start, data, writable_segments)
            except Exception as exc:
                raise RecoveryRequiredError(
                    f"Readback raised {type(exc).__name__} after programming.",
                    last_known_state="readback_verification",
                ) from exc
            if not readback_ok:
                raise RecoveryRequiredError(
                    "Readback differs after programming; preserve power for recovery.",
                    last_known_state="readback_verification",
                )

            self._progress_cb(100.0, "Resetting ECU...")
            try:
                reset_ok = self._session.return_to_normal()
            except Exception as exc:
                raise RecoveryRequiredError(
                    f"Reset raised {type(exc).__name__} after verified programming.",
                    last_known_state="resetting",
                ) from exc
            if not reset_ok:
                raise RecoveryRequiredError(
                    "Programming verified but ECU reset was not acknowledged.",
                    last_known_state="resetting",
                )

        if self._cancel.is_cancelled:
            self._progress_cb(100.0, "Cancellation was deferred until verified reset; programming completed safely.")
        app_logger.info("ECU reset to normal mode after verified write.")
        return True

    def _execute_managed(self, plan: ApprovedProgrammingPlan) -> bool:
        """Delegate a non-flat ECU workflow to its family coordinator."""
        if self._cancel.should_interrupt:
            raise OperationCancelled("Write cancelled before ECU-specific programming began.")
        try:
            completed = self._protocol.execute_managed_programming(
                region_name=plan.region_name,
                region_start=plan.start,
                data=plan.data,
                progress_callback=self._progress_cb,
            )
        except (RecoveryRequiredError, OperationCancelled):
            raise
        except Exception as exc:
            raise RecoveryRequiredError(
                f"ECU-specific programming failed with {type(exc).__name__}; "
                "the controller state must be assessed before retrying.",
                last_known_state="managed_programming",
            ) from exc
        if not completed:
            raise RecoveryRequiredError(
                "ECU-specific programming did not complete; automatic retry is forbidden.",
                last_known_state="managed_programming",
            )
        if self._cancel.is_cancelled:
            self._progress_cb(
                100.0,
                "Cancellation was deferred until the ECU-specific plan reached a safe reset.",
            )
        return True

    def _erase_flash(self, writable_segments: Tuple[Tuple[int, int], ...]) -> bool:
        erase_size = sum(end - start for start, end in writable_segments)
        app_logger.info(f"Initiating download / erase session ({erase_size} bytes)...")

        self._download_parameters = self._protocol.request_download(erase_size)
        if not self._download_parameters:
            app_logger.error("Flash RequestDownload failed.")
            return False

        delay = self._ecu.POST_ERASE_DELAY
        if delay > 0:
            app_logger.info(f"Waiting {delay}s for session to settle...")
            self._clock.sleep(delay)

        app_logger.info("Flash download session ready.")
        return True

    def _write_blocks(
        self,
        region_start: int,
        data: bytes,
        writable_segments: Tuple[Tuple[int, int], ...],
    ) -> bool:
        negotiated_size = self._download_parameters.max_data_bytes(
            self._ecu.TRANSFER_REQUEST_OVERHEAD
        )
        block_size = min(self._ecu.WRITE_BLOCK_SIZE, negotiated_size)
        if block_size <= 0:
            raise ValueError("No usable TransferData payload remains after negotiation")
        app_logger.info(
            f"Using {block_size}-byte data blocks (ECU maximum request "
            f"{self._download_parameters.max_request_bytes} bytes)."
        )
        bytes_written = 0
        total = sum(end - start for start, end in writable_segments)
        data_view = memoryview(data)

        start_time = self._clock.monotonic()

        for segment_start, segment_end in writable_segments:
            current_addr = segment_start
            while current_addr < segment_end:
                remaining = segment_end - current_addr
                chunk_len = min(block_size, remaining)
                file_offset = current_addr - region_start
                chunk = data_view[file_offset:file_offset + chunk_len]
                if len(chunk) != chunk_len:
                    app_logger.error(f"Approved data is short at 0x{current_addr:06X}.")
                    return False
                if not self._protocol.write_memory_block(current_addr, chunk):
                    app_logger.error(f"Write failed at 0x{current_addr:06X}.")
                    return False
                self._session.keep_alive()
                current_addr += chunk_len
                bytes_written += chunk_len
                pct = 5.0 + (bytes_written / total) * 87.0
                elapsed = self._clock.monotonic() - start_time
                self._progress_cb(pct, f"0x{current_addr:06X} | {int(elapsed // 60)}m {int(elapsed % 60)}s")

        app_logger.info("Write blocks complete.")
        return True

    def _readback_verify(
        self,
        region_start: int,
        data: bytes,
        writable_segments: Tuple[Tuple[int, int], ...],
    ) -> bool:
        """Read the flashed region back and compare byte-for-byte."""
        app_logger.info(f"Readback verify across {len(writable_segments)} approved segment(s)")
        verify_chunk = self._ecu.READ_HIGH_SPEED_CHUNK
        mismatches = 0
        total = sum(end - start for start, end in writable_segments)
        verified = 0
        data_view = memoryview(data)

        for segment_start, segment_end in writable_segments:
            current_addr = segment_start
            while current_addr < segment_end:
                remaining = segment_end - current_addr
                fetch_size = min(verify_chunk, remaining)

                self._session.keep_alive()

                file_offset = current_addr - region_start
                expected = data_view[file_offset:file_offset + fetch_size]

                try:
                    actual = self._protocol.read_memory_by_address(current_addr, fetch_size, timeout_s=5.0)
                except TimeoutError:
                    app_logger.error(f"Readback timeout at 0x{current_addr:06X}")
                    return False

                if actual is None or len(actual) != fetch_size:
                    app_logger.error(f"Readback: incomplete data at 0x{current_addr:06X}")
                    return False

                if actual != expected:
                    mismatches += 1
                    app_logger.error(f"Readback MISMATCH at 0x{current_addr:06X}.")
                    return False

                current_addr += fetch_size
                verified += fetch_size
                pct = 94.0 + verified / max(1, total) * 5.0
                self._progress_cb(pct, f"Readback 0x{current_addr:06X}")

        if mismatches > 0:
            app_logger.error(f"Readback verification failed with {mismatches} mismatch(es).")
            return False

        app_logger.info("Readback verification PASSED.")
        return True
