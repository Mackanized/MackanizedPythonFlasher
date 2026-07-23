"""
ISO 15765-2 (ISO-TP) Transport Protocol Implementation.

Provides frame segmentation, reassembly, Flow Control management, sequence counter
validation, ISO-TP 2016 extended 32-bit length handling, and OS-native timer sleep
management to eliminate CPU starvation.
"""

import ctypes
import struct
import os
from typing import Optional, Tuple
from adapters.base_adapter import BaseAdapter
from domain.cancellation import CancellationToken
from domain.clock import Clock, SystemClock
from domain.errors import (
    IsoTpFlowControlError,
    IsoTpSequenceError as _DomainIsoTpSequenceError,
    TransportError,
    OperationCancelled,
)
from logger import can_logger, app_logger

FRAME_TYPE_SF = 0x0
FRAME_TYPE_FF = 0x1
FRAME_TYPE_CF = 0x2
FRAME_TYPE_FC = 0x3

DEFAULT_PADDING_BYTE = 0x00
MAX_ISOTP_PAYLOAD = 16 * 1024 * 1024
MAX_FC_WAIT_FRAMES = 3


class IsoTpSequenceError(_DomainIsoTpSequenceError):
    """Raised when an out-of-order or duplicate ISO-TP Consecutive Frame is received.

    Subclassed from :class:`domain.errors.IsoTpSequenceError` for backward
    compatibility with code that imports from this module directly.
    """


