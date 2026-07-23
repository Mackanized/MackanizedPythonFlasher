"""Trionic 7 KWP2000 row-framed CAN client."""

from __future__ import annotations

from enum import Enum
from typing import Callable, Dict, Optional

from adapters.base_adapter import BaseAdapter
from domain.cancellation import CancellationToken
from domain.clock import Clock, SystemClock
from domain.errors import (
    DiagnosticError,
    NegativeResponseError,
    SecurityAccessError,
    SessionError,
)
from ecus.base_ecu import BaseECU
from firmware.trionic.checksums import TrionicChecksumError, inspect_t7_checksums
from protocols.base_protocol import DownloadParameters, ProtocolClient
from protocols.trionic.codecs import KwpCanCodec
from protocols.trionic.transport import BoundedCanTransport


class T7State(str, Enum):
    CONNECTED = "connected"
    SESSION = "session"
    AUTHENTICATED = "authenticated"
    ERASED = "erased"
    DOWNLOADING = "downloading"
    VERIFIED = "verified"
    RECOVERY_REQUIRED = "recovery-required"


class Trionic7Client(ProtocolClient):
    """Strict row transport with a single identity-selected key variant."""

    def __init__(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        cancellation_token: Optional[CancellationToken] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        if adapter.is_simulation and not adapter.is_replay:
            raise ValueError("Trionic7Client requires a physical/replay transport")
        super().__init__(adapter, ecu)
        self._cancel = cancellation_token or CancellationToken()
        self._clock = clock or SystemClock()
        self._can = BoundedCanTransport(adapter, self._cancel, self._clock)
        self._state = T7State.CONNECTED
        self._download_start = 0
        self._download_size = 0
        self._download_offset = 0
        self._security_key_variant: Optional[int] = None

    @property
    def state(self) -> T7State:
        return self._state

    def enter_programming_mode(self) -> bool:
        self._can.require_connection()
        frame = KwpCanCodec.session_start()
        response = self._can.exchange(
            frame.can_id,
            frame.data,
            KwpCanCodec.SESSION_RESPONSE_ID,
            self.ecu.P2_TIMEOUT_S,
        )
        if not response:
            raise SessionError("T7 proprietary KWP session was not acknowledged")
        self._state = T7State.SESSION
        return True

    def authenticate(self) -> bool:
        if self._state is T7State.AUTHENTICATED:
            return True
        if self._state is T7State.CONNECTED:
            raise SessionError("T7 SecurityAccess requires the proprietary KWP session")
        # Tries all five known key-candidate methods in sequence, since
        # different physical T7 ECUs accept different candidates; stops at
        # the first one that's accepted. A lockout-indicating negative
        # response (0x36 exceeded attempts, 0x37 delay not expired) aborts
        # immediately instead of feeding it another live key attempt.
        last_error: Optional[Exception] = None
        for variant in range(5):
            try:
                response = self._request(0x27, b"\x05")
                if len(response) != 5 or response[1:3] != b"\x67\x05":
                    raise SecurityAccessError("T7 seed response is malformed", level=0x05)
                seed = int.from_bytes(response[3:5], "big")
                if seed == 0 and self.ecu.SECURITY_POLICY.zero_seed_means_unlocked:
                    self._state = T7State.AUTHENTICATED
                    self._security_key_variant = variant
                    return True
                key = self.ecu.candidate_keys(seed)[variant]
                accepted = self._request(0x27, b"\x06" + key.to_bytes(2, "big"))
                if len(accepted) >= 3 and accepted[1] == 0x67 and accepted[2] in (0x06, 0x34):
                    self._state = T7State.AUTHENTICATED
                    self._security_key_variant = variant
                    return True
                last_error = SecurityAccessError("T7 key was not acknowledged", level=0x05)
            except NegativeResponseError as exc:
                if exc.nrc in (0x36, 0x37):
                    raise
                if exc.nrc == 0x35:
                    last_error = exc
                    continue
                raise
        raise SecurityAccessError(f"T7 SecurityAccess failed for all five key variants: {last_error}", level=0x05)

    def prepare_read_session(self) -> bool:
        if self._state is T7State.AUTHENTICATED:
            return True
        if self._state is T7State.CONNECTED:
            self.enter_programming_mode()
        return self.authenticate()

    def prepare_programming_session(self) -> bool:
        return self.prepare_read_session() and self.send_tester_present()

    def read_memory_by_address(
        self, address: int, size: int, timeout_s: float = 5.0
    ) -> Optional[bytes]:
        if self._state is T7State.CONNECTED:
            raise SessionError("T7 memory read requires an authenticated KWP session")
        if not 0 < size <= 0xFF:
            raise ValueError("T7 row reader accepts 1..255 bytes per request")
        if not 0 <= address < address + size <= self.ecu.TOTAL_FLASH_SIZE:
            raise ValueError("T7 read lies outside the configured image")
        # The reference flasher first defines local identifier F0 using 2C,
        # then fetches it using 21 F0.
        define = b"\xF0\x03" + size.to_bytes(2, "big") + address.to_bytes(3, "big")
        configured = self._request(0x2C, define, timeout_s=timeout_s)
        if len(configured) < 3 or configured[1:3] != b"\x6C\xF0":
            raise DiagnosticError("T7 dynamic memory window was not accepted")
        fetched = self._request(0x21, b"\xF0", timeout_s=timeout_s)
        if len(fetched) != size + 3 or fetched[1:3] != b"\x61\xF0":
            raise DiagnosticError("T7 dynamic memory response is truncated")
        return fetched[3:]

    def request_download(self, size: int) -> DownloadParameters:
        del size
        raise DiagnosticError(
            "T7 RequestDownload requires an explicit primary/footer address; "
            "use managed full-image programming"
        )

    def _erase(self) -> None:
        if self._state is not T7State.AUTHENTICATED:
            raise SessionError("T7 erase requires SecurityAccess")
        try:
            # Poll-count bounded rather than capped by a shared wall-clock
            # ERASE_TIMEOUT: the actual erase routine (0x53) can legitimately
            # take far longer to complete than the EOL-session routine
            # (0x52), and giving up too early would abandon a real
            # in-progress erase, forcing an unnecessary recovery state.
            for routine, limit in ((0x52, 30), (0x53, 200)):
                polls = 0
                while True:
                    try:
                        result = self._request(0x31, bytes((routine,)), timeout_s=2.0)
                    except NegativeResponseError as exc:
                        if exc.nrc != 0x78:
                            raise
                        result = b""
                    # The pinned handler treats positive SID 0x71 as complete;
                    # not every software revision echoes the routine byte.
                    if len(result) >= 2 and result[1] == 0x71:
                        break
                    polls += 1
                    if polls > limit:
                        raise TimeoutError(f"T7 erase routine 0x{routine:02X} exceeded its retry budget")
                    self._clock.sleep(1.0)
            confirmation = None
            for _ in range(10):
                try:
                    confirmation = self._request(0x3E, b"\x53")
                    break
                except NegativeResponseError as exc:
                    if exc.nrc != 0x78:
                        raise
                    self._clock.sleep(1.0)
            if confirmation is None:
                raise TimeoutError("T7 erase confirmation exceeded its retry budget")
            if len(confirmation) < 2 or confirmation[1] != 0x7E:
                raise DiagnosticError("T7 erase confirmation is malformed")
        except Exception:
            self._state = T7State.RECOVERY_REQUIRED
            raise
        self._state = T7State.ERASED

    def _begin_download(self, address: int, size: int) -> DownloadParameters:
        if self._state not in {T7State.ERASED, T7State.DOWNLOADING}:
            raise SessionError("T7 download requested before erase")
        parameters = address.to_bytes(3, "big") + size.to_bytes(4, "big")
        response = self._request(0x34, parameters)
        if len(response) < 2 or response[1] != 0x74:
            raise DiagnosticError("T7 RequestDownload was not accepted")
        self._download_start = address
        self._download_size = size
        self._download_offset = 0
        self._state = T7State.DOWNLOADING
        # The row transport accepts 128-byte flash blocks in the reference.
        return DownloadParameters(max_request_bytes=0x81, raw_response=response)

    def write_memory_block(self, address: int, data: bytes) -> bool:
        if self._state is not T7State.DOWNLOADING:
            raise DiagnosticError("T7 TransferData sent outside an active region")
        expected = self._download_start + self._download_offset
        if address != expected or address + len(data) > self._download_start + self._download_size:
            raise DiagnosticError("T7 TransferData is not the next negotiated block")
        if not 0 < len(data) <= 0x80:
            raise ValueError("T7 TransferData block exceeds 0x80 bytes")
        response = self._request(0x36, bytes(data), timeout_s=self.ecu.WRITE_TIMEOUT)
        if len(response) < 2 or response[1] != 0x76:
            raise DiagnosticError("T7 TransferData acknowledgement is malformed")
        self._download_offset += len(data)
        return True

    def finalize_transfer(self) -> bool:
        if self._state is not T7State.DOWNLOADING:
            return False
        if self._download_offset != self._download_size:
            raise DiagnosticError("T7 region transfer is incomplete")
        return True

    def verify_flash_routine(self) -> bool:
        if self._state not in {T7State.DOWNLOADING, T7State.VERIFIED}:
            raise DiagnosticError("T7 verification requested outside programming")
        self._state = T7State.VERIFIED
        return True

    def return_to_normal_mode(self) -> bool:
        if self._state is T7State.CONNECTED:
            return True
        response = self._request(0x82, b"\x00")
        if len(response) < 2 or response[1] != 0xC2:
            raise DiagnosticError("T7 stop-session response is malformed")
        self._state = T7State.CONNECTED
        return True

    def send_tester_present(self) -> bool:
        response = self._request(0x3E)
        if len(response) < 2 or response[1] != 0x7E:
            raise DiagnosticError("T7 TesterPresent response is malformed")
        return True

    def read_ecu_info(self) -> Dict[str, str]:
        if self._state is T7State.CONNECTED:
            self.enter_programming_mode()
        result: Dict[str, str] = {}
        for name, pid in (("vin", 0x90), ("hardware_type", 0x97)):
            response = self._request(0x1A, bytes((pid,)))
            if len(response) >= 3 and response[1:3] == bytes((0x5A, pid)):
                result[name] = response[3:].decode("ascii", errors="replace").strip("\x00 ")
        if result.get("vin") or result.get("hardware_type"):
            result["ecu_family"] = self.ecu.NAME
        if self._security_key_variant is not None:
            result["security_key_variant"] = str(self._security_key_variant)
        return result

    def enter_recovery_mode(self) -> bool:
        self._can.require_connection()
        if self._state is T7State.CONNECTED:
            self.enter_programming_mode()
        if self._state is T7State.SESSION:
            return self.authenticate()
        return self._state in {
            T7State.AUTHENTICATED,
            T7State.ERASED,
            T7State.DOWNLOADING,
            T7State.VERIFIED,
        }

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
            raise ValueError("T7 managed programming requires one exact 512 KiB image")
        try:
            checksum = inspect_t7_checksums(data)
        except TrionicChecksumError as exc:
            raise DiagnosticError(f"T7 firmware structure rejected: {exc}") from exc
        if not checksum.valid:
            raise DiagnosticError(checksum.reason)
        progress_callback(0.0, "Starting T7 KWP session and SecurityAccess")
        self.prepare_programming_session()
        with self._cancel.defer_interrupts():
            try:
                progress_callback(3.0, "Running T7 erase routines 0x52 and 0x53")
                self._erase()
                # Derived from the ECU profile rather than hardcoded so the
                # protected-gap partition can never silently drift out of sync
                # with what actually gets written.
                ranges = tuple((r.start, r.end_exclusive) for r in self.ecu.PROFILE.writable_ranges)
                if not ranges:
                    raise DiagnosticError("T7 profile declares no writable ranges")
                total = sum(end - start for start, end in ranges)
                written = 0
                for start, end in ranges:
                    self._begin_download(start, end - start)
                    for address in range(start, end, 0x80):
                        chunk = data[address:min(end, address + 0x80)]
                        self.write_memory_block(address, chunk)
                        written += len(chunk)
                        progress_callback(5.0 + 75.0 * written / total, f"T7 0x{address:06X}")
                    self.finalize_transfer()
                progress_callback(82.0, "Reading T7 programmed regions back")
                verified = 0
                for start, end in ranges:
                    for address in range(start, end, 0x40):
                        chunk = data[address:min(end, address + 0x40)]
                        actual = self.read_memory_by_address(address, len(chunk))
                        if actual != chunk:
                            raise DiagnosticError(f"T7 readback mismatch at 0x{address:06X}")
                        verified += len(chunk)
                        progress_callback(82.0 + 17.0 * verified / total, f"T7 verify 0x{address:06X}")
                self.verify_flash_routine()
                self.return_to_normal_mode()
            except Exception:
                if self._state in {T7State.ERASED, T7State.DOWNLOADING}:
                    self._state = T7State.RECOVERY_REQUIRED
                raise
        progress_callback(100.0, "T7 programming and readback complete")
        return True

    def _request(self, service: int, parameters: bytes = b"", timeout_s: Optional[float] = None) -> bytes:
        self._can.require_connection()
        transaction_timeout = timeout_s or self.ecu.P2_TIMEOUT_S
        deadline = self._clock.monotonic() + transaction_timeout

        def remaining() -> float:
            value = deadline - self._clock.monotonic()
            if value <= 0:
                raise TimeoutError(f"T7 service 0x{service:02X} exceeded its absolute deadline")
            return value

        request = KwpCanCodec.request(service, parameters)
        for row in KwpCanCodec.encode_request_rows(request):
            self._can.send(row.can_id, row.data)
        first = self._can.receive(KwpCanCodec.RESPONSE_ID, remaining())
        count = (first[0] & 0x3F) + 1
        rows = [first]
        self._can.send(
            KwpCanCodec.ACK_ID,
            KwpCanCodec.acknowledgement(count - 1).data,
        )
        for row_remaining in range(count - 1, 0, -1):
            rows.append(self._can.receive(KwpCanCodec.RESPONSE_ID, remaining()))
            self._can.send(
                KwpCanCodec.ACK_ID,
                KwpCanCodec.acknowledgement(row_remaining - 1).data,
            )
        try:
            decoded = KwpCanCodec.decode_response_rows(rows)
        except ValueError as exc:
            raise DiagnosticError(f"T7 KWP row response malformed: {exc}") from exc
        if len(decoded) >= 4 and decoded[1] == 0x7F:
            if decoded[2] != service:
                raise DiagnosticError("T7 negative response references another service")
            raise NegativeResponseError(service, decoded[3])
        expected = (service + 0x40) & 0xFF
        if len(decoded) < 2 or decoded[1] != expected:
            raise DiagnosticError(
                f"T7 service 0x{service:02X} returned an unexpected positive SID"
            )
        return decoded
