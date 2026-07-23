"""Pure diagnostic payload codec for the EDC16C39 profile.

The high-level services and parameters come from ``EDC16.cnf``.  These
builders stop short of claiming a complete physical transport: the archive
does not expose TransferData packing or recovery behavior.
"""

from __future__ import annotations

from domain.edc16c39 import Edc16Area


DIAGNOSTIC_MODE = 0x84
SECURITY_SEED_LEVEL = 0x05
ERASE_ROUTINE = 0x02
CHECKSUM_ROUTINE = 0x01
IDENTIFICATION_LOCAL_ID = 0x8A
ERASE_RESULT_CODE = 0xFB
CHECKSUM_RESULT_CODE = 0x23
ROUTINE_SUCCESS_FLAG = 0x00


def start_programming_session() -> bytes:
    return bytes((0x10, DIAGNOSTIC_MODE))


def request_seed() -> bytes:
    return bytes((0x27, SECURITY_SEED_LEVEL))


def send_key(key: bytes) -> bytes:
    if len(key) != 4:
        raise ValueError("EDC16C39 ETAS key must contain four bytes")
    return bytes((0x27, SECURITY_SEED_LEVEL + 1)) + key


def identify() -> bytes:
    return bytes((0x1A, IDENTIFICATION_LOCAL_ID))


def erase(area: Edc16Area) -> bytes:
    return bytes((0x31, ERASE_ROUTINE)) + area.start.to_bytes(4, "big") + area.size.to_bytes(4, "big")


def request_download(area: Edc16Area) -> bytes:
    return bytes((0x34, 0x00, 0x44)) + area.start.to_bytes(4, "big") + area.size.to_bytes(4, "big")


def read_memory(address: int, size: int) -> bytes:
    if address < 0 or size <= 0 or address + size > 0x1_0000_0000:
        raise ValueError("EDC16C39 ReadMemoryByAddress range is invalid")
    return bytes((0x23, 0x44)) + address.to_bytes(4, "big") + size.to_bytes(4, "big")


def transfer_data(block_counter: int, data: bytes) -> bytes:
    if not 0 <= block_counter <= 0xFF:
        raise ValueError("EDC16C39 TransferData block counter must fit in one byte")
    if not data:
        raise ValueError("EDC16C39 TransferData payload cannot be empty")
    return bytes((0x36, block_counter)) + bytes(data)


def request_transfer_exit() -> bytes:
    return b"\x37"


def verify_checksum() -> bytes:
    return bytes((0x31, CHECKSUM_ROUTINE))


def ecu_reset() -> bytes:
    return bytes((0x11, 0x01))


def tester_present() -> bytes:
    return bytes((0x3E, 0x00))


def parse_seed(response: bytes) -> bytes:
    expected_length = 2 + 6
    if len(response) != expected_length or response[:2] != bytes((0x67, SECURITY_SEED_LEVEL)):
        raise ValueError("malformed EDC16C39 ETAS seed response")
    return response[2:]


def parse_download_parameters(response: bytes) -> int:
    """Parse the standard length-format identifier in a 0x74 response."""
    if len(response) < 3 or response[0] != 0x74:
        raise ValueError("malformed EDC16C39 RequestDownload response")
    length_bytes = (response[1] >> 4) & 0x0F
    if length_bytes == 0 or response[1] & 0x0F or len(response) != 2 + length_bytes:
        raise ValueError("malformed EDC16C39 maximum-number-of-block-length field")
    maximum = int.from_bytes(response[2:], "big")
    if maximum <= 2:
        raise ValueError("EDC16C39 negotiated TransferData size is unusable")
    return maximum


def parse_routine_result(response: bytes, routine: int, result_code: int) -> None:
    expected = bytes((0x71, routine, result_code, ROUTINE_SUCCESS_FLAG))
    if response != expected:
        raise ValueError(
            f"malformed EDC16C39 routine result; expected {expected.hex().upper()}"
        )
