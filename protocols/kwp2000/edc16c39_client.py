"""Experimental physical KWP2000/ISO-TP client for EDC16C39.

Session parameters, security, areas, and phase ordering come from the
diagnostic specification. The 0x23/0x34/0x36 wire layouts follow the reverse-engineering
candidate contract and are deliberately not a physical-write release: the
application readiness gate remains closed until captured replay and recovery
evidence validates them on the supported hardware/software identities.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional

from adapters.base_adapter import BaseAdapter
from domain.cancellation import CancellationToken
from domain.clock import Clock, SystemClock
from domain.edc16c39 import Edc16Area
from domain.errors import (
    DiagnosticError,
    NegativeResponseError,
    SecurityAccessError,
    SessionError,
    TransportError,
)
from ecus.base_ecu import BaseECU
from protocols.base_protocol import DownloadParameters, ProtocolClient
from protocols.isotp.isotp_transport import ISOTPTransport
from protocols.kwp2000 import edc16c39_codec as codec
from protocols.kwp2000.edc16c39_programming import Edc16C39ProgrammingCoordinator


class Edc16ClientState(str, Enum):
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    PROGRAMMING = "programming"
    DOWNLOADING = "downloading"
    RESETTING = "resetting"
    RECOVERY_REQUIRED = "recovery-required"


class Edc16C39Client(Edc16C39ProgrammingCoordinator, ProtocolClient):
    """Strict EDC16C39 diagnostic client over normal-addressed ISO-TP."""

    def __init__(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        cancellation_token: Optional[CancellationToken] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        if adapter.is_simulation:
            raise ValueError("Edc16C39Client is for physical transports; use the semantic simulator")
        super().__init__(adapter, ecu)
        self._cancel = cancellation_token or CancellationToken()
        self._clock = clock or SystemClock()
        self.tp = ISOTPTransport(
            adapter,
            ecu.CAN_ID_TX,
            ecu.CAN_ID_RX,
            cancellation_token=self._cancel,
            clock=self._clock,
        )
        self._state = Edc16ClientState.CONNECTED
        self._security_attempts = 0
        self._security_retry_not_before = 0.0
        self._download_area: Optional[Edc16Area] = None
        self._download_address = 0
        self._block_counter = 1

    @property
    def state(self) -> Edc16ClientState:
        return self._state

    def prepare_read_session(self) -> bool:
        return self.authenticate() and self.enter_programming_mode() and self.send_tester_present()

    def prepare_programming_session(self) -> bool:
        return self.prepare_read_session()

    def enter_programming_mode(self) -> bool:
        self._require_connection()
        response = self._request(codec.start_programming_session(), 0x50, timeout_s=5.0)
        if response != b"\x50\x84":
            raise SessionError("EDC16 programming-session response did not echo mode 0x84")
        self._state = Edc16ClientState.PROGRAMMING
        return True

    def authenticate(self) -> bool:
        self._require_connection()
        policy = self.ecu.SECURITY_POLICY
        now = self._clock.monotonic()
        if now < self._security_retry_not_before:
            raise SecurityAccessError(
                "EDC16 SecurityAccess delay has not expired",
                level=policy.request_level,
                retry_after=self._security_retry_not_before - now,
            )
        if self._security_attempts >= policy.max_attempts_per_connection:
            raise SecurityAccessError(
                "EDC16 SecurityAccess attempt budget is exhausted",
                level=policy.request_level,
            )
        self._security_attempts += 1
        try:
            response = self._request(codec.request_seed(), 0x67, timeout_s=5.0)
            seed_bytes = codec.parse_seed(response)
            if not any(seed_bytes) and policy.zero_seed_means_unlocked:
                self._state = Edc16ClientState.AUTHENTICATED
                self._security_attempts = 0
                return True
            key = self.ecu.calculate_key(int.from_bytes(seed_bytes, "big"))
            key_bytes = key.to_bytes(policy.key_length, "big")
            key_response = self._request(codec.send_key(key_bytes), 0x67, timeout_s=5.0)
            if key_response != bytes((0x67, policy.request_level + 1)):
                raise SecurityAccessError(
                    "EDC16 key acknowledgement is malformed",
                    level=policy.request_level,
                )
        except NegativeResponseError as exc:
            retry_after = policy.required_delay_seconds if exc.nrc == 0x37 else None
            if retry_after is not None:
                self._security_retry_not_before = self._clock.monotonic() + retry_after
            raise SecurityAccessError(
                f"EDC16 SecurityAccess rejected with NRC 0x{exc.nrc:02X}",
                level=policy.request_level,
                nrc=exc.nrc,
                retry_after=retry_after,
            ) from exc
        self._security_attempts = 0
        self._state = Edc16ClientState.AUTHENTICATED
        return True

    def read_memory_by_address(
        self,
        address: int,
        size: int,
        timeout_s: float = 5.0,
    ) -> Optional[bytes]:
        if not 0 <= address < address + size <= self.ecu.TOTAL_FLASH_SIZE:
            raise ValueError("EDC16 read lies outside the configured flash image")
        response = self._request(codec.read_memory(address, size), 0x63, timeout_s=timeout_s)
        if len(response) != size + 1:
            raise DiagnosticError(
                f"EDC16 ReadMemoryByAddress expected {size} bytes, got {max(0, len(response) - 1)}"
            )
        return response[1:]

    def request_download(self, size: int) -> DownloadParameters:
        del size
        raise DiagnosticError(
            "EDC16 RequestDownload requires an explicit destination area; "
            "use the managed full-image programming workflow"
        )

    def _edc16_erase_area(self, area: Edc16Area) -> bool:
        try:
            response = self._request(
                codec.erase(area),
                0x71,
                timeout_s=self.ecu.ERASE_TIMEOUT,
                max_pending=80,
            )
            codec.parse_routine_result(response, codec.ERASE_ROUTINE, codec.ERASE_RESULT_CODE)
        except Exception:
            self._state = Edc16ClientState.RECOVERY_REQUIRED
            raise
        return True

    def _edc16_request_download_area(self, area: Edc16Area) -> DownloadParameters:
        response = self._request(
            codec.request_download(area),
            0x74,
            timeout_s=self.ecu.ERASE_TIMEOUT,
            max_pending=80,
        )
        maximum = codec.parse_download_parameters(response)
        self._download_area = area
        self._download_address = area.start
        self._block_counter = 1
        self._state = Edc16ClientState.DOWNLOADING
        return DownloadParameters(max_request_bytes=maximum, raw_response=response)

    def write_memory_block(self, address: int, data: bytes) -> bool:
        area = self._download_area
        if self._state is not Edc16ClientState.DOWNLOADING or area is None:
            raise DiagnosticError("EDC16 TransferData sent outside an active download")
        if address != self._download_address or address + len(data) > area.end:
            raise DiagnosticError("EDC16 TransferData address is not the next negotiated byte range")
        counter = self._block_counter
        response = self._request(
            codec.transfer_data(counter, data),
            0x76,
            timeout_s=self.ecu.WRITE_TIMEOUT,
            max_pending=40,
        )
        if response != bytes((0x76, counter)):
            raise DiagnosticError("EDC16 TransferData acknowledgement did not echo its block counter")
        self._download_address += len(data)
        self._block_counter = (counter + 1) & 0xFF
        return True

    def finalize_transfer(self) -> bool:
        area = self._download_area
        if area is None or self._download_address != area.end:
            raise DiagnosticError("EDC16 transfer cannot exit before the destination is complete")
        response = self._request(
            codec.request_transfer_exit(),
            0x77,
            timeout_s=self.ecu.WRITE_TIMEOUT,
            max_pending=40,
        )
        if response != b"\x77":
            raise DiagnosticError("EDC16 RequestTransferExit acknowledgement is malformed")
        self._download_area = None
        self._state = Edc16ClientState.PROGRAMMING
        return True

    def verify_flash_routine(self) -> bool:
        response = self._request(
            codec.verify_checksum(),
            0x71,
            timeout_s=self.ecu.ERASE_TIMEOUT,
            max_pending=80,
        )
        codec.parse_routine_result(response, codec.CHECKSUM_ROUTINE, codec.CHECKSUM_RESULT_CODE)
        return True

    def return_to_normal_mode(self) -> bool:
        self._state = Edc16ClientState.RESETTING
        response = self._request(codec.ecu_reset(), 0x51, timeout_s=5.0)
        if response != b"\x51\x01":
            raise DiagnosticError("EDC16 reset acknowledgement is malformed")
        self._download_area = None
        self._security_attempts = 0
        self._state = Edc16ClientState.CONNECTED
        return True

    def _edc16_wait_reconnect(self) -> bool:
        deadline = self._clock.monotonic() + self.ecu.P2_STAR_TIMEOUT_S
        while self._clock.monotonic() < deadline:
            if not self.adapter.is_connected():
                self._clock.sleep(0.1)
                continue
            try:
                response = self._request(codec.identify(), 0x5A, timeout_s=1.0)
            except (DiagnosticError, TransportError, TimeoutError):
                self._clock.sleep(0.1)
                continue
            if len(response) >= 2 and response[:2] == b"\x5A\x8A":
                self._state = Edc16ClientState.CONNECTED
                return True
        return False

    def send_tester_present(self) -> bool:
        response = self._request(codec.tester_present(), 0x7E, timeout_s=2.0)
        if response not in (b"\x7E", b"\x7E\x00"):
            raise DiagnosticError("EDC16 TesterPresent acknowledgement is malformed")
        return True

    def attempt_bootblock_recovery(self) -> bool:
        """OEM flash.pri bootblock recovery sequence: reset, re-authenticate, and resume programming session."""
        try:
            self.return_to_normal_mode()
        except Exception:
            pass
        self._edc16_wait_reconnect()
        self.authenticate()
        return self.enter_programming_mode()

    def read_ecu_info(self) -> Dict[str, str]:
        response = self._request(codec.identify(), 0x5A, timeout_s=5.0)
        if len(response) < 3 or response[:2] != b"\x5A\x8A":
            raise DiagnosticError("EDC16 identification response is malformed")
        payload = response[2:]
        printable = "".join(chr(value) if 0x20 <= value <= 0x7E else "." for value in payload)
        return {
            "edc16_local_id_8a_hex": payload.hex().upper(),
            "edc16_local_id_8a_ascii": printable,
        }

    def _request(
        self,
        payload: bytes,
        positive_sid: int,
        *,
        timeout_s: float,
        max_pending: int = 10,
    ) -> bytes:
        self._require_connection()
        if not self.tp.send_payload(payload):
            raise TransportError(f"failed to send EDC16 service 0x{payload[0]:02X}")
        deadline = self._clock.monotonic() + timeout_s
        pending = 0
        while self._clock.monotonic() < deadline:
            remaining = max(0.001, deadline - self._clock.monotonic())
            response = self.tp.receive_payload(timeout_s=min(remaining, self.ecu.P2_TIMEOUT_S))
            if response is None:
                continue
            if len(response) == 3 and response[0] == 0x7F:
                if response[1] != payload[0]:
                    raise DiagnosticError("EDC16 negative response references another service")
                if response[2] == 0x78:
                    pending += 1
                    if pending > max_pending:
                        raise DiagnosticError("EDC16 response-pending budget exceeded")
                    continue
                raise NegativeResponseError(payload[0], response[2])
            if not response or response[0] != positive_sid:
                raise DiagnosticError(
                    f"EDC16 service 0x{payload[0]:02X} returned an unexpected response"
                )
            return bytes(response)
        raise TimeoutError(f"EDC16 service 0x{payload[0]:02X} exceeded its absolute deadline")

    def _require_connection(self) -> None:
        if not self.adapter.is_connected():
            raise TransportError("EDC16 operation requires a connected adapter")
