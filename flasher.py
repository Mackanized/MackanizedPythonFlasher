import os
import time
from typing import Callable, Dict, Optional, Tuple

from adapters.base_adapter import BaseAdapter
from application.operations.session_manager import SessionManager
from application.operations.write_operation import WriteOperation
from ecus.base_ecu import BaseECU
from gmlan import GMLANClient
from logger import app_logger
from protocols.factory import DefaultProtocolClientFactory
from domain.cancellation import CancellationToken


def _console_progress(percent: float, message: str):
    print(f"  [Progress] {percent:.1f}% | {message}", end='\r')


class ECUFlasher:
    """
    ECU-agnostic flash read/write orchestrator.

    Works with any BaseAdapter (Kvaser, J2534, ...) and any BaseECU subclass.
    Progress is reported via an optional callback; falls back to console output.
    """

    def __init__(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        cancellation_token: Optional[CancellationToken] = None,
        confirmation_provider=None,
    ):
        self.adapter = adapter
        self.ecu = ecu
        self.gmlan: Optional[GMLANClient] = None
        self._progress_cb = progress_callback or _console_progress
        self._cancel = cancellation_token or CancellationToken()
        self._confirmation_provider = confirmation_provider
        self._last_tp_time: float = 0.0
        self._owns_connection = False

    # ── Connection ───────────────────────────────────────────────────

    def connect(self, baudrate: int = 500000) -> bool:
        if not self.adapter.is_connected():
            if not self.adapter.connect(baudrate=baudrate):
                app_logger.error("Failed to connect adapter.")
                return False
            self.adapter.check_bus_status()
            self._owns_connection = True
        else:
            self._owns_connection = False
        self._clear_bus_buffer()
        self.gmlan = DefaultProtocolClientFactory().create(self.adapter, self.ecu, self._cancel)
        self._last_tp_time = 0.0
        app_logger.info(f"Connected via {type(self.adapter).__name__} to {self.ecu.NAME}.")
        return True

    def disconnect(self):
        if self.adapter and self._owns_connection:
            self.adapter.disconnect()
            app_logger.info("Adapter disconnected.")

    # ── Read ─────────────────────────────────────────────────────────

    def read_region(self, start: int, end: int) -> bytearray:
        """
        Read a memory region from the ECU into a bytearray.

        Enters programming session, authenticates, then uses high-speed
        chunked reads with automatic fallback to small reads on NRC.
        Skips known gaps. Returns data placed at absolute offsets
        within a TOTAL_FLASH_SIZE buffer.
        """
        if not self.gmlan:
            raise RuntimeError("Not connected. Call connect() first.")

        if not self._enter_read_session():
            raise RuntimeError("Failed to enter read session (programming mode + auth).")

        total_size = self.ecu.TOTAL_FLASH_SIZE
        image = bytearray(b'\xFF' * total_size)
        target_length = end - start
        current_addr = start

        self._report(0.0, f"Reading 0x{start:06X} - 0x{end:06X}")
        app_logger.info(f"Reading region 0x{start:06X} - 0x{end:06X}")

        start_time = time.time()
        self._last_tp_time = time.time()

        while current_addr < end:
            current_addr = self.ecu.skip_gaps_forward(current_addr)
            if current_addr >= end:
                break

            remaining = end - current_addr
            fetch_size = min(self.ecu.READ_HIGH_SPEED_CHUNK, remaining)

            self._keep_alive()

            try:
                chunk = self.gmlan.read_memory_by_address(current_addr, fetch_size)
            except TimeoutError:
                app_logger.error(f"Timeout at 0x{current_addr:06X}. Aborting read.")
                raise

            if chunk:
                image[current_addr:current_addr + len(chunk)] = chunk
                current_addr += fetch_size
            else:
                current_addr = self._read_fallback(
                    image, current_addr, fetch_size, end, self._last_tp_time
                )

            elapsed = time.time() - start_time
            bytes_read = current_addr - start
            pct = (bytes_read / target_length) * 100
            elapsed_m = int(elapsed // 60)
            elapsed_s = int(elapsed % 60)
            self._report(pct, f"0x{current_addr:06X} | {elapsed_m}m {elapsed_s}s")

        elapsed = time.time() - start_time
        elapsed_m = int(elapsed // 60)
        elapsed_s = int(elapsed % 60)
        app_logger.info(f"Read complete. {elapsed_m}m {elapsed_s}s")
        return image

    def _read_fallback(
        self,
        image: bytearray,
        addr: int,
        block_size: int,
        end: int,
        last_tp_time: float,
    ) -> int:
        """Fall back to 2-byte chunk reads for a restricted block."""
        app_logger.warning(f"Fallback active at 0x{addr:06X}")
        self._clear_bus_buffer()

        fallback_end = min(addr + block_size, end)
        chunk_size = self.ecu.READ_FALLBACK_CHUNK

        while addr < fallback_end:
            self._keep_alive()
            chunk = min(chunk_size, fallback_end - addr)

            try:
                small = self.gmlan.read_memory_by_address(
                    addr, chunk, timeout_s=self.ecu.READ_FALLBACK_TIMEOUT,
                )
            except TimeoutError:
                app_logger.error(f"Timeout during fallback at 0x{addr:06X}.")
                raise

            if small:
                image[addr:addr + len(small)] = small
            else:
                image[addr:addr + chunk] = b'\xFF' * chunk

            addr += chunk

        return addr

    def read_to_file(
        self,
        region_name: str,
        output_dir: str = ".",
    ) -> str:
        """
        Read a named region and save it to a .bin file.

        Returns the path of the saved file.
        """
        start, end, default_name = self._resolve_read_region(region_name)
        image = self.read_region(start, end)

        filename = os.path.join(output_dir, default_name)
        with open(filename, "wb") as f:
            f.write(image)

        app_logger.info(f"Saved {len(image)} bytes to {filename}")
        return filename

    # ── Write ────────────────────────────────────────────────────────

    def write_region(self, start: int, end: int, data: bytes, max_retries: int = 3) -> bool:
        """
        Write data to the ECU flash.

        Handles the full programming sequence: session, auth, erase, write, reset.
        Retries the full sequence on failure with a delay between attempts.
        """
        if not self.gmlan:
            raise RuntimeError("Not connected. Call connect() first.")

        app_logger.info(f"Writing region 0x{start:06X} - 0x{end:06X}")

        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                delay = 5 * (attempt - 1)
                print(f"\n  Resetting ECU and retrying in {delay}s (attempt {attempt}/{max_retries})...")
                app_logger.info(f"Resetting ECU and retrying attempt {attempt}/{max_retries} after {delay}s delay.")
                try:
                    self.gmlan.return_to_normal_mode()
                except Exception:
                    pass
                time.sleep(delay)

            if not self._enter_write_session():
                app_logger.warning(f"Write session failed (attempt {attempt}).")
                continue

            self._report(0.0, "Erasing flash...")
            if not self._erase_flash(start, end):
                app_logger.warning(f"Erase failed (attempt {attempt}).")
                continue

            self._report(5.0, "Writing blocks...")
            if not self._write_blocks(start, end, data):
                app_logger.warning(f"Write blocks failed (attempt {attempt}).")
                continue

            self._report(100.0, "Resetting ECU...")
            self.gmlan.return_to_normal_mode()
            app_logger.info("ECU reset to normal mode.")
            return True

        app_logger.error(f"All {max_retries} write attempts failed.")
        return False

    def write_from_file(self, region_name: str, filename: str) -> bool:
        """
        Write a .bin file to a named region on the ECU.

        Accepts both a full 2MB image or a raw region-sized file.
        Uses write-specific regions (e.g. skips bootloader).
        Performs pre-flash verification before writing.
        """
        start, end, _ = self._resolve_write_region(region_name)
        region_size = end - start

        if not os.path.exists(filename):
            app_logger.error(f"File not found: {filename}")
            return False

        with open(filename, "rb") as f:
            raw = f.read()

        if len(raw) == self.ecu.TOTAL_FLASH_SIZE:
            data = raw[start:end]
        elif len(raw) == region_size:
            data = raw
        else:
            app_logger.error(
                f"Invalid file size {len(raw)} bytes. "
                f"Expected {self.ecu.TOTAL_FLASH_SIZE} (full) or {region_size} (region)."
            )
            return False

        if not self.verify_pre_flash(raw, start, end):
            return False

        return self.write_region(start, end, data)

    def write_from_plan(self, plan) -> bool:
        if not self.gmlan:
            raise RuntimeError("Not connected. Call connect() first.")
        operation = WriteOperation(
            self.gmlan,
            self.ecu,
            SessionManager(self.gmlan, self._cancel),
            progress_callback=self._progress_cb,
            cancellation_token=self._cancel,
        )
        return operation.execute(plan)

    # ── Recovery ─────────────────────────────────────────────────────

    def prepare_recovery(self) -> bool:
        """Enter the ECU-family recovery path and prepare its loader.

        This is intentionally separate from the normal managed write flow. For
        Trionic 8 the protocol client enters the 0x011/0x311 recovery session,
        performs security access, uploads the stock recovery programming loader,
        and starts it. It does not erase or transfer a flash image.
        """
        if not self.gmlan:
            raise RuntimeError("Not connected. Call connect() first.")

        enter_recovery = getattr(self.gmlan, "enter_recovery_mode", None)
        if not callable(enter_recovery):
            raise RuntimeError(f"{self.ecu.NAME} does not expose a recovery session.")

        self._report(5.0, "Entering recovery session...")
        if not enter_recovery():
            return False

        prepare_loader = getattr(self.gmlan, "prepare_recovery_loader", None)
        if callable(prepare_loader):
            self._report(45.0, "Uploading recovery loader...")
            if not prepare_loader():
                return False
            self._report(95.0, "Recovery loader active.")
        else:
            self._report(95.0, "Recovery session active.")
        return True

    # ── ECU Info ─────────────────────────────────────────────────────

    _INFO_DISPATCH = {
        "vin":             lambda g: g.get_vehicle_vin(),
        "serial":          lambda g: g.get_serial_number(),
        "hardware_type":   lambda g: g.get_hardware_type(),
        "supplier":        lambda g: g.get_supplier_id(),
        "diag_address":    lambda g: g.get_diagnostic_address(),
        "build_date":      lambda g: g.get_build_date(),
        "programming_date": lambda g: g.get_programming_date_me96(),
        "main_os":         lambda g: g.get_main_os(),
        "engine_calib":    lambda g: g.get_engine_calib(),
        "system_calib":    lambda g: g.get_system_calib(),
        "speedo_calib":    lambda g: g.get_speedo_calib(),
        "slave_os":        lambda g: g.get_slave_os(),
        "top_speed":       lambda g: g.get_top_speed(),
        "radum":           lambda g: g.get_radum(),
        "pmc_w":           lambda g: g.get_pmc_w(),
        "saab_pn":         lambda g: g.get_saab_partnumber(),
        "end_pn":          lambda g: g.get_end_model_partnumber(),
        "base_pn":         lambda g: g.get_base_model_partnumber(),
        "calibration_set": lambda g: g.get_calibration_set(),
        "codefile_version": lambda g: g.get_codefile_version(),
        "diag_data_id":    lambda g: g.get_diagnostic_data_identifier(),
        "mfg_enable_counter": lambda g: g.get_manufacturers_enable_counter(),
        "tester_serial":   lambda g: g.get_tester_serial(),
        "bosch_enable_counter": lambda g: g.get_bosch_enable_counter(),
    }

    def read_ecu_info(self) -> Dict[str, str]:
        """Read and return ECU identification data for supported PIDs only."""
        if not self.gmlan:
            raise RuntimeError("Not connected. Call connect() first.")

        protocol_info_reader = getattr(self.gmlan, "read_ecu_info", None)
        if callable(protocol_info_reader) and type(self.gmlan).__module__.startswith("protocols."):
            return dict(protocol_info_reader())

        # Ensure ECU is in diagnostic session so it responds to $1A PID requests
        self.gmlan.enter_programming_mode()

        supported = self.ecu.get_info_pids()
        info: Dict[str, str] = {}

        for key in supported:
            fetcher = self._INFO_DISPATCH.get(key)
            if fetcher:
                info[key] = fetcher(self.gmlan)

        return info

    # ── Pre-flash verification ───────────────────────────────────────

    def verify_pre_flash(self, raw: bytes, write_start: int, write_end: int) -> bool:
        """
        Verify file against ECU before flashing.

        Checks:
        1. File is not empty (all 0xFF)
        2. Version numbers in file match the ECU (full images only)
        3. User confirms to proceed

        Only searches for version numbers within [write_start, write_end)
        so that PIDs outside the write region (e.g. Main OS in bootloader
        area) are not flagged as missing.

        Returns True if safe to flash.
        """
        if not self.gmlan:
            raise RuntimeError("Not connected. Call connect() first.")

        # 1. Check file isn't empty
        if all(b == 0xFF for b in raw):
            print("[FAIL] File is empty (all 0xFF). Nothing to flash.")
            app_logger.error("Pre-flash check failed: file is empty.")
            return False

        is_full_image = len(raw) == self.ecu.TOTAL_FLASH_SIZE

        # 2. Version compatibility check (full images only)
        verify_pids = self.ecu.get_verify_pids()
        if verify_pids and is_full_image:
            print("\nQuerying ECU for version info...")
            ecu_info = self.read_ecu_info()

            # Only check PIDs whose data falls within the write range
            write_data = raw[write_start:write_end]

            print("Verifying version compatibility...\n")
            all_ok = True
            for name, (pid, desc) in verify_pids.items():
                ecu_val_str = ecu_info.get(name, "Unknown")
                if ecu_val_str == "Unknown":
                    print(f"  [SKIP]  {desc}: not available from ECU")
                    continue
                try:
                    ecu_val = int(ecu_val_str)
                except ValueError:
                    print(f"  [SKIP]  {desc}: cannot parse '{ecu_val_str}'")
                    continue

                needle = ecu_val.to_bytes(4, 'big')
                offset = write_data.find(needle)
                if offset != -1:
                    actual_offset = write_start + offset
                    print(f"  [OK]    {desc}: {ecu_val} found at 0x{actual_offset:06X}")
                else:
                    print(f"  [WARN]  {desc}: {ecu_val} NOT found in write region!")
                    all_ok = False

            if not all_ok:
                print("\n  Some version numbers were NOT found in the write region.")
                print("  This file may be incompatible with the current ECU software.")
                print("  Flashing a mismatched calibration can damage the ECU!")
                if not self._confirm("  Flash anyway? [y/N]: "):
                    app_logger.info("Pre-flash verification aborted by user (version mismatch).")
                    return False
        elif not is_full_image:
            # Raw region file — can't verify versions, show ECU info for manual check
            print("\nQuerying ECU for version info...")
            ecu_info = self.read_ecu_info()
            for key in self.ecu.get_info_pids():
                print(f"  {key:25s} {ecu_info.get(key, '?')}")
            print(f"\n  Cannot verify version compatibility from a region-only file.")
            print(f"  Ensure this calibration is compatible with the ECU above.")
            if not self._confirm("  Proceed with flash? [y/N]: "):
                app_logger.info("Pre-flash verification aborted by user.")
                return False
        else:
            # Full image but no verify PIDs defined for this ECU
            print("\nQuerying ECU for version info...")
            ecu_info = self.read_ecu_info()
            for key in self.ecu.get_info_pids():
                print(f"  {key:25s} {ecu_info.get(key, '?')}")
            if not self._confirm("  Proceed with flash? [y/N]: "):
                return False

        app_logger.info("Pre-flash verification passed.")
        return True

    def _confirm(self, prompt: str) -> bool:
        """Ask user for y/N confirmation. Override for GUI support."""
        if self._confirmation_provider is not None:
            return bool(self._confirmation_provider.confirm(prompt))
        try:
            answer = input(prompt).strip().lower()
            return answer in ('y', 'yes')
        except (EOFError, KeyboardInterrupt):
            return False

    # ── Internal helpers ─────────────────────────────────────────────

    def _resolve_read_region(self, name: str) -> Tuple[int, int, str]:
        regions = self.ecu.get_flash_regions()
        if name not in regions:
            available = ", ".join(regions.keys())
            raise ValueError(f"Unknown region '{name}'. Available: {available}")
        return regions[name]

    def _resolve_write_region(self, name: str) -> Tuple[int, int, str]:
        regions = self.ecu.get_write_regions()
        if name not in regions:
            available = ", ".join(regions.keys())
            raise ValueError(f"Unknown region '{name}'. Available: {available}")
        return regions[name]

    def _gap_bytes(self, start: int, end: int) -> int:
        """Total bytes of gaps within a write range, for accurate progress."""
        total = 0
        for gap_start, gap_end in self.ecu.GAPS:
            overlap_start = max(start, gap_start)
            overlap_end = min(end, gap_end)
            if overlap_start < overlap_end:
                total += overlap_end - overlap_start
        return total

    def _enter_read_session(self) -> bool:
        """Wake up ECU, authenticate, then enter programming session for reading."""
        app_logger.info("Waking up ECU for read...")
        self.gmlan.wakeup_bus()

        self._report(1.0, "Authenticating...")
        if not self.gmlan.authenticate():
            app_logger.error("Security access denied.")
            return False

        self._report(2.0, "Entering programming session...")
        if not self.gmlan.enter_programming_mode():
            app_logger.warning("ECU denied or already in programming session.")

        app_logger.info("Read session ready.")
        return True

    def _enter_write_session(self) -> bool:
        """Enter programming session and set up write mode according to OEM log sequence.

        OEM log sequence:
        1. Wakeup bus (functional TesterPresent on 0x101)
        2. SecurityAccess seed/key (physical 0x7E0)
        3. StartSession $10 02 (functional 0x101)
        4. DisableNormalCommunication $28 (functional 0x101)
        5. ReportProgrammedState $A2 (functional 0x101)
        6. ProgrammingMode $A5 01 (functional 0x101)
        7. EnableProgrammingMode $A5 03 (functional 0x101)
        8. TesterPresent (functional 0x101)
        """
        self._report(0.0, "Waking up ECU...")
        app_logger.info("Waking up ECU bus...")
        self.gmlan.wakeup_bus()

        self._report(1.0, "Authenticating...")
        app_logger.info("Authenticating with ECU...")

        if not self.gmlan.authenticate():
            app_logger.error("Security access denied.")
            return False

        app_logger.info("Setting up programming session for write...")

        if not self.gmlan.enter_programming_mode():
            app_logger.warning("ECU denied or already in programming session.")

        if not self.gmlan.disable_normal_communication():
            app_logger.warning("Disable normal communication warning.")
        time.sleep(0.1)

        if not self.gmlan.report_programmed_state():
            app_logger.warning("Report programmed state warning.")
        time.sleep(0.5)

        if not self.gmlan.request_programming_mode_a501():
            app_logger.warning("Programming mode request A501 warning.")
        time.sleep(0.5)

        self.gmlan.enable_programming_mode_a503()
        time.sleep(0.5)

        self.gmlan.send_tester_present()
        self._last_tp_time = time.time()

        app_logger.info("Write session ready.")
        return True

    def _erase_flash(self, start: int = 0, end: int = 0) -> bool:
        gap_bytes = self._gap_bytes(start, end)
        erase_size = ((end - start) - gap_bytes) if end > start else self.ecu.ERASE_SIZE
        if (end - start) == 0x03E000:
            erase_size = 0x02E000  # Exact calibration download parameter from OEM log
        app_logger.info(f"Initiating download / erase session ({erase_size} bytes)...")

        start_time = time.time()
        if not self.gmlan.request_download(erase_size):
            app_logger.error("Flash RequestDownload failed.")
            return False

        delay = self.ecu.POST_ERASE_DELAY
        if delay > 0:
            app_logger.info(f"Waiting {delay}s for session to settle...")
            time.sleep(delay)

        elapsed = time.time() - start_time
        app_logger.info(f"Flash download session ready in {elapsed:.1f}s.")
        return True

    def _write_blocks(self, start: int, end: int, data: bytes) -> bool:
        block_size = self.ecu.WRITE_BLOCK_SIZE
        current_addr = start
        bytes_written = 0
        gap_bytes = self._gap_bytes(start, end)
        total = (end - start) - gap_bytes

        start_time = time.time()
        self._last_tp_time = time.time()

        while current_addr < end:
            current_addr = self.ecu.skip_gaps_forward(current_addr)
            if current_addr >= end:
                break

            remaining = end - current_addr
            chunk_len = min(block_size, remaining)

            if len(data) >= self.ecu.TOTAL_FLASH_SIZE:
                file_offset = current_addr
            else:
                file_offset = current_addr - start
            chunk = data[file_offset:file_offset + chunk_len]

            if not self.gmlan.write_memory_block(current_addr, chunk):
                app_logger.error(f"Write failed at 0x{current_addr:06X}.")
                return False

            self._keep_alive()

            current_addr += chunk_len
            bytes_written += chunk_len

            pct = 5.0 + (bytes_written / total) * 95.0
            elapsed = time.time() - start_time
            elapsed_m = int(elapsed // 60)
            elapsed_s = int(elapsed % 60)
            self._report(pct, f"0x{current_addr:06X} | {elapsed_m}m {elapsed_s}s")

        elapsed = time.time() - start_time
        elapsed_m = int(elapsed // 60)
        elapsed_s = int(elapsed % 60)
        app_logger.info(f"Write complete. {elapsed_m}m {elapsed_s}s")
        return True

    def _keep_alive(self):
        now = time.time()
        if now - self._last_tp_time >= 2.0 and self.gmlan:
            self.gmlan.send_tester_present()
            self._last_tp_time = now

    def _clear_bus_buffer(self):
        if hasattr(self.adapter, "flush_rx_buffer"):
            self.adapter.flush_rx_buffer()
        else:
            while True:
                rx_id, rx_data = self.adapter.read_frame(timeout_ms=10)
                if not rx_data:
                    break

    def _report(self, percent: float, message: str):
        self._progress_cb(percent, message)
