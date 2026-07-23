"""Trionic 8 GMLAN bootstrap, SRAM loader, read, write, and recovery client."""

from __future__ import annotations

from enum import Enum
from typing import Callable, Dict, Optional

from adapters.base_adapter import BaseAdapter
from domain.cancellation import CancellationToken
from domain.clock import Clock, SystemClock
from domain.errors import DiagnosticError, NegativeResponseError, SessionError, TransportError
from domain.trionic_firmware import t8_last_used_address
from ecus.base_ecu import BaseECU
from firmware.trionic.checksums import TrionicChecksumError, inspect_t8_checksums
from firmware.trionic.loaders import LoaderCatalog
from protocols.base_protocol import DownloadParameters
from protocols.gmlan.gmlan_client import GMLANClient
from protocols.isotp.isotp_transport import ISOTPTransport
from protocols.trionic.codecs import Trionic8Codec


class T8State(str, Enum):
    CONNECTED = "connected"
    SESSION = "session"
    AUTHENTICATED = "authenticated"
    LOADER_ACTIVE = "loader-active"
    ERASED = "erased"
    PROGRAMMING = "programming"
    VERIFIED = "verified"
    RECOVERY_SESSION = "recovery-session"
    RECOVERY_REQUIRED = "recovery-required"


class Trionic8Client(GMLANClient):
    LOADER_ADDRESS = 0x00102400
    LOADER_ENTRY = 0x00102460
    ERASE_TIMEOUT_S = 120.0

    def __init__(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        cancellation_token: Optional[CancellationToken] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        if adapter.is_simulation and not adapter.is_replay:
            raise ValueError("Trionic8Client requires a physical/replay transport")
        super().__init__(adapter, ecu, cancellation_token=cancellation_token, clock=clock)
        self._state = T8State.CONNECTED
        self._loader_purpose: Optional[str] = None
        self._download_next = 0
        self._recovery_tp: Optional[ISOTPTransport] = None

    @property
    def state(self) -> T8State:
        return self._state

    def _require_connection(self) -> None:
        if not self.adapter.is_connected():
            raise TransportError("Trionic 8 operation requires a connected adapter")

    def enter_programming_mode(self) -> bool:
        self._require_connection()
        response = self._request(b"\x10\x02", 0x50)
        if response[:2] != b"\x50\x02":
            raise SessionError("T8 programming session did not echo subfunction 0x02")
        self._state = T8State.SESSION
        return True

    def authenticate(self) -> bool:
        result = super().authenticate()
        if result:
            self._state = T8State.AUTHENTICATED
        return result

    def prepare_read_session(self) -> bool:
        self._start_session_1081()
        return self._prepare_loader("read")

    def prepare_programming_session(self) -> bool:
        return self._prepare_loader("program")

    def _prepare_loader(self, purpose: str) -> bool:
        if self._state is T8State.LOADER_ACTIVE and self._loader_purpose == purpose:
            return True
        self.enter_programming_mode()
        self._expect(b"\x28", 0x68, "disable normal communication")
        self._expect(b"\xA2", 0xE2, "report programmed state")
        self._expect(b"\xA5\x01", 0xE5, "request programming mode")
        # A5/03 deliberately has no response in the pinned flow.
        if not self.tp.send_payload(b"\xA5\x03"):
            raise TransportError("T8 enable-programming-mode transmit failed")
        self._clock.sleep(0.05)
        self.send_tester_present()
        self.authenticate()
        self._clock.sleep(0.05)
        loader_id = "t8-stock-read" if purpose == "read" else "t8-stock-program"
        self._upload_loader(LoaderCatalog().get(loader_id).read_verified())
        self._clock.sleep(0.05)
        self._start_loader(self.LOADER_ENTRY)
        self._clock.sleep(0.10)
        self._loader_purpose = purpose
        self._state = T8State.LOADER_ACTIVE
        return True

    def _start_session_1081(self) -> None:
        """Reference reader sends 10 81 and expects a diagnostic negative response."""
        self._require_connection()
        if not self.tp.send_payload(b"\x10\x81"):
            raise TransportError("T8 10 81 preamble transmit failed")
        response = self.tp.receive_payload(timeout_s=2.0)
        if response is None:
            raise TimeoutError("T8 10 81 preamble returned no response")
        if not (len(response) >= 3 and response[:2] == b"\x7F\x10"):
            raise DiagnosticError("T8 10 81 preamble did not match the reference negative response")

    def _request(self, payload: bytes, positive_sid: int, timeout_s: float = 5.0) -> bytes:
        self._require_connection()
        if not self.tp.send_payload(payload):
            raise TransportError(f"T8 service 0x{payload[0]:02X} transmit failed")
        response = self._await_response(
            payload[0], positive_sid, timeout_s=timeout_s, max_pending=240
        )
        if response is None:
            raise DiagnosticError(f"T8 service 0x{payload[0]:02X} returned no response")
        return bytes(response)

    def _expect(self, payload: bytes, positive_sid: int, name: str) -> None:
        response = self._request(payload, positive_sid)
        if response[0] != positive_sid:
            raise DiagnosticError(f"T8 {name} acknowledgement is malformed")

    def _upload_loader(self, artifact: bytes, tp: Optional[ISOTPTransport] = None) -> None:
        transport = tp or self.tp
        if not transport.send_payload(b"\x34\x00\x00\x00\x00\x00"):
            raise TransportError("T8 SRAM RequestDownload transmit failed")
        response = self._receive_positive(transport, 0x34, 0x74, 5.0)
        if response[0] != 0x74:
            raise DiagnosticError("T8 SRAM RequestDownload was not accepted")
        address = self.LOADER_ADDRESS
        cursor = 0
        # The imported artifact is the exact upstream sequence of 34 seven-byte
        # CF payloads per group. ISO-TP consumes 234 meaningful bytes and pads
        # the final CF, so the last four bytes of each 238-byte source group are
        # transport padding and are intentionally skipped.
        for _ in range(70):
            source_group = artifact[cursor:cursor + 238]
            if len(source_group) != 238:
                raise DiagnosticError("T8 loader artifact ended inside a transfer group")
            self._send_loader_transfer(transport, address, source_group[:234])
            cursor += 238
            address += 234
        tail = artifact[cursor:]
        if len(tail) != 7:
            raise DiagnosticError("T8 loader artifact tail is not one seven-byte source frame")
        self._send_loader_transfer(transport, address, tail[:4])

    def _send_loader_transfer(self, transport: ISOTPTransport, address: int, data: bytes) -> None:
        payload = Trionic8Codec.transfer_header(address) + bytes(data)
        if not transport.send_payload(payload):
            raise TransportError(f"T8 loader transfer failed at 0x{address:08X}")
        response = self._receive_positive(transport, 0x36, 0x76, self.ecu.WRITE_TIMEOUT)
        if response != b"\x76":
            raise DiagnosticError(f"T8 loader transfer acknowledgement failed at 0x{address:08X}")

    def _start_loader(self, address: int, tp: Optional[ISOTPTransport] = None) -> None:
        transport = tp or self.tp
        payload = Trionic8Codec.transfer_header(address)
        if not transport.send_payload(payload):
            raise TransportError("T8 loader start transmit failed")
        response = self._receive_positive(transport, 0x36, 0x76, 5.0)
        if response != b"\x76":
            raise DiagnosticError("T8 loader start was not acknowledged")

    def _receive_positive(
        self,
        transport: ISOTPTransport,
        service: int,
        positive_sid: int,
        timeout_s: float,
    ) -> bytes:
        deadline = self._clock.monotonic() + timeout_s
        pending = 0
        while self._clock.monotonic() < deadline:
            response = transport.receive_payload(
                timeout_s=min(0.5, max(0.001, deadline - self._clock.monotonic()))
            )
            if response is None:
                continue
            if response[0] == positive_sid:
                return bytes(response)
            if len(response) == 3 and response[:2] == bytes((0x7F, service)):
                if response[2] == 0x78:
                    pending += 1
                    if pending > 240:
                        break
                    continue
                from domain.errors import NegativeResponseError
                raise NegativeResponseError(service, response[2])
            raise DiagnosticError(f"T8 service 0x{service:02X} returned an unexpected response")
        raise TimeoutError(f"T8 service 0x{service:02X} exceeded its absolute deadline")

    def read_memory_by_address(
        self, address: int, size: int, timeout_s: float = 5.0
    ) -> Optional[bytes]:
        if self._state not in {T8State.LOADER_ACTIVE, T8State.PROGRAMMING, T8State.VERIFIED}:
            raise SessionError("T8 stock-loader read requires an active SRAM loader")
        if not 0 < size <= 0x80:
            raise ValueError("T8 stock-loader reads are limited to 0x80 bytes")
        if not 0 <= address < address + size <= self.ecu.TOTAL_FLASH_SIZE:
            raise ValueError("T8 read lies outside the configured image")
        payload = b"\x21" + bytes((size,)) + address.to_bytes(3, "big") + b"\x00"
        response = self._request(payload, 0x61, timeout_s=timeout_s)
        if len(response) != size + 2 or response[1] != size:
            raise DiagnosticError("T8 stock-loader read response is malformed")
        return response[2:]

    def request_download(self, size: int) -> DownloadParameters:
        if self._state is not T8State.LOADER_ACTIVE or self._loader_purpose != "program":
            raise SessionError("T8 flash erase requires the programming SRAM loader")
        if size != sum(item.address_range.length for item in self.ecu.PROFILE.partitions if item.writable_by_stock_flow):
            raise DiagnosticError("T8 stock erase must target all application partitions")
        response = self._erase_application(self.tp)
        self._state = T8State.ERASED
        self._download_next = 0x020000
        return DownloadParameters(max_request_bytes=0xF0, raw_response=response)

    def _erase_application(self, transport: ISOTPTransport) -> bytes:
        if not transport.send_payload(b"\x34\x01\x00\x00\x00\x00"):
            raise TransportError("T8 application RequestDownload transmit failed")
        deadline = self._clock.monotonic() + self.ERASE_TIMEOUT_S
        pending = 0
        accept_ids = {transport.rx_id, self.ecu.CAN_ID_RX, 0x311}
        while self._clock.monotonic() < deadline:
            rx_id, frame = self.adapter.read_frame(
                timeout_ms=max(1, min(100, int((deadline - self._clock.monotonic()) * 1000)))
            )
            if not frame or rx_id not in accept_ids:
                continue
            payload = self._decode_single_frame(frame)
            if payload is None:
                continue
            if payload and payload[0] == 0x74:
                return payload
            if len(payload) == 3 and payload[:2] == b"\x7F\x34":
                if payload[2] == 0x78:
                    pending += 1
                    if pending > 240:
                        break
                    self._send_tester_present_raw(transport.tx_id)
                    continue
                raise NegativeResponseError(0x34, payload[2])
            raise DiagnosticError("T8 application erase returned an unexpected frame")
        raise TimeoutError("T8 application erase exceeded its absolute deadline")

    @staticmethod
    def _decode_single_frame(frame: bytes) -> Optional[bytes]:
        if not frame:
            return None
        if (frame[0] >> 4) != 0:
            return None
        length = frame[0] & 0x0F
        if length > 7 or length > len(frame) - 1:
            raise TransportError("Malformed ISO-TP single-frame response")
        return bytes(frame[1:1 + length])

    def _send_tester_present_raw(self, tx_id: int) -> None:
        if not self.adapter.send_frame(tx_id, b"\x01\x3E".ljust(8, b"\x00")):
            raise TransportError("T8 erase keepalive transmit failed")

    def write_memory_block(self, address: int, data: bytes) -> bool:
        if self._state not in {T8State.ERASED, T8State.PROGRAMMING}:
            raise DiagnosticError("T8 loader TransferData sent before confirmed erase")
        if address != self._download_next:
            raise DiagnosticError(
                f"T8 loader expected 0x{self._download_next:06X}, got 0x{address:06X}"
            )
        if not 0 < len(data) <= 0xEA or address + len(data) > self.ecu.TOTAL_FLASH_SIZE:
            raise ValueError("T8 stock-loader block lies outside its 0xEA-byte contract")
        response = self._request(
            Trionic8Codec.stock_transfer_payload(address, data),
            0x76,
            timeout_s=self.ecu.WRITE_TIMEOUT,
        )
        if response != b"\x76":
            raise DiagnosticError(f"T8 TransferData acknowledgement failed at 0x{address:06X}")
        self._download_next += len(data)
        self._state = T8State.PROGRAMMING
        return True

    def finalize_transfer(self) -> bool:
        # The stock SRAM loader has no 0x37 phase; each 0x36 block is committed
        # before its 0x76 response.
        return self._state is T8State.PROGRAMMING

    def verify_flash_routine(self) -> bool:
        if self._state is not T8State.PROGRAMMING:
            raise DiagnosticError("T8 verification requested outside programming")
        self._state = T8State.VERIFIED
        return True

    def send_tester_present(self) -> bool:
        response = self._request(b"\x3E", 0x7E, timeout_s=2.0)
        return response == b"\x7E"

    def return_to_normal_mode(self) -> bool:
        if self._state is T8State.CONNECTED:
            return True
        if not self.tp.send_payload(b"\x20"):
            raise TransportError("T8 loader-exit transmit failed")
        deadline = self._clock.monotonic() + 5.0
        response = None
        while self._clock.monotonic() < deadline:
            candidate = self.tp.receive_payload(
                timeout_s=min(0.5, max(0.001, deadline - self._clock.monotonic()))
            )
            if candidate and candidate[0] in (0x50, 0x60):
                response = candidate
                break
        if response is None:
            raise TimeoutError("T8 loader exit exceeded its absolute deadline")
        if response[0] not in (0x50, 0x60):
            raise DiagnosticError("T8 loader exit response is malformed")
        self._state = T8State.CONNECTED
        self._loader_purpose = None
        return True

    def read_ecu_info(self) -> Dict[str, str]:
        self._require_connection()
        if self._state is T8State.CONNECTED:
            self.enter_programming_mode()
        result: Dict[str, str] = {}
        for name, pid in (("vin", 0x90), ("hardware_type", 0x97), ("supplier", 0x92), ("serial", 0xB4)):
            response = self._request(bytes((0x1A, pid)), 0x5A)
            if len(response) >= 2 and response[1] == pid:
                result[name] = response[2:].decode("ascii", errors="replace").strip("\x00 ")
        if result.get("vin") or result.get("hardware_type"):
            result["ecu_family"] = self.ecu.NAME
        return result

    def enter_recovery_mode(self) -> bool:
        """Enter the reference 0x011/0x311 recovery session/security path."""
        self._require_connection()
        recovery = ISOTPTransport(
            self.adapter,
            0x011,
            0x311,
            cancellation_token=self._cancel,
            clock=self._clock,
        )
        if not recovery.send_payload(b"\x10\x02"):
            return False
        if self._receive_positive(recovery, 0x10, 0x50, 5.0)[:2] != b"\x50\x02":
            return False
        if not recovery.send_payload(b"\x28"):
            return False
        comm = self._receive_positive(recovery, 0x28, 0x68, 5.0)
        if comm[0] != 0x68:
            return False
        if not recovery.send_payload(b"\xA2"):
            return False
        state = self._receive_positive(recovery, 0xA2, 0xE2, 5.0)
        if len(state) > 1 and state[1] == 0:
            raise DiagnosticError("T8 recovery path reported a non-recovery programmed state")
        if not recovery.send_payload(b"\x28"):
            return False
        self._receive_positive(recovery, 0x28, 0x68, 5.0)
        if not recovery.send_payload(b"\xA5\x01"):
            return False
        self._receive_positive(recovery, 0xA5, 0xE5, 5.0)
        if not recovery.send_payload(b"\xA5\x03"):
            return False
        self._clock.sleep(0.10)
        if not recovery.send_payload(b"\x27\x01"):
            return False
        seed_response = self._receive_positive(recovery, 0x27, 0x67, 5.0)
        if len(seed_response) != 4 or seed_response[1] != 0x01:
            raise DiagnosticError("T8 recovery seed response is malformed")
        key = self.ecu.calculate_key(int.from_bytes(seed_response[2:], "big"))
        if not recovery.send_payload(b"\x27\x02" + key.to_bytes(2, "big")):
            return False
        accepted = self._receive_positive(recovery, 0x27, 0x67, 5.0)
        if accepted[:2] != b"\x67\x02":
            return False
        self._recovery_tp = recovery
        self._state = T8State.RECOVERY_SESSION
        return True

    def prepare_recovery_loader(self) -> bool:
        if self._state is not T8State.RECOVERY_SESSION or self._recovery_tp is None:
            self.enter_recovery_mode()
        if self._recovery_tp is None:
            return False
        self._upload_loader(LoaderCatalog().get("t8-stock-program").read_verified(), self._recovery_tp)
        self._clock.sleep(0.05)
        self._start_loader(self.LOADER_ENTRY, self._recovery_tp)
        self._loader_purpose = "program"
        self._state = T8State.LOADER_ACTIVE
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
            raise ValueError("T8 managed programming requires one exact 1 MiB image")
        try:
            checksum = inspect_t8_checksums(data)
        except TrionicChecksumError as exc:
            raise DiagnosticError(f"T8 firmware structure rejected: {exc}") from exc
        if not checksum.valid:
            raise DiagnosticError(checksum.reason)
        last_used = min(self.ecu.TOTAL_FLASH_SIZE, max(0x020000, t8_last_used_address(data)))
        # BlockManager in the reference uses integer division and an inclusive
        # last-block loop. Preserve that boundary so the final used block is
        # completely programmed, including its bytes beyond the 0x200 margin.
        program_end = min(
            self.ecu.TOTAL_FLASH_SIZE,
            0x020000 + (((last_used - 0x020000) // 0xEA) + 1) * 0xEA,
        )
        progress_callback(0.0, "Entering T8 programming session and uploading SRAM loader")
        self.prepare_programming_session()
        with self._cancel.defer_interrupts():
            try:
                progress_callback(4.0, "Erasing T8 application partitions")
                size = sum(
                    item.address_range.length
                    for item in self.ecu.PROFILE.partitions
                    if item.writable_by_stock_flow
                )
                self.request_download(size)
                address = 0x020000
                total = max(1, program_end - address)
                while address < program_end:
                    chunk = data[address:min(program_end, address + 0xEA)]
                    self.write_memory_block(address, chunk)
                    address += len(chunk)
                    progress_callback(5.0 + 75.0 * (address - 0x020000) / total, f"T8 0x{address:06X}")
                self.finalize_transfer()
                self.verify_flash_routine()
                progress_callback(82.0, "Switching to T8 read loader for readback")
                self.return_to_normal_mode()
                self.prepare_read_session()
                progress_callback(84.0, "Reading programmed T8 application back")
                address = 0x020000
                while address < program_end:
                    chunk = data[address:min(program_end, address + 0x80)]
                    actual = self.read_memory_by_address(address, len(chunk))
                    if actual != chunk:
                        raise DiagnosticError(f"T8 readback mismatch at 0x{address:06X}")
                    address += len(chunk)
                    progress_callback(82.0 + 17.0 * (address - 0x020000) / total, f"T8 verify 0x{address:06X}")
                self._state = T8State.VERIFIED
                self.return_to_normal_mode()
            except Exception:
                if self._state in {T8State.ERASED, T8State.PROGRAMMING}:
                    self._state = T8State.RECOVERY_REQUIRED
                raise
        progress_callback(100.0, "T8 programming and readback complete")
        return True
