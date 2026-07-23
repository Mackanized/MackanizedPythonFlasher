"""Strict command codecs derived from observed Trionic interoperability flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple


@dataclass(frozen=True)
class EncodedCanFrame:
    can_id: int
    data: bytes

    def __post_init__(self) -> None:
        if not 0 <= self.can_id <= 0x7FF:
            raise ValueError("Only 11-bit Trionic CAN identifiers are supported")
        if not 1 <= len(self.data) <= 8:
            raise ValueError("Classic CAN payload must contain 1..8 bytes")


class T5CommandCodec:
    """Encode the native T5 SRAM-loader command frames.

    The byte layout is represented in on-wire order.  Loader acknowledgement
    frames echo the command/offset in byte 0 and report status in byte 1.
    """

    REQUEST_ID = 0x005
    RESPONSE_ID = 0x00C
    STATUS_OK = 0x00

    @classmethod
    def begin_upload(cls) -> EncodedCanFrame:
        return cls.address(0, 0)

    @classmethod
    def address(cls, address: int, length: int) -> EncodedCanFrame:
        if not 0 <= address <= 0xFFFFFF:
            raise ValueError("T5 loader address must fit in 24 bits")
        if not 0 <= length <= 0xFF:
            raise ValueError("T5 loader length must fit in one byte")
        data = bytes((
            0xA5,
            0x00,
            (address >> 16) & 0xFF,
            (address >> 8) & 0xFF,
            address & 0xFF,
            length,
            0x00,
            0x00,
        ))
        return EncodedCanFrame(cls.REQUEST_ID, data)

    @classmethod
    def data(cls, offset: int, chunk: bytes) -> EncodedCanFrame:
        if not 0 <= offset <= 0xFF:
            raise ValueError("T5 loader block offset must fit in one byte")
        if not 1 <= len(chunk) <= 7:
            raise ValueError("T5 loader data frame carries 1..7 bytes")
        return EncodedCanFrame(cls.REQUEST_ID, bytes((offset,)) + bytes(chunk).ljust(7, b"\x00"))

    @classmethod
    def start(cls, address: int) -> EncodedCanFrame:
        if not 0 <= address <= 0xFFFFFF:
            raise ValueError("T5 start vector must fit in 24 bits")
        data = bytes((
            0xC1,
            0x00,
            (address >> 16) & 0xFF,
            (address >> 8) & 0xFF,
            address & 0xFF,
            0x00,
            0x00,
            0x00,
        ))
        return EncodedCanFrame(cls.REQUEST_ID, data)

    @classmethod
    def read(cls, address: int) -> EncodedCanFrame:
        if not 0 <= address <= 0xFFFFFFFF:
            raise ValueError("T5 read address must fit in 32 bits")
        return EncodedCanFrame(cls.REQUEST_ID, b"\xC7" + address.to_bytes(4, "big") + b"\x00\x00\x00")

    @classmethod
    def chip_types(cls) -> EncodedCanFrame:
        return EncodedCanFrame(cls.REQUEST_ID, b"\xC9".ljust(8, b"\x00"))

    @staticmethod
    def decode_six_byte_response(response: bytes) -> bytes:
        if len(response) != 8:
            raise ValueError("T5 six-byte response requires one classic-CAN frame")
        return bytes(reversed(response[2:8]))

    @classmethod
    def erase(cls) -> EncodedCanFrame:
        return EncodedCanFrame(cls.REQUEST_ID, b"\xC0".ljust(8, b"\x00"))

    @classmethod
    def checksum(cls) -> EncodedCanFrame:
        return EncodedCanFrame(cls.REQUEST_ID, b"\xC8".ljust(8, b"\x00"))

    @classmethod
    def reset(cls) -> EncodedCanFrame:
        return EncodedCanFrame(cls.REQUEST_ID, b"\xC2".ljust(8, b"\x00"))

    @staticmethod
    def acknowledgement_ok(response: bytes, expected_echo: int) -> bool:
        return (
            len(response) == 8
            and response[0] == expected_echo
            and response[1] == T5CommandCodec.STATUS_OK
        )


class KwpCanCodec:
    """Encode/decode Saab T7 KWP2000 row framing over classic CAN."""

    SESSION_REQUEST_ID = 0x220
    SESSION_RESPONSE_ID = 0x238
    REQUEST_ID = 0x240
    RESPONSE_ID = 0x258
    ACK_ID = 0x266

    @staticmethod
    def session_start() -> EncodedCanFrame:
        return EncodedCanFrame(
            KwpCanCodec.SESSION_REQUEST_ID,
            bytes((0x3F, 0x81, 0x00, 0x11, 0x02, 0x40, 0x00)),
        )

    @staticmethod
    def request(service: int, parameters: bytes = b"") -> bytes:
        if not 0 <= service <= 0xFF:
            raise ValueError("KWP service must fit in one byte")
        body = bytes((service,)) + bytes(parameters)
        if len(body) > 0xFF:
            raise ValueError("KWP request exceeds its one-byte length field")
        return bytes((len(body),)) + body

    @staticmethod
    def encode_request_rows(request: bytes) -> Tuple[EncodedCanFrame, ...]:
        request = bytes(request)
        if len(request) < 2 or request[0] != len(request) - 1:
            raise ValueError("Malformed KWP request length")
        row_count = request[0] // 6 + 1
        frames = []
        for row in range(row_count - 1, -1, -1):
            first = row_count - row - 1 == 0
            header = (0x40 | row) if first else row
            offset = 0 if first else (row_count - row - 1) * 6
            chunk = request[offset:offset + 6]
            frames.append(EncodedCanFrame(
                KwpCanCodec.REQUEST_ID,
                bytes((header, 0xA1)) + chunk.ljust(6, b"\x00"),
            ))
        return tuple(frames)

    @staticmethod
    def acknowledgement(row: int) -> EncodedCanFrame:
        if not 0 <= row <= 0x3F:
            raise ValueError("KWP response row must fit in six bits")
        return EncodedCanFrame(
            KwpCanCodec.ACK_ID,
            bytes((0x40, 0xA1, 0x3F, 0x80 | row, 0x00)),
        )

    @staticmethod
    def decode_response_rows(frames: Iterable[bytes]) -> bytes:
        rows = tuple(bytes(frame) for frame in frames)
        if not rows or any(len(frame) != 8 for frame in rows):
            raise ValueError("KWP response requires one or more 8-byte CAN rows")
        expected = (rows[0][0] & 0x3F) + 1
        if len(rows) != expected or (rows[0][0] & 0xC0) != 0xC0:
            raise ValueError("KWP response row count/header mismatch")
        for index, frame in enumerate(rows[1:], start=1):
            remaining = expected - index - 1
            if (frame[0] & 0xC0) != 0x80 or (frame[0] & 0x3F) != remaining:
                raise ValueError("KWP response rows are missing or out of order")
        joined = b"".join(frame[2:] for frame in rows)
        total = joined[0] + 1
        if total > len(joined):
            raise ValueError("KWP response payload is truncated")
        return joined[:total]


class Trionic8Codec:
    """T8 loader payload primitives kept independent of ISO-TP transport."""

    _CODING_MASK = bytes((0x39, 0x68, 0x77, 0x6D, 0x47, 0x39))

    @classmethod
    def code_block(cls, data: bytes) -> bytes:
        return bytes(value ^ cls._CODING_MASK[index % len(cls._CODING_MASK)] for index, value in enumerate(data))

    @staticmethod
    def transfer_header(address: int) -> bytes:
        if not 0 <= address <= 0xFFFFFFFF:
            raise ValueError("T8 loader transfer address must fit in 32 bits")
        # The stock loader's ISO-TP first frame is, for example,
        # ``10 F0 36 00 00 10 24 00`` for SRAM address 0x00102400.
        # In other words the loader sub-protocol carries a four-byte address;
        # it is not the three-byte GMLAN ReadMemoryByAddress layout.
        return b"\x36\x00" + address.to_bytes(4, "big")

    @classmethod
    def stock_transfer_payload(cls, address: int, data: bytes) -> bytes:
        if not data:
            raise ValueError("T8 transfer block cannot be empty")
        return cls.transfer_header(address) + cls.code_block(bytes(data))

    @staticmethod
    def legion_checksum16(data: bytes) -> bytes:
        return (sum(data) & 0xFFFF).to_bytes(2, "big")
