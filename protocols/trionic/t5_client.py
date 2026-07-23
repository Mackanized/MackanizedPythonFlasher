"""Trionic 5.2/5.5 native CAN SRAM-loader client.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Dict, Iterator, Optional, Tuple

from adapters.base_adapter import BaseAdapter
from domain.cancellation import CancellationToken
from domain.clock import Clock, SystemClock
from domain.errors import DiagnosticError
from domain.trionic_firmware import inspect_t5_checksum
from ecus.base_ecu import BaseECU
from firmware.trionic.loaders import LoaderCatalog
from protocols.base_protocol import DownloadParameters, ProtocolClient
from protocols.trionic.codecs import EncodedCanFrame, T5CommandCodec
from protocols.trionic.transport import BoundedCanTransport


class T5State(str, Enum):
    CONNECTED = "connected"
    LOADER_ACTIVE = "loader-active"
    ERASED = "erased"
    PROGRAMMING = "programming"
    VERIFIED = "verified"
    RECOVERY_REQUIRED = "recovery-required"


def _parse_s_records(payload: bytes) -> Iterator[Tuple[str, int, bytes]]:
    """Yield ``(kind, address, data)`` from an integrity-checked S-record."""
    for line in payload.decode("ascii").splitlines():
        if not line:
            continue
        kind = line[1]
        if kind not in "123789":
            continue
        record = bytes.fromhex(line[2:])
        address_length = {"1": 2, "2": 3, "3": 4, "7": 4, "8": 3, "9": 2}[kind]
        address = int.from_bytes(record[1:1 + address_length], "big")
        data = record[1 + address_length:-1] if kind in "123" else b""
        yield kind, address, data


class Trionic5Client(ProtocolClient):
    GENERAL_TIMEOUT_S = 1.0
    ERASE_TIMEOUT_S = 60.0
    CHECKSUM_TIMEOUT_S = 10.0

    def __init__(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        cancellation_token: Optional[CancellationToken] = None,
        clock: Optional[Clock] = None,
    ) -> None:
        if adapter.is_simulation and not adapter.is_replay:
            raise ValueError("Trionic5Client requires a physical/replay transport")
        super().__init__(adapter, ecu)
        self._cancel = cancellation_token or CancellationToken()
        self._clock = clock or SystemClock()
        self._can = BoundedCanTransport(adapter, self._cancel, self._clock)
        self._state = T5State.CONNECTED
        self._download_address: Optional[int] = None

    @property
    def state(self) -> T5State:
        return self._state

    def enter_programming_mode(self) -> bool:
        self._can.require_connection()
        if self._state is T5State.LOADER_ACTIVE:
            return True
        loader = LoaderCatalog().get("t5-loader").read_verified()
        begin = self._exchange(T5CommandCodec.begin_upload())
        self._require_ack(begin, 0xA5, "loader begin")
        start_vector = None
        for kind, address, data in _parse_s_records(loader):
            if kind in "123":
                self._upload_record(address, data)
            else:
                start_vector = address
        if start_vector is None:
            raise DiagnosticError("T5 loader contains no start-vector record")
        response = self._exchange(T5CommandCodec.start(start_vector))
        self._require_ack(response, 0xC1, "loader start")
        self._state = T5State.LOADER_ACTIVE
        return True

    def _upload_record(self, address: int, data: bytes) -> None:
        if not data or len(data) > 0xFF:
            raise DiagnosticError("T5 S-record data length is outside the A5 contract")
        self._require_ack(
            self._exchange(T5CommandCodec.address(address, len(data))),
            0xA5,
            "loader address",
        )
        for offset in range(0, len(data), 7):
            self._cancel_if_safe("during T5 loader upload")
            frame = T5CommandCodec.data(offset, data[offset:offset + 7])
            self._require_ack(self._exchange(frame), offset, "loader data")

    def authenticate(self) -> bool:
        # T5 access is provided by the uploaded SRAM loader, not SID 0x27.
        return self.enter_programming_mode()

    def prepare_read_session(self) -> bool:
        return self.enter_programming_mode()

    def prepare_programming_session(self) -> bool:
        return self.enter_programming_mode()

    def read_memory_by_address(
        self, address: int, size: int, timeout_s: float = 5.0
    ) -> Optional[bytes]:
        if self._state not in {T5State.LOADER_ACTIVE, T5State.PROGRAMMING, T5State.VERIFIED}:
            raise DiagnosticError("T5 flash read requires the SRAM loader")
        if size == 0:
            return b""
        if not 0 <= address < address + size <= self.ecu.TOTAL_FLASH_SIZE:
            raise ValueError("T5 read lies outside the configured image")
        output = bytearray()
        physical = self.ecu.PROFILE.physical_flash_base + address
        full_groups, tail = divmod(size, 6)
        for index in range(full_groups):
            self._cancel_if_safe("during T5 read")
            response = self._exchange(
                T5CommandCodec.read(physical + index * 6 + 5),
                timeout_s=min(timeout_s, self.GENERAL_TIMEOUT_S),
            )
            try:
                output.extend(T5CommandCodec.decode_six_byte_response(response))
            except ValueError as exc:
                raise DiagnosticError("T5 C7 response is not one classic-CAN frame") from exc
        if tail:
            self._cancel_if_safe("during T5 read")
            response = self._exchange(
                T5CommandCodec.read(physical + size - 1),
                timeout_s=min(timeout_s, self.GENERAL_TIMEOUT_S),
            )
            try:
                output.extend(T5CommandCodec.decode_six_byte_response(response)[-tail:])
            except ValueError as exc:
                raise DiagnosticError("T5 C7 tail response is not one classic-CAN frame") from exc
        return bytes(output)

    def request_download(self, size: int) -> DownloadParameters:
        if size != self.ecu.TOTAL_FLASH_SIZE:
            raise DiagnosticError("T5 erase is a whole-device operation")
        if self._state is not T5State.LOADER_ACTIVE:
            raise DiagnosticError("T5 erase requires an active SRAM loader")
        response = self._exchange(T5CommandCodec.erase(), timeout_s=self.ERASE_TIMEOUT_S)
        self._require_ack(response, 0xC0, "flash erase")
        self._state = T5State.ERASED
        self._download_address = 0
        return DownloadParameters(max_request_bytes=0x80, raw_response=response)

    def write_memory_block(self, address: int, data: bytes) -> bool:
        if self._state not in {T5State.ERASED, T5State.PROGRAMMING}:
            raise DiagnosticError("T5 data sent before a confirmed erase")
        if not 0 < len(data) <= 0x80 or address % 0x80:
            raise ValueError("T5 blocks must be aligned and no larger than 0x80 bytes")
        if self._download_address is not None and address < self._download_address:
            raise DiagnosticError("T5 block addresses must be monotonically increasing")
        if address + len(data) > self.ecu.TOTAL_FLASH_SIZE:
            raise ValueError("T5 write exceeds the configured image")
        physical = self.ecu.PROFILE.physical_flash_base + address
        self._require_ack(
            self._exchange(T5CommandCodec.address(physical, len(data))),
            0xA5,
            "flash block address",
        )
        for offset in range(0, len(data), 7):
            frame = T5CommandCodec.data(offset, data[offset:offset + 7])
            self._require_ack(self._exchange(frame), offset, "flash data")
        self._download_address = address + len(data)
        self._state = T5State.PROGRAMMING
        return True

    def finalize_transfer(self) -> bool:
        return self._state is T5State.PROGRAMMING

    def verify_flash_routine(self) -> bool:
        if self._state is not T5State.PROGRAMMING:
            raise DiagnosticError("T5 checksum requested outside programming")
        response = self._exchange(T5CommandCodec.checksum(), timeout_s=self.CHECKSUM_TIMEOUT_S)
        self._require_ack(response, 0xC8, "ECU checksum")
        self._state = T5State.VERIFIED
        return True

    def return_to_normal_mode(self) -> bool:
        if self._state is T5State.CONNECTED:
            return True
        response = self._exchange(T5CommandCodec.reset())
        # Some loader builds return six useful bytes for C2; when a full
        # status frame is present it must pass the normal echo/status check.
        if len(response) == 8 and response[0] == 0xC2 and response[1] != 0:
            raise DiagnosticError("T5 reset returned a failure status")
        self._state = T5State.CONNECTED
        self._download_address = None
        return True

    def send_tester_present(self) -> bool:
        # The native loader has no tester-present command. C8 is destructive
        # to timing and is not used as a keepalive; successful active state is
        # the only honest answer here.
        return self._state is not T5State.CONNECTED

    def read_ecu_info(self) -> Dict[str, str]:
        self._can.require_connection()
        self.enter_programming_mode()
        raw = self._exchange(T5CommandCodec.chip_types())
        try:
            chip_info = T5CommandCodec.decode_six_byte_response(raw)
        except ValueError as exc:
            raise DiagnosticError("T5 C9 chip identity response is malformed") from exc
        chip_id = chip_info[0]
        manufacturer = chip_info[1]
        physical_base = int.from_bytes(chip_info[2:6], "little")
        chip_sizes = {
            0xB8: 0x20000,
            0x5D: 0x20000,
            0x25: 0x20000,
            0xD5: 0x40000,
            0xB5: 0x40000,
            0xB4: 0x40000,
            0xA7: 0x40000,
            0xA4: 0x40000,
            0x20: 0x40000,
        }
        size = chip_sizes.get(chip_id, self.ecu.TOTAL_FLASH_SIZE)
        if size == 0x20000 and physical_base == 0x60000:
            family = "Trionic 5.2"
        elif size == 0x40000 and physical_base in (0x40000, 0x60000):
            family = "Trionic 5.5"
        else:
            raise DiagnosticError(
                f"Unknown T5 flash identity chip=0x{chip_id:02X}, base=0x{physical_base:X}"
            )
        return {
            "ecu_family": family,
            "flash_chip_id": f"0x{chip_id:02X}",
            "flash_manufacturer_id": f"0x{manufacturer:02X}",
            "flash_image_size": f"0x{size:X}",
            "physical_flash_base": f"0x{physical_base:X}",
            "identity_status": "live C9 flash-chip identity",
        }

    def enter_recovery_mode(self) -> bool:
        self._can.require_connection()
        if self._state in {
            T5State.LOADER_ACTIVE,
            T5State.ERASED,
            T5State.PROGRAMMING,
            T5State.VERIFIED,
        }:
            self._exchange(T5CommandCodec.chip_types())
            return True
        return self.enter_programming_mode()

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
            raise ValueError("T5 managed programming requires one exact full image")
        checksum = inspect_t5_checksum(data)
        if not checksum.valid:
            raise DiagnosticError(f"T5 programming checksum rejected: {checksum.reason}")
        progress_callback(0.0, "Uploading and starting verified T5 SRAM loader")
        self.prepare_programming_session()
        with self._cancel.defer_interrupts():
            try:
                progress_callback(4.0, "Erasing complete T5 flash")
                self.request_download(len(data))
                nonblank = [
                    address for address in range(0, len(data), 0x80)
                    if any(value != 0xFF for value in data[address:address + 0x80])
                ]
                for index, address in enumerate(nonblank, 1):
                    self.write_memory_block(address, data[address:address + 0x80])
                    progress_callback(5.0 + 75.0 * index / max(1, len(nonblank)), f"T5 0x{address:06X}")
                if not nonblank:
                    raise DiagnosticError("T5 image has no programmable blocks")
                self.finalize_transfer()
                progress_callback(82.0, "Running T5 loader checksum")
                self.verify_flash_routine()
                progress_callback(85.0, "Reading programmed T5 flash back")
                for address in range(0, len(data), 0x80):
                    expected = data[address:min(len(data), address + 0x80)]
                    actual = self.read_memory_by_address(address, len(expected))
                    if actual != expected:
                        raise DiagnosticError(f"T5 readback mismatch at 0x{address:06X}")
                progress_callback(99.0, "Resetting T5 ECU")
                self.return_to_normal_mode()
            except Exception:
                if self._state in {T5State.ERASED, T5State.PROGRAMMING}:
                    self._state = T5State.RECOVERY_REQUIRED
                raise
        progress_callback(100.0, "T5 programming and readback complete")
        return True

    def _exchange(self, frame: EncodedCanFrame, timeout_s: float = GENERAL_TIMEOUT_S) -> bytes:
        return self._can.exchange(frame.can_id, frame.data, T5CommandCodec.RESPONSE_ID, timeout_s)

    @staticmethod
    def _require_ack(response: bytes, echo: int, action: str) -> None:
        if not T5CommandCodec.acknowledgement_ok(response, echo):
            raise DiagnosticError(f"T5 {action} acknowledgement/status mismatch")

    def _cancel_if_safe(self, context: str) -> None:
        if self._cancel.should_interrupt:
            from domain.errors import OperationCancelled
            raise OperationCancelled(f"Operation cancelled {context}")