class ISOTPTransport:
    """Protocol-agnostic ISO-TP Transport Engine."""

    def __init__(
        self,
        adapter: BaseAdapter,
        tx_id: int,
        rx_id: int,
        stmin_s: float = 0.0,
        padding_byte: int = DEFAULT_PADDING_BYTE,
        cancellation_token: Optional[CancellationToken] = None,
        capture_sensitive_payloads: bool = False,
        clock: Optional[Clock] = None,
    ):
        self.adapter = adapter
        self.tx_id = tx_id
        self.rx_id = rx_id
        self.stmin_s = stmin_s
        self.padding_byte = padding_byte
        self._cancel = cancellation_token or CancellationToken()
        self._capture_sensitive_payloads = bool(capture_sensitive_payloads)
        self._clock = clock or SystemClock()

    def send_payload(self, payload: bytes) -> bool:
        length = len(payload)
        if length > MAX_ISOTP_PAYLOAD:
            raise TransportError(f"ISO-TP payload exceeds configured maximum: {length}")

        # Single Frame (SF)
        if length <= 7:
            frame_data = bytes([(FRAME_TYPE_SF << 4) | length]) + payload
            frame_data = frame_data.ljust(8, bytes([self.padding_byte]))
            self._trace("TX", self.tx_id, frame_data)
            return self.adapter.send_frame(self.tx_id, frame_data)

        # Multi-Frame First Frame (FF)
        if length <= 4095:
            ff_header = bytes([(FRAME_TYPE_FF << 4) | ((length >> 8) & 0x0F), length & 0xFF])
            ff_data = (ff_header + payload[:6]).ljust(8, bytes([self.padding_byte]))
            bytes_sent = 6
        else:
            # ISO 15765-2:2016 Extended 32-bit payload length format
            ff_header = bytes([(FRAME_TYPE_FF << 4) | 0x00, 0x00]) + struct.pack(">I", length)
            ff_data = (ff_header + payload[:2]).ljust(8, bytes([self.padding_byte]))
            bytes_sent = 2

        self._trace("TX", self.tx_id, ff_data)
        if not self.adapter.send_frame(self.tx_id, ff_data):
            return False

        try:
            block_size, stmin_s = self._wait_for_flow_control(timeout_s=2.0)
        except IsoTpFlowControlError as exc:
            app_logger.error(f"[ISO-TP] {exc}")
            return False

        # Consecutive Frames (CF) transmission
        seq_num = 1
        sent_in_block = 0

        winmm = None
        if hasattr(ctypes, 'windll'):
            try:
                winmm = ctypes.windll.winmm
                winmm.timeBeginPeriod(1)
            except (AttributeError, OSError):
                pass

        try:
            while bytes_sent < length:
                self._raise_if_cancelled()
                chunk = payload[bytes_sent:bytes_sent + 7]
                cf_header = bytes([(FRAME_TYPE_CF << 4) | (seq_num & 0x0F)])
                cf_data = (cf_header + chunk).ljust(8, bytes([self.padding_byte]))
                self._trace("TX", self.tx_id, cf_data)

                if not self.adapter.send_frame(self.tx_id, cf_data):
                    return False

                bytes_sent += len(chunk)
                seq_num = (seq_num + 1) & 0x0F
                sent_in_block += 1

                if stmin_s >= 0.002:
                    self._clock.sleep(stmin_s)
                elif stmin_s > 0.0:
                    self._clock.sleep(stmin_s)

                if block_size and sent_in_block >= block_size and bytes_sent < length:
                    try:
                        block_size, stmin_s = self._wait_for_flow_control(timeout_s=2.0)
                    except IsoTpFlowControlError as exc:
                        app_logger.error(f"[ISO-TP] {exc}")
                        return False
                    sent_in_block = 0
        finally:
            if winmm:
                try:
                    winmm.timeEndPeriod(1)
                except (AttributeError, OSError):
                    pass

        return True

    def receive_payload(self, timeout_s: float = 2.0) -> Optional[bytes]:
        deadline = self._clock.monotonic() + timeout_s
        rx_buffer = bytearray()
        expected_length = 0
        expected_seq = 1

        while self._clock.monotonic() < deadline:
            self._raise_if_cancelled()
            remaining_s = max(0.0, deadline - self._clock.monotonic())
            rx_id, rx_data = self.adapter.read_frame(timeout_ms=max(1, min(100, int(remaining_s * 1000))))
            if not rx_data:
                continue

            self._trace("RX", rx_id, rx_data)

            if rx_id != self.rx_id:
                continue

            frame_type = (rx_data[0] >> 4) & 0x0F

            if frame_type == FRAME_TYPE_SF:
                length = rx_data[0] & 0x0F
                if length > 7 or length > len(rx_data) - 1:
                    raise TransportError("Malformed ISO-TP Single Frame length")
                return bytes(rx_data[1:1 + length])

            elif frame_type == FRAME_TYPE_FF:
                if expected_length:
                    raise TransportError("Unexpected second ISO-TP First Frame")
                length_field = ((rx_data[0] & 0x0F) << 8) | rx_data[1]
                if length_field > 0:
                    expected_length = length_field
                    rx_buffer.extend(rx_data[2:8])
                else:
                    # ISO 15765-2:2016 32-bit Extended Length First Frame
                    if len(rx_data) >= 6:
                        expected_length = struct.unpack(">I", rx_data[2:6])[0]
                        rx_buffer.extend(rx_data[6:8])

                if expected_length <= len(rx_buffer) or expected_length > MAX_ISOTP_PAYLOAD:
                    raise TransportError(f"Invalid ISO-TP First Frame length: {expected_length}")

                expected_seq = 1

                # Send Flow Control (CTS)
                fc_frame = bytes([0x30, 0x00, 0x00]).ljust(8, bytes([self.padding_byte]))
                self._trace("TX", self.tx_id, fc_frame)
                if not self.adapter.send_frame(self.tx_id, fc_frame):
                    return None

            elif frame_type == FRAME_TYPE_CF:
                if not expected_length:
                    raise TransportError("ISO-TP Consecutive Frame received before First Frame")
                current_seq = rx_data[0] & 0x0F

                if current_seq != expected_seq:
                    app_logger.error(
                        f"[ISO-TP] Sequence counter mismatch on 0x{rx_id:03X}! "
                        f"Expected 0x{expected_seq:X}, got 0x{current_seq:X}."
                    )
                    raise IsoTpSequenceError(
                        f"Sequence number mismatch: expected {expected_seq}, got {current_seq}"
                    )

                remaining = expected_length - len(rx_buffer)
                chunk_len = min(7, remaining)
                rx_buffer.extend(rx_data[1:1 + chunk_len])

                if len(rx_buffer) >= expected_length:
                    return bytes(rx_buffer)

                expected_seq = (expected_seq + 1) & 0x0F

        if rx_buffer:
            app_logger.error(
                f"[ISO-TP] Incomplete response: received {len(rx_buffer)} of {expected_length} bytes."
            )
        return None

    def _wait_for_flow_control(self, timeout_s: float) -> Tuple[int, float]:
        deadline = self._clock.monotonic() + timeout_s
        wait_frames = 0
        while self._clock.monotonic() < deadline:
            self._raise_if_cancelled()
            remaining_s = max(0.0, deadline - self._clock.monotonic())
            rx_id, rx_data = self.adapter.read_frame(
                timeout_ms=max(1, min(100, int(remaining_s * 1000)))
            )
            if not rx_data or rx_id != self.rx_id:
                continue
            self._trace("RX", rx_id, rx_data)
            if len(rx_data) < 3 or ((rx_data[0] >> 4) & 0x0F) != FRAME_TYPE_FC:
                continue
            flow_status = rx_data[0] & 0x0F
            if flow_status == 0x01:
                wait_frames += 1
                if wait_frames > MAX_FC_WAIT_FRAMES:
                    raise IsoTpFlowControlError("Flow Control WAIT limit exceeded")
                continue
            if flow_status == 0x02:
                raise IsoTpFlowControlError("Receiver reported Flow Control OVERFLOW")
            if flow_status != 0x00:
                raise IsoTpFlowControlError(f"Invalid Flow Control status 0x{flow_status:X}")
            stmin_s = self._decode_stmin(rx_data[2])
            return rx_data[1], stmin_s
        raise IsoTpFlowControlError("Flow Control timeout")

    @staticmethod
    def _decode_stmin(value: int) -> float:
        if value == 0x00:
            return 0.0
        if 0x01 <= value <= 0x7F:
            return value / 1000.0
        if 0xF1 <= value <= 0xF9:
            return (value - 0xF0) / 10000.0
        raise IsoTpFlowControlError(f"Invalid STmin value 0x{value:02X}")

    def _raise_if_cancelled(self) -> None:
        if self._cancel.should_interrupt:
            raise OperationCancelled("ISO-TP transfer cancelled")

    def _trace(self, direction: str, can_id: int, data: bytes) -> None:
        """Redact diagnostic and firmware payloads unless explicitly enabled."""
        if not self.adapter.is_simulation:
            if self._capture_sensitive_payloads and os.environ.get("MACKANIZED_FLASHER_SENSITIVE_TRACE") == "1":
                can_logger.info(f"{direction} | 0x{can_id:03X} | {data.hex(' ').upper()}")
            else:
                frame_type = (data[0] >> 4) & 0x0F if data else -1
                can_logger.info(
                    f"{direction} | 0x{can_id:03X} | len={len(data)} "
                    f"isotp_type=0x{frame_type:X} payload=REDACTED"
                )
