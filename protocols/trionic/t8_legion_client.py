"""Trionic 8 alternate bootloader ("Legion") live client.

EXPERIMENTAL — UNVALIDATED AGAINST REAL HARDWARE.

This is a direct port of a community-documented alternate T8 bootloader
protocol used for high-speed flash read/write and MCP (secondary
co-processor) access. It has not been exercised against a real ECU. In
particular :meth:`Trionic8LegionClient.erase_flash` and
:meth:`Trionic8LegionClient.write_flash` are destructive, hard-to-reverse
operations on physical hardware — do not run them against a real ECU
without independently re-verifying every frame this module sends, ideally
first against a bench ECU or a CAN trace from known-good hardware.

The wire protocol itself is a custom raw-CAN-frame command set spoken by
the uploaded loader once it is running — it is not ISO-TP and not KWP2000,
which is why this client talks to the adapter directly (``send_frame`` /
``read_frame``) for everything after ``bootstrap()`` instead of going
through :class:`~protocols.isotp.isotp_transport.ISOTPTransport`.

This class *composes* a private :class:`~protocols.trionic.t8_client.Trionic8Client`
rather than subclassing it. It only borrows that class's session/security
bootstrap mechanics (already hardware-validated by the stock read/write/
recovery flow — see ``bootstrap()`` for exactly which calls are reused);
it deliberately does not inherit that class's public API, since methods
like ``read_memory_by_address``, ``execute_managed_programming``, or
``enter_recovery_mode`` describe the *stock* loader's protocol and would
be actively misleading to expose on a client that talks a completely
different one once the alternate loader is running.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Callable, Optional, Tuple

from domain.errors import DiagnosticError, TransportError
from firmware.trionic.loaders import LoaderId, get_default_catalog
from firmware.trionic.t8_partitions import (
    erased_region,
    ff_block,
    get_current_block,
    mcp_is_byte_swapped,
    mcp_partition_md5,
    t8_main_partition_md5,
)
from protocols.gmlan.service_ids import (
    POSITIVE_DISABLE_NORMAL_COMMUNICATION,
    POSITIVE_PROGRAMMING_MODE,
    POSITIVE_REPORT_PROGRAMMED_STATE,
    POSITIVE_SECURITY_ACCESS,
    SID_DISABLE_NORMAL_COMMUNICATION,
    SID_PROGRAMMING_MODE,
    SID_REPORT_PROGRAMMED_STATE,
    SID_SECURITY_ACCESS,
    SUBFUNCTION_PROGRAMMING_MODE_ENABLE,
    SUBFUNCTION_PROGRAMMING_MODE_REQUEST,
)
from protocols.trionic.codecs import Trionic8Codec
from protocols.trionic.t8_client import Trionic8Client

ECU_TARGET_MCP = 5
ECU_TARGET_T8 = 6

LEGION_LOADER_ADDRESS = 0x00102400
LEGION_SECURITY_REQUEST_LEVEL = 0x01
_RAW_FRAME_LEN = 8

_DISABLE_NORMAL_COMMUNICATION = bytes((SID_DISABLE_NORMAL_COMMUNICATION,))
_REPORT_PROGRAMMED_STATE = bytes((SID_REPORT_PROGRAMMED_STATE,))
_PROGRAMMING_MODE_REQUEST = bytes((SID_PROGRAMMING_MODE, SUBFUNCTION_PROGRAMMING_MODE_REQUEST))
_PROGRAMMING_MODE_ENABLE = bytes((SID_PROGRAMMING_MODE, SUBFUNCTION_PROGRAMMING_MODE_ENABLE))


class LegionCommand(IntEnum):
    SET_INTER_FRAME_LATENCY = 0x00
    GET_CRC32 = 0x01
    GET_T8_MD5 = 0x02
    GET_T8_MCP_MD5 = 0x03
    START_SECONDARY_BOOTLOADER = 0x04
    MARRY_SECONDARY_PROCESSOR = 0x05
    READ_ADC_PIN = 0x06


class Trionic8LegionClient:
    """Live client for the alternate T8 bootloader. See module docstring."""

    def __init__(self, adapter, ecu, cancellation_token=None, clock=None) -> None:
        # Held purely as a toolkit for the shared session/security bootstrap
        # primitives (see module docstring) — never exposed or delegated to
        # wholesale.
        self._t8 = Trionic8Client(adapter, ecu, cancellation_token=cancellation_token, clock=clock)
        self.adapter = adapter
        self.ecu = ecu
        self._clock = self._t8._clock
        self._cancel = self._t8._cancel
        self._legion_running = False
        self._interframe_latency_us = 200

    @property
    def tp(self):
        return self._t8.tp

    @property
    def legion_running(self) -> bool:
        return self._legion_running

    def _require_connection(self) -> None:
        self._t8._require_connection()

    # ---- bootstrap -----------------------------------------------------

    def bootstrap(self) -> bool:
        """Enter programming mode, authenticate, upload, and start the
        alternate loader, then switch it into high-speed framing.

        The first five steps below (programming mode, disable normal
        communication, report programmed state, request/enable programming
        mode) are byte-identical to ``Trionic8Client._prepare_loader`` and
        already hardware-validated by that path; only the SecurityAccess
        level (0x01, not this ECU's normal 0xFD) and the uploaded artifact
        differ.
        """
        if self._legion_running and self.ping():
            return True
        self._require_connection()
        self._t8.enter_programming_mode()
        self._t8._expect(_DISABLE_NORMAL_COMMUNICATION, POSITIVE_DISABLE_NORMAL_COMMUNICATION, "disable normal communication")
        self._t8._expect(_REPORT_PROGRAMMED_STATE, POSITIVE_REPORT_PROGRAMMED_STATE, "report programmed state")
        self._t8._expect(_PROGRAMMING_MODE_REQUEST, POSITIVE_PROGRAMMING_MODE, "request programming mode")
        if not self.tp.send_payload(_PROGRAMMING_MODE_ENABLE):
            raise TransportError("T8 Legion enable-programming-mode transmit failed")
        self._clock.sleep(0.05)
        self._t8.send_tester_present()
        self._security_access_level(LEGION_SECURITY_REQUEST_LEVEL)
        self._clock.sleep(0.05)
        self._t8._upload_loader(get_default_catalog().get(LoaderId.T8_LEGION).read_verified())
        self._clock.sleep(0.05)
        # The alternate loader's entry point is its load base address itself
        # (no header offset), unlike the stock loader's LOADER_ENTRY = base + 0x60.
        self._t8._start_loader(LEGION_LOADER_ADDRESS)
        self._clock.sleep(0.5)
        self._legion_running = self.ping()
        if not self._legion_running:
            raise DiagnosticError("T8 Legion loader did not respond after start")
        self.enable_high_speed()
        return True

    def _security_access_level(self, request_level: int) -> None:
        response_level = request_level + 1
        if not self.tp.send_payload(bytes((SID_SECURITY_ACCESS, request_level))):
            raise TransportError("T8 Legion SecurityAccess seed request transmit failed")
        seed_response = self._t8._receive_positive(self.tp, SID_SECURITY_ACCESS, POSITIVE_SECURITY_ACCESS, 5.0)
        if len(seed_response) != 4 or seed_response[1] != request_level:
            raise DiagnosticError("T8 Legion SecurityAccess seed response is malformed")
        key = self.ecu.calculate_key(int.from_bytes(seed_response[2:], "big"), level=request_level)
        if not self.tp.send_payload(bytes((SID_SECURITY_ACCESS, response_level)) + key.to_bytes(2, "big")):
            raise TransportError("T8 Legion SecurityAccess key transmit failed")
        accepted = self._t8._receive_positive(self.tp, SID_SECURITY_ACCESS, POSITIVE_SECURITY_ACCESS, 5.0)
        if accepted[:2] != bytes((POSITIVE_SECURITY_ACCESS, response_level)):
            raise DiagnosticError("T8 Legion SecurityAccess key was rejected")

    # ---- raw framing -----------------------------------------------------

    def _send_raw(self, payload: bytes) -> None:
        if len(payload) > _RAW_FRAME_LEN:
            raise ValueError("T8 Legion raw frame exceeds 8 bytes")
        if not self.adapter.send_frame(self.ecu.CAN_ID_TX, payload.ljust(_RAW_FRAME_LEN, b"\x00")):
            raise TransportError("T8 Legion raw frame transmit failed")

    def _recv_raw(self, timeout_ms: int = 200) -> Optional[bytes]:
        accept_ids = {self.ecu.CAN_ID_RX}
        deadline = self._clock.monotonic() + timeout_ms / 1000.0
        while self._clock.monotonic() < deadline:
            remaining_ms = max(1, int((deadline - self._clock.monotonic()) * 1000))
            rx_id, frame = self.adapter.read_frame(timeout_ms=min(remaining_ms, timeout_ms))
            if frame and rx_id in accept_ids:
                return bytes(frame)
        return None

    # ---- loader-level commands --------------------------------------------

    def ping(self) -> bool:
        self._send_raw(bytes((0xEF, 0xBE, 0x00, 0x00, 0x00, 0x00, 0x33, 0x66)))
        response = self._recv_raw(timeout_ms=50)
        return response is not None and response[0] == 0xDE and response[1] == 0xAD

    def exit_loader(self) -> bool:
        self._send_raw(bytes((0x01, 0x20)))
        response = self._recv_raw(timeout_ms=400)
        ok = response is not None and response[0] == 0x01 and response[1] == 0x60
        if ok:
            self._legion_running = False
        return ok

    def enable_high_speed(self) -> None:
        self.idemand(LegionCommand.SET_INTER_FRAME_LATENCY, self._interframe_latency_us)

    def idemand(self, command: LegionCommand, wish: int = 0) -> bytes:
        payload = bytes((0x02, 0xA5, int(command) & 0xFF, 0x00, 0x00, 0x00, (wish >> 8) & 0xFF, wish & 0xFF))
        last_error: Optional[Exception] = None
        for _ in range(10):
            self._send_raw(payload)
            response = self._recv_raw(timeout_ms=200)
            if response is None:
                last_error = TimeoutError("T8 Legion command received no response")
                continue
            try:
                self._check_idemand_response(command, response)
                if command in (LegionCommand.GET_T8_MD5, LegionCommand.GET_T8_MCP_MD5):
                    data, _ = self.read_data_by_local_identifier(0x07, 0, 16)
                    return data
                if command == LegionCommand.GET_CRC32:
                    return response[4:8]
                if command == LegionCommand.READ_ADC_PIN:
                    return response[4:5]
                return b""
            except (_LegionRetryable, TimeoutError) as retryable:
                last_error = retryable
                self._clock.sleep(0.15)
                continue
        raise DiagnosticError(f"T8 Legion command {command!r} did not complete: {last_error}")

    @staticmethod
    def _check_idemand_response(command: LegionCommand, response: bytes) -> None:
        status = response[3]
        if command == LegionCommand.SET_INTER_FRAME_LATENCY:
            if status != 1:
                raise DiagnosticError("T8 Legion failed to set inter-frame latency")
            return
        if command in (LegionCommand.GET_CRC32, LegionCommand.GET_T8_MD5, LegionCommand.GET_T8_MCP_MD5):
            if status != 1:
                raise _LegionRetryable("not ready yet")
            return
        if command == LegionCommand.START_SECONDARY_BOOTLOADER:
            if status != 1:
                raise _LegionRetryable("secondary loader not ready yet")
            return
        if command == LegionCommand.MARRY_SECONDARY_PROCESSOR:
            if status == 0xFF:
                raise DiagnosticError("T8 Legion failed to start the secondary loader")
            if status == 0xFD:
                raise _LegionRetryable("retrying write")
            if status == 0xFE:
                raise _LegionRetryable("retrying format")
            if status != 1:
                raise _LegionRetryable("busy marrying")
            return
        if command == LegionCommand.READ_ADC_PIN and status != 1:
            raise _LegionRetryable("ADC read not ready yet")
        if status == 0xFF:
            raise DiagnosticError("T8 Legion loader reported failure")

    def read_data_by_local_identifier(
        self, pci: int, address: int, length: int
    ) -> Tuple[bytes, int]:
        """Returns (data, blocks_to_skip). ``blocks_to_skip`` is nonzero only
        when the loader reports a run of known-erased (0xFF) blocks instead
        of streaming them.
        """
        payload = bytes((pci, 0x21, length, (address >> 24) & 0xFF, (address >> 16) & 0xFF, (address >> 8) & 0xFF, address & 0xFF, 0x00))
        self._send_raw(payload)
        response = self._recv_raw(timeout_ms=200)
        if response is None:
            raise TimeoutError("T8 Legion ReadDataByLocalIdentifier timed out")
        if response[0] == 0x7E:
            raise DiagnosticError("T8 Legion got 0x7E in response to ReadDataByLocalIdentifier")
        if response == bytes(_RAW_FRAME_LEN):
            raise DiagnosticError("T8 Legion got a blank response to ReadDataByLocalIdentifier")
        if response[0] == 0x03 and response[1] == 0x7F and response[2] == 0x23:
            raise DiagnosticError("T8 Legion: no security access granted")
        if response[2] != 0x61 and response[1] != 0x61 and response == bytes((0x01, 0x7E, 0, 0, 0, 0, 0, 0)):
            raise DiagnosticError(f"T8 Legion incorrect ReadDataByLocalIdentifier response, byte 2 was 0x{response[2]:02X}")

        if length <= 4:
            return bytes(response[4:4 + length]), 0

        data = bytearray(length)
        data[:4] = response[4:8]
        received = 4
        if response[3] == 0x00:
            self._send_raw(bytes((0x30,)))
            seq = 0x21
            frames_needed = (length - 4 + 6) // 7
            for _ in range(frames_needed):
                frame = self._recv_raw(timeout_ms=400)
                if frame is None:
                    raise TimeoutError("T8 Legion ReadDataByLocalIdentifier continuation timed out")
                if frame[0] != seq:
                    raise DiagnosticError(
                        f"T8 Legion continuation frame out of sequence: got 0x{frame[0]:02X} expected 0x{seq:02X}"
                    )
                chunk = frame[1:8]
                take = min(len(chunk), length - received)
                data[received:received + take] = chunk[:take]
                received += take
                seq = 0x20 if seq >= 0x2F else seq + 1
            return bytes(data), 0

        # Loader tagged this run as pre-known 0xFF content — no continuation
        # frames follow; the response's 4th byte is how many blocks to skip.
        return bytes([0xFF]) * length, response[3]

    def read_flash_range(
        self,
        device: int,
        start_address: int,
        last_address: int,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> bytes:
        if not self._legion_running:
            raise DiagnosticError("T8 Legion loader is not running")
        buf = bytearray(b"\xFF" * last_address)
        block_size = 0x80
        pointer = (start_address // block_size) * block_size if start_address > block_size else 0
        while pointer < last_address:
            data, blocks_to_skip = self.read_data_by_local_identifier(device, pointer, block_size)
            if blocks_to_skip > 0:
                pointer += blocks_to_skip * block_size
            elif len(data) == block_size:
                buf[pointer:pointer + block_size] = data
                pointer += block_size
            else:
                raise DiagnosticError(f"T8 Legion dropped frame reading 0x{pointer:06X}")
            if progress_callback is not None:
                percent = 100.0 * min(pointer, last_address) / last_address
                progress_callback(percent, f"T8 Legion read 0x{min(pointer, last_address):06X}/0x{last_address:06X}")
        return bytes(buf[:last_address])

    def get_md5(self, md5type: LegionCommand, partition: int) -> bytes:
        if md5type not in (LegionCommand.GET_T8_MD5, LegionCommand.GET_T8_MCP_MD5):
            raise ValueError("invalid Legion MD5 command")
        return self.idemand(md5type, partition)

    def get_crc32(self, target: int = 0) -> int:
        return int.from_bytes(self.idemand(LegionCommand.GET_CRC32, target), "big")

    def get_mcp_version(self) -> str:
        data, _ = self.read_data_by_local_identifier(ECU_TARGET_MCP, 0x8100, 0x80)
        return data[0x0C:0x16].decode("ascii", errors="replace").strip("\x00 ")

    def start_secondary_bootloader(self) -> None:
        self.idemand(LegionCommand.START_SECONDARY_BOOTLOADER, 0)

    def marry_mcp(self) -> str:
        self.idemand(LegionCommand.MARRY_SECONDARY_PROCESSOR, 0)
        return self.get_mcp_version()

    # ---- partition comparison / programming (DESTRUCTIVE) -----------------

    def _local_partition_md5(self, file_bytes: bytes, device: int, partition: int) -> bytes:
        if device == ECU_TARGET_MCP:
            return bytes.fromhex(mcp_partition_md5(file_bytes, partition))
        if device == ECU_TARGET_T8:
            return bytes.fromhex(t8_main_partition_md5(file_bytes, partition))
        raise ValueError("device must be ECU_TARGET_MCP or ECU_TARGET_T8")

    def verify_flash(self, file_bytes: bytes, device: int, format_mask: int) -> bool:
        md5type = LegionCommand.GET_T8_MCP_MD5 if device == ECU_TARGET_MCP else LegionCommand.GET_T8_MD5
        for partition in range(1, 10):
            if not (format_mask & (1 << (partition - 1))):
                continue
            local = self._local_partition_md5(file_bytes, device, partition)
            remote = self.get_md5(md5type, partition)
            if local != remote:
                return False
        return True

    def determine_partition_mask(
        self, file_bytes: bytes, device: int, *, boot: bool = False, nvdm: bool = False, z22se: bool = False
    ) -> int:
        """Compare every partition's MD5 against the connected ECU and
        return a bitmask of the partitions that differ (bit N = partition
        N+1), narrowed by which protected regions the caller opted into.
        """
        md5type = LegionCommand.GET_T8_MCP_MD5 if device == ECU_TARGET_MCP else LegionCommand.GET_T8_MD5
        start = 1 if (z22se or boot) else 2
        mask = 0
        for partition in range(start, 10):
            local = self._local_partition_md5(file_bytes, device, partition)
            remote = self.get_md5(md5type, partition)
            if local != remote:
                mask |= 1 << (partition - 1)
        if not z22se:
            if not boot:
                mask &= 0x1FE
            if not nvdm:
                mask &= 0x1F9
        if device == ECU_TARGET_MCP:
            mask &= 0xFF
            mask |= (mask & 1) << 8
            if not z22se:
                mask &= 0x1BF
        return mask

    def erase_flash(self, device: int, format_mask: int, *, confirm_unvalidated: bool = False) -> None:
        """DESTRUCTIVE — erases flash partitions selected by ``format_mask``
        on the connected ECU. UNVALIDATED against real hardware; see module
        docstring before calling this against anything but a disposable
        bench ECU.

        Requires ``confirm_unvalidated=True`` so a caller can't reach real
        hardware through this path by accident — a wiring mistake here
        erases flash, not something recoverable by rerunning a test.
        """
        if not confirm_unvalidated:
            raise DiagnosticError(
                "T8 Legion erase_flash is unvalidated against real hardware; "
                "call with confirm_unvalidated=True once you've verified this "
                "against a bench ECU or a known-good CAN trace (see module docstring)."
            )
        if not self._legion_running:
            raise DiagnosticError("T8 Legion loader is not running")
        if format_mask == 0:
            return
        swapped_mask = ((format_mask & 0xFF) << 8) | ((format_mask >> 8) & 0xFF)
        command = ((swapped_mask << 40) | (((~swapped_mask) & 0xFFFF) << 24) | 0x13400) + device
        self._send_raw(command.to_bytes(8, "little"))

        first_pass = True
        retries = 0
        while True:
            data, _ = self.read_data_by_local_identifier(0xF0, 0, 4)
            if first_pass:
                if data[3] != device:
                    self._clock.sleep(5.0)
                    self._send_raw(command.to_bytes(8, "little"))
                else:
                    first_pass = False
            elif data[3] == 1:
                return
            retries += 1
            if retries > 40:
                raise TimeoutError("T8 Legion erase did not complete")
            self._clock.sleep(0.5)

    def write_flash(
        self,
        device: int,
        last_address: int,
        flash_data: bytes,
        format_mask: int,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        *,
        confirm_unvalidated: bool = False,
    ) -> None:
        """DESTRUCTIVE — programs flash on the connected ECU. UNVALIDATED
        against real hardware; see module docstring before calling this
        against anything but a disposable bench ECU.

        Requires ``confirm_unvalidated=True`` so a caller can't reach real
        hardware through this path by accident — a wiring mistake here
        corrupts flash, not something recoverable by rerunning a test.
        """
        if not confirm_unvalidated:
            raise DiagnosticError(
                "T8 Legion write_flash is unvalidated against real hardware; "
                "call with confirm_unvalidated=True once you've verified this "
                "against a bench ECU or a known-good CAN trace (see module docstring)."
            )
        if not self._legion_running:
            raise DiagnosticError("T8 Legion loader is not running")
        if format_mask == 0:
            return
        byteswapped = False
        if device == ECU_TARGET_MCP:
            byteswapped = mcp_is_byte_swapped(flash_data)

        last_block = (last_address // 0x80) - 1
        block_number = 0
        while block_number <= last_block:
            address = block_number * 0x80
            block = bytearray(get_current_block(flash_data, block_number, byteswapped))
            checksum = Trionic8Codec.legion_checksum16(bytes(block[:0x80]))
            block[0x80:0x82] = checksum

            problem = False
            if not ff_block(flash_data, address, 0x80) and erased_region(address, device, format_mask):
                problem = True
                for _attempt in range(20):
                    # Raw 8-byte ISO-TP-style First-Frame header announcing an
                    # 0x88-byte block write, sent directly (not through the
                    # normal ISO-TP transport) because the frames that follow
                    # are the loader's own raw multi-frame scheme, not
                    # standard ISO-TP consecutive frames.
                    header = bytes((0x10, 0x88, 0x36, 0x00)) + address.to_bytes(4, "big")
                    self._send_raw(header)
                    ack = self._recv_raw(timeout_ms=200)
                    if ack is None or ack[0] != 0x30 or ack[1] != 0x00:
                        continue
                    sequence = 0x21
                    cursor = 0
                    for _ in range(19):
                        frame_payload = bytes((sequence,)) + bytes(block[cursor:cursor + 7]).ljust(7, b"\x00")
                        self._send_raw(frame_payload)
                        sequence = 0x20 if sequence >= 0x2F else sequence + 1
                        cursor += 7
                    response = self._recv_raw(timeout_ms=150)
                    if response is not None and response[0] == 0x01 and response[1] == 0x76:
                        problem = False
                        break
                if problem:
                    raise DiagnosticError(f"T8 Legion write failed at 0x{address:06X} after 20 attempts")
            block_number += 1
            if progress_callback is not None:
                percent = 100.0 * block_number / (last_block + 1)
                progress_callback(percent, f"T8 Legion write block {block_number}/{last_block + 1}")


class _LegionRetryable(Exception):
    """Internal: signals idemand() to retry rather than fail outright."""
