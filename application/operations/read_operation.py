"""
Application Layer - Read Operation.

State-machine-like read of a memory region from an ECU.  Extracted from the
former ``ECUFlasher.read_region`` method.
"""

import os
import json
import hashlib
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional
from protocols.base_protocol import ProtocolClient
from ecus.base_ecu import BaseECU
from domain.cancellation import CancellationToken
from domain.clock import Clock, SystemClock
from domain.errors import FlashError, OperationCancelled, NotConnectedError
from application.operations.session_manager import SessionManager
from logger import app_logger


class ReadOperation:
    """Reads a memory region from an ECU via a protocol client."""

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
        self._last_provenance = []

    def execute(self, start: int, end: int) -> bytearray:
        """Read ``[start, end)`` and return only the requested region bytes."""
        if not self._protocol:
            raise NotConnectedError("Protocol client not connected.")

        if not self._session.enter_read_session():
            raise FlashError("Failed to enter read session.")

        target_length = end - start
        if not 0 <= start < end <= self._ecu.TOTAL_FLASH_SIZE:
            raise ValueError("Read range lies outside the ECU flash map")
        image = bytearray(b'\xFF' * target_length)
        unreadable = [
            (max(start, item_start), min(end, item_end))
            for item_start, item_end in self._ecu.get_unreadable_ranges()
            if max(start, item_start) < min(end, item_end)
        ]
        readable_total = target_length - sum(item_end - item_start for item_start, item_end in unreadable)
        confirmed_bytes = 0
        current_addr = start
        self._last_provenance = []

        self._progress_cb(0.0, f"Reading 0x{start:06X} - 0x{end:06X}")
        app_logger.info(f"Reading region 0x{start:06X} - 0x{end:06X}")

        start_time = self._clock.monotonic()

        try:
            while current_addr < end:
                self._cancel.check("read")  # raises OperationCancelled if set
                if self._cancel.is_cancelled:
                    raise OperationCancelled("Read cancelled by user.")

                before_skip = current_addr
                current_addr = self._ecu.skip_gaps_forward(current_addr)
                for protected_start, protected_end in self._ecu.get_unreadable_ranges():
                    if protected_start <= current_addr < protected_end:
                        current_addr = protected_end
                        break
                if current_addr > before_skip:
                    self._last_provenance.append({
                        "start": before_skip,
                        "end": min(current_addr, end),
                        "status": "protected_not_read",
                    })
                if current_addr >= end:
                    break

                remaining = end - current_addr
                fetch_size = min(self._ecu.READ_HIGH_SPEED_CHUNK, remaining)
                for protected_start, _protected_end in self._ecu.get_unreadable_ranges():
                    if current_addr < protected_start < current_addr + fetch_size:
                        fetch_size = protected_start - current_addr

                self._session.keep_alive()

                try:
                    chunk = self._protocol.read_memory_by_address(current_addr, fetch_size)
                except TimeoutError:
                    app_logger.error(f"Timeout at 0x{current_addr:06X}. Aborting read.")
                    raise

                if chunk is None or len(chunk) != fetch_size:
                    received = 0 if chunk is None else len(chunk)
                    raise FlashError(
                        f"Incomplete read at 0x{current_addr:06X}: "
                        f"expected {fetch_size} bytes, received {received}."
                    )
                image[current_addr - start:current_addr - start + fetch_size] = chunk
                self._last_provenance.append({
                    "start": current_addr,
                    "end": current_addr + fetch_size,
                    "status": "read_from_ecu",
                })
                current_addr += fetch_size
                confirmed_bytes += fetch_size

                elapsed = self._clock.monotonic() - start_time
                pct = (confirmed_bytes / readable_total) * 100 if readable_total else 100.0
                elapsed_m = int(elapsed // 60)
                elapsed_s = int(elapsed % 60)
                self._progress_cb(pct, f"0x{current_addr:06X} | {elapsed_m}m {elapsed_s}s")
        finally:
            self._session.return_to_normal()

        elapsed = self._clock.monotonic() - start_time
        app_logger.info(f"Read complete in {int(elapsed // 60)}m {int(elapsed % 60)}s.")
        return image

    def execute_to_file(self, region_name: str, output_dir: str = ".") -> str:
        """Read a named region and save to file with a manifest."""
        regions = self._ecu.get_flash_regions()
        if region_name not in regions:
            available = ", ".join(regions.keys())
            raise ValueError(f"Unknown region '{region_name}'. Available: {available}")
        start, end, default_name = regions[region_name]

        image = self.execute(start, end)

        save_data = image

        protected = [
            (max(start, s), min(end, e))
            for s, e in self._ecu.get_unreadable_ranges()
            if max(start, s) < min(end, e)
        ]
        complete = not protected
        output_name = default_name
        if not complete:
            stem, suffix = os.path.splitext(default_name)
            output_name = f"{stem}.partial{suffix or '.bin'}"
        filename = os.path.join(output_dir, output_name)

        manifest_path = filename + ".manifest.json"
        manifest = {
            "ecu": self._ecu.NAME,
            "region": region_name,
            "start": f"0x{start:06X}",
            "end": f"0x{end:06X}",
            "bytes_saved": len(save_data),
            "total_flash_size": self._ecu.TOTAL_FLASH_SIZE,
            "status": "complete" if complete else "partial",
            "sha256": hashlib.sha256(save_data).hexdigest(),
            "protected_or_skipped_ranges": [
                {"start": f"0x{s:06X}", "end": f"0x{e:06X}"}
                for s, e in protected
            ],
            "spans": [
                {
                    "start": f"0x{span['start']:06X}",
                    "end": f"0x{span['end']:06X}",
                    "status": span["status"],
                }
                for span in self._last_provenance
            ],
            "note": (
                "Every saved byte was read from the ECU."
                if complete else
                "PARTIAL artifact: protected ranges were not read and must not be treated as a complete backup."
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._atomic_write_artifact(Path(filename), save_data, manifest)

        app_logger.info(
            f"Saved {manifest['status']} read artifact ({len(save_data)} bytes) to {filename}"
        )
        return filename

    @staticmethod
    def _atomic_write_artifact(filename: Path, data: bytes, manifest: dict) -> None:
        """Commit data and mandatory provenance manifest without swallowing failures."""
        filename.parent.mkdir(parents=True, exist_ok=True)
        manifest_path = Path(str(filename) + ".manifest.json")
        data_tmp = manifest_tmp = None
        try:
            with tempfile.NamedTemporaryFile("wb", dir=filename.parent, delete=False) as handle:
                data_tmp = Path(handle.name)
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            with tempfile.NamedTemporaryFile(
                "w", dir=filename.parent, encoding="utf-8", delete=False
            ) as handle:
                manifest_tmp = Path(handle.name)
                json.dump(manifest, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(data_tmp, filename)
            data_tmp = None
            try:
                os.replace(manifest_tmp, manifest_path)
                manifest_tmp = None
            except OSError:
                filename.unlink(missing_ok=True)
                raise
        finally:
            if data_tmp is not None:
                data_tmp.unlink(missing_ok=True)
            if manifest_tmp is not None:
                manifest_tmp.unlink(missing_ok=True)
