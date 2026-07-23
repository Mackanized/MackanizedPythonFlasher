"""
GMLAN Protocol Client Implementation.
"""

from typing import Dict, Optional, Callable
from adapters.base_adapter import BaseAdapter
from ecus.base_ecu import BaseECU
from logger import can_logger, app_logger
from protocols.base_protocol import DownloadParameters, ProtocolClient
from protocols.isotp.isotp_transport import ISOTPTransport
from domain.cancellation import CancellationToken
from domain.clock import Clock, SystemClock
from domain.errors import (
    DiagnosticError,
    NegativeResponseError,
    OperationCancelled,
    SecurityAccessError,
    SessionError,
    TransportError,
)


class GMLANClient(ProtocolClient):
    """GMLAN (General Motors Local Area Network) protocol client."""

    def __init__(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        cancellation_token: Optional[CancellationToken] = None,
        clock: Optional[Clock] = None,
    ):
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
        self._security_attempts = 0
        self._security_retry_not_before = 0.0

    def send_functional_message(self, service_id: int, subfunction: Optional[int] = None) -> bool:
        payload = [0xFE]
        if subfunction is not None:
            payload.extend([0x02, service_id, subfunction])
        else:
            payload.extend([0x01, service_id])

        frame_data = bytes(payload).ljust(8, bytes([0xAA]))
        can_logger.info(f"TX | 0x101 | functional SID=0x{service_id:02X} len={len(frame_data)} payload=REDACTED")
        return self.tp.adapter.send_frame(0x101, frame_data)

    def wakeup_bus(self) -> bool:
        app_logger.debug("Sending Wakeup Pulse (Functional TesterPresent)...")
        if not self.send_functional_message(0x3E):
            return False
        self._clock.sleep(0.05)
        self.tp.receive_payload(timeout_s=0.2)
        return True

    def send_tester_present(self) -> bool:
        if not self.send_functional_message(0x3E):
            return False
        self.tp.receive_payload(timeout_s=0.2)
        return True

    def enter_programming_mode(self) -> bool:
        if not self.wakeup_bus():
            return False
        if not self.send_functional_message(0x10, 0x02):
            app_logger.error("[GMLAN] Failed to send Functional Programming Session request.")
            return False
        resp = self._await_response(0x10, 0x50, timeout_s=5.0)
        if resp and len(resp) >= 2 and resp[0] == 0x50 and resp[1] == 0x02:
            app_logger.info("[GMLAN] Programming Session Active.")
            return True
        raise SessionError("Programming-session acknowledgement was malformed or for the wrong subfunction")

    def prepare_programming_session(self) -> bool:
        """Strict ME9/GMLAN preparation sequence retained from trace-backed flow."""
        mandatory_steps = (
            ("bus wakeup", self.wakeup_bus),
            ("security access", self.authenticate),
            ("programming session", self.enter_programming_mode),
            ("disable normal communication", self.disable_normal_communication),
            ("report programmed state", self.report_programmed_state),
            ("request programming mode A5/01", self.request_programming_mode_a501),
            ("enable programming mode A5/03", self.enable_programming_mode_a503),
            ("tester present", self.send_tester_present),
        )
        for name, action in mandatory_steps:
            self._raise_if_cancelled(f"before {name}")
            if not action():
                app_logger.error(f"[GMLAN] Mandatory programming step failed: {name}.")
                return False
        return True

    def request_seed(self) -> Optional[int]:
        policy = self.ecu.SECURITY_POLICY
        if policy.request_level != self.ecu.SECURITY_LEVEL:
            raise SecurityAccessError(
                "ECU security policy level does not match SECURITY_LEVEL",
                level=self.ecu.SECURITY_LEVEL,
            )
        payload = bytes([0x27, policy.request_level])
        if not self.tp.send_payload(payload):
            raise SecurityAccessError("Failed to send SecurityAccess seed request", level=policy.request_level)
        try:
            resp = self._await_response(0x27, 0x67, timeout_s=5.0)
        except NegativeResponseError as exc:
            retry_after = None
            if exc.nrc == 0x37:
                retry_after = policy.required_delay_seconds
                self._security_retry_not_before = self._clock.monotonic() + retry_after
            raise SecurityAccessError(
                f"Security seed request rejected with NRC 0x{exc.nrc:02X}",
                level=policy.request_level,
                nrc=exc.nrc,
                retry_after=retry_after,
            ) from exc
        expected_length = 2 + policy.seed_length
        if not resp or len(resp) != expected_length or resp[1] != policy.request_level:
            raise SecurityAccessError(
                f"Security seed response malformed: expected level 0x{policy.request_level:02X} "
                f"and {policy.seed_length} seed bytes",
                level=policy.request_level,
            )
        return int.from_bytes(resp[2:], "big")

    def send_key(self, key: int) -> bool:
        policy = self.ecu.SECURITY_POLICY
        key_level = policy.request_level + 1
        key_bytes = key.to_bytes(policy.key_length, "big")
        payload = bytes([0x27, key_level]) + key_bytes
        if not self.tp.send_payload(payload):
            return False
        try:
            resp = self._await_response(0x27, 0x67, timeout_s=5.0)
        except NegativeResponseError as exc:
            raise SecurityAccessError(
                f"Security key rejected with NRC 0x{exc.nrc:02X}",
                level=policy.request_level,
                nrc=exc.nrc,
            ) from exc
        return resp is not None and len(resp) == 2 and resp[1] == key_level

    def authenticate(self) -> bool:
        policy = self.ecu.SECURITY_POLICY
        if self._clock.monotonic() < self._security_retry_not_before:
            raise SecurityAccessError(
                "SecurityAccess delay has not expired",
                level=policy.request_level,
                retry_after=max(0.0, self._security_retry_not_before - self._clock.monotonic()),
            )
        if self._security_attempts >= policy.max_attempts_per_connection:
            raise SecurityAccessError(
                "SecurityAccess attempt budget exhausted for this connection",
                level=policy.request_level,
            )
        self._security_attempts += 1
        seed = self.request_seed()

        if seed == 0 and policy.zero_seed_means_unlocked:
            self._security_attempts = 0
            app_logger.info("[GMLAN] ECU already unlocked (seed is 0x0000).")
            return True

        key = self.ecu.calculate_key(seed)
        app_logger.info(f"[GMLAN] Seed received (redacted), key computed (redacted).")

        if self.send_key(key):
            self._security_attempts = 0
            app_logger.info("[GMLAN] Security Access Granted!")
            return True

        app_logger.error("[GMLAN] Security Access Denied.")
        return False

    def read_memory_by_address(self, address: int, size: int, timeout_s: float = 5.0) -> Optional[bytes]:
        addr_len_identifier = getattr(self.ecu, 'ADDR_LEN_IDENTIFIER', 0x00)
        addr_bytes = address.to_bytes(4, 'big')[1:]
        size_bytes = size.to_bytes(2, 'big')
        payload = bytes([0x23, addr_len_identifier]) + addr_bytes + size_bytes

        if not self.tp.send_payload(payload):
            raise TransportError("Failed to send ReadMemoryByAddress request")

        resp = self._await_response(0x23, 0x63, timeout_s=timeout_s)
        if resp is None:
            raise DiagnosticError(f"ECU did not respond to ReadMemoryByAddress at 0x{address:06X}")
        expected_length = 5 + size
        if len(resp) != expected_length or resp[1:5] != payload[1:5]:
            raise DiagnosticError(
                f"ReadMemoryByAddress returned malformed/short data at 0x{address:06X}: "
                f"expected {expected_length} bytes, got {len(resp)}"
            )
        return resp[5:]

    def disable_normal_communication(self) -> bool:
        if not self.send_functional_message(0x28):
            return False
        return self._functional_positive(0x28, 0x68)

    def report_programmed_state(self) -> bool:
        if not self.send_functional_message(0xA2):
            return False
        return self._functional_positive(0xA2, 0xE2)

    def request_programming_mode_a501(self) -> bool:
        if not self.send_functional_message(0xA5, 0x01):
            return False
        return self._functional_positive(0xA5, 0xE5)

    def enable_programming_mode_a503(self) -> bool:
        return self.send_functional_message(0xA5, 0x03)

    def request_download(self, size: int) -> DownloadParameters:
        size_bytes = size.to_bytes(3, 'big')
        payload = bytes([0x34, 0x00]) + size_bytes

        if not self.tp.send_payload(payload):
            raise TransportError("Failed to send RequestDownload")

        resp = self._await_response(0x34, 0x74, timeout_s=self.ecu.ERASE_TIMEOUT, max_pending=40)
        if not resp or len(resp) < 3:
            raise DiagnosticError("RequestDownload positive response is truncated")
        length_bytes = (resp[1] >> 4) & 0x0F
        if length_bytes == 0 or len(resp) != 2 + length_bytes:
            raise DiagnosticError("RequestDownload maximum-block-length field is malformed")
        max_request_bytes = int.from_bytes(resp[2:], "big")
        if max_request_bytes <= self.ecu.TRANSFER_REQUEST_OVERHEAD:
            raise DiagnosticError("ECU negotiated an unusable TransferData request size")
        return DownloadParameters(max_request_bytes=max_request_bytes, raw_response=bytes(resp))

    def write_memory_block(self, address: int, data: bytes) -> bool:
        addr_bytes = address.to_bytes(4, 'big')[1:]
        payload = b"".join((bytes([0x36, 0x00]), addr_bytes, data))

        if not self.tp.send_payload(payload):
            raise TransportError(f"Failed to send TransferData block at 0x{address:06X}")

        resp = self._await_response(0x36, 0x76, timeout_s=self.ecu.WRITE_TIMEOUT, max_pending=20)
        expected_echo = bytes([0x76, 0x00]) + addr_bytes
        if resp != expected_echo:
            raise DiagnosticError(
                f"TransferData acknowledgement mismatch at 0x{address:06X}; "
                f"expected counter/address echo"
            )
        return True

    def finalize_transfer(self) -> bool:
        if not self.tp.send_payload(b"\x37"):
            raise TransportError("Failed to send RequestTransferExit")
        resp = self._await_response(0x37, 0x77, timeout_s=self.ecu.WRITE_TIMEOUT, max_pending=20)
        if resp != b"\x77":
            raise DiagnosticError("RequestTransferExit returned malformed acknowledgement")
        return True

    def verify_flash_routine(self) -> bool:
        app_logger.info("[GMLAN] Executing post-flash verification (ReportProgrammedState)...")
        if self.report_programmed_state():
            app_logger.info("[GMLAN] Post-flash verification PASSED (ECU programmed state valid).")
            return True
        app_logger.error("[GMLAN] Post-flash verification FAILED (ReportProgrammedState rejected).")
        return False

    def return_to_normal_mode(self) -> bool:
        return self.send_functional_message(0x20)

    def read_data_by_identifier(self, pid: int, timeout_s: float = 3.0) -> Optional[bytes]:
        payload = bytes([0x1A, pid])
        if not self.tp.send_payload(payload):
            return None

        try:
            resp = self._await_response(0x1A, 0x5A, timeout_s=timeout_s)
        except DiagnosticError as exc:
            app_logger.debug(f"[GMLAN] PID 0x{pid:02X} failed: {exc}")
            return None
        return resp[2:] if resp and len(resp) >= 2 and resp[1] == pid else None

    def _functional_positive(self, service_id: int, positive_sid: int) -> bool:
        return bool(self._await_response(service_id, positive_sid, timeout_s=3.0))

    def _await_response(
        self,
        service_id: int,
        positive_sid: int,
        *,
        timeout_s: float,
        max_pending: int = 10,
    ) -> Optional[bytes]:
        """Wait once for a diagnostic result using an absolute bounded deadline."""
        deadline = self._clock.monotonic() + timeout_s
        pending_count = 0
        while True:
            self._raise_if_cancelled(f"waiting for service 0x{service_id:02X}")
            remaining = deadline - self._clock.monotonic()
            if remaining <= 0:
                raise DiagnosticError(f"Service 0x{service_id:02X} exceeded its absolute deadline")
            response = self.tp.receive_payload(timeout_s=min(0.5, remaining))
            if response is None:
                continue
            if response[0] == positive_sid:
                return response
            if response[0] == 0x7F:
                if len(response) != 3:
                    raise DiagnosticError("Malformed negative diagnostic response")
                response_service, nrc = response[1], response[2]
                if response_service != service_id:
                    raise NegativeResponseError(response_service, nrc, "Negative response for unexpected service")
                if nrc == 0x78:
                    pending_count += 1
                    if pending_count > max_pending:
                        raise DiagnosticError(
                            f"Service 0x{service_id:02X} exceeded ResponsePending limit ({max_pending})"
                        )
                    continue
                raise NegativeResponseError(service_id, nrc)
            raise DiagnosticError(
                f"Unexpected response SID 0x{response[0]:02X} while waiting for 0x{positive_sid:02X}"
            )

    def _raise_if_cancelled(self, context: str) -> None:
        if self._cancel.should_interrupt:
            raise OperationCancelled(f"Operation cancelled {context}.")

    # ── PID Handlers ──────────────────────────────────────────────────

    _INFO_DISPATCH: Dict[str, Callable[['GMLANClient'], str]] = {
        "vin":                  lambda g: g._get_vin(),
        "serial":               lambda g: g._get_serial(),
        "hardware_type":        lambda g: g._get_pid_ascii(0x97),
        "supplier":             lambda g: g._get_pid_ascii(0x92),
        "diag_address":         lambda g: g._get_diag_addr(),
        "build_date":           lambda g: g._get_pid_ascii(0x0A),
        "programming_date":     lambda g: g._get_prog_date(),
        "main_os":              lambda g: g._get_part_num(0xC1),
        "engine_calib":         lambda g: g._get_part_num(0xC2),
        "system_calib":         lambda g: g._get_part_num(0xC3),
        "speedo_calib":         lambda g: g._get_part_num(0xC4),
        "slave_os":             lambda g: g._get_part_num(0xC5),
        "top_speed":            lambda g: g._get_top_speed(),
        "radum":                lambda g: g._get_single_byte(0x24),
        "pmc_w":                lambda g: g._get_scaled_word(0x2E),
        "saab_pn":              lambda g: g._get_part_num_4byte(0x7C),
        "end_pn":               lambda g: g._get_part_num_4byte(0xCB),
        "base_pn":              lambda g: g._get_part_num_4byte(0xCC),
        "calibration_set":      lambda g: g._get_pid_ascii(0x74),
        "codefile_version":     lambda g: g._get_pid_ascii(0x73),
        "diag_data_id":         lambda g: g._get_hex_word(0x9A),
        "mfg_enable_counter":   lambda g: g._get_single_byte(0xA0),
        "tester_serial":        lambda g: g._get_pid_ascii(0x98),
        "bosch_enable_counter": lambda g: g._get_hex_byte(0x70),
    }

    def read_ecu_info(self) -> Dict[str, str]:
        if not self.enter_programming_mode():
            raise DiagnosticError("Unable to enter the diagnostic session required for identification")
        try:
            supported = self.ecu.get_info_pids()
            info: Dict[str, str] = {}
            for key in supported:
                self._raise_if_cancelled("during identification")
                fetcher = self._INFO_DISPATCH.get(key)
                if fetcher:
                    info[key] = fetcher(self)
            return info
        finally:
            self.return_to_normal_mode()

    def _get_vin(self) -> str:
        data = self.read_data_by_identifier(0x90, timeout_s=3.0)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def _get_serial(self) -> str:
        data = self.read_data_by_identifier(0xB4)
        if not data:
            return "Unknown"
        if len(data) >= 16:
            return data[:16].decode('ascii', errors='ignore').strip('\x00')
        return data.hex(' ').upper()

    def _get_pid_ascii(self, pid: int) -> str:
        data = self.read_data_by_identifier(pid)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def _get_part_num(self, pid: int) -> str:
        data = self.read_data_by_identifier(pid)
        if not data:
            return "Unknown"
        if len(data) >= 16 and hasattr(self.ecu, 'FORMAT_C_SERIES_AS_ASCII'):
            s = data[:16].decode('ascii', errors='ignore').strip('\x00')
            return f"{s[:8]}-{s[8:]}" if len(s) >= 16 else s
        if len(data) >= 3:
            val = int.from_bytes(data, 'big')
            return str(val) if val != 0 else "Unknown"
        return "Unknown"

    def _get_part_num_4byte(self, pid: int) -> str:
        data = self.read_data_by_identifier(pid)
        if data and len(data) >= 4:
            return str(int.from_bytes(data[:4], 'big'))
        return "Unknown"

    def _get_diag_addr(self) -> str:
        data = self.read_data_by_identifier(0xB0)
        return f"0x{data[0]:02X}" if data else "Unknown"

    def _get_prog_date(self) -> str:
        data = self.read_data_by_identifier(0x99)
        if data and len(data) >= 4:
            y = f"{data[0]>>4:X}{data[0]&0x0F:X}{data[1]>>4:X}{data[1]&0x0F:X}"
            m = f"{data[2]>>4:X}{data[2]&0x0F:X}"
            d = f"{data[3]>>4:X}{data[3]&0x0F:X}"
            return f"{y}-{m}-{d}"
        return "Unknown"

    def _get_top_speed(self) -> str:
        data = self.read_data_by_identifier(0x02)
        if data and len(data) >= 2:
            val = (data[0] << 8) | data[1]
            return f"{val / 10:.1f} km/h"
        return "Unknown"

    def _get_single_byte(self, pid: int) -> str:
        data = self.read_data_by_identifier(pid)
        return str(data[0]) if data else "Unknown"

    def _get_scaled_word(self, pid: int) -> str:
        data = self.read_data_by_identifier(pid)
        if data and len(data) >= 2:
            val = (data[0] << 8) | data[1]
            return f"{val / 10:.1f}"
        return "Unknown"

    def _get_hex_word(self, pid: int) -> str:
        data = self.read_data_by_identifier(pid)
        if data and len(data) >= 2:
            return f"0x{data[0]:02X} 0x{data[1]:02X}"
        return "Unknown"

    def _get_hex_byte(self, pid: int) -> str:
        data = self.read_data_by_identifier(pid)
        return f"0x{data[0]:X}" if data else "Unknown"
