"""Compatibility wrappers for Trionic firmware inspection helpers."""

from dataclasses import dataclass
import hashlib
from typing import Optional

@dataclass(frozen=True)
class T5ChecksumInspection:
    valid: bool
    last_used_file_address: Optional[int]
    stored_checksum: Optional[int]
    calculated_checksum: Optional[int]
    reason: str


@dataclass(frozen=True)
class T8Layer1Inspection:
    valid: bool
    checksum_area_offset: Optional[int]
    stored_digest: bytes
    calculated_digest: bytes
    reason: str


def inspect_t5_checksum(image: bytes) -> T5ChecksumInspection:
    """Inspect a 128/256 KiB T5 image footer and additive checksum."""
    image = bytes(image)
    length = len(image)
    if length not in (0x20000, 0x40000):
        return T5ChecksumInspection(False, None, None, None, "unsupported T5 image length")

    location = length - 5
    lower_bound = length // 2
    while location > lower_bound and image[location - 1] != 0xFE:
        step = image[location] + 2
        if step <= 1 or location < step:
            return T5ChecksumInspection(False, None, None, None, "malformed footer container chain")
        location -= step
    if location <= lower_bound or image[location - 1] != 0xFE:
        return T5ChecksumInspection(False, None, None, None, "footer end-pointer container not found")

    marker_length = image[location]
    if not 1 <= marker_length <= 8 or location - marker_length - 1 < 0:
        return T5ChecksumInspection(False, None, None, None, "invalid footer end-pointer length")
    marker = bytes(image[location - marker_length - 1:location - 1][::-1])
    try:
        physical_end = int(marker.decode("ascii"), 16)
    except (UnicodeDecodeError, ValueError):
        return T5ChecksumInspection(False, None, None, None, "footer end pointer is not hexadecimal ASCII")

    file_end = physical_end - (0x7FFFF - length)
    if not 0 < file_end <= length - 7:
        return T5ChecksumInspection(False, None, None, None, "footer end pointer lies outside the image")
    stored = int.from_bytes(image[-4:], "big")
    calculated = sum(image[:file_end]) & 0xFFFFFFFF
    return T5ChecksumInspection(
        stored == calculated,
        file_end,
        stored,
        calculated,
        "checksum matches" if stored == calculated else "stored checksum differs",
    )


def correct_t5_checksum(image: bytes) -> bytes:
    """Return a copy of a 128/256 KiB T5 image with corrected additive footer checksum."""
    original = bytes(image)
    inspection = inspect_t5_checksum(original)
    if not inspection.last_used_file_address or inspection.calculated_checksum is None:
        raise ValueError(f"Unable to correct T5 checksum: {inspection.reason}")
    output = bytearray(original)
    output[-4:] = inspection.calculated_checksum.to_bytes(4, "big")
    return bytes(output)


def inspect_t8_layer1(image: bytes) -> T8Layer1Inspection:
    """Validate the transformed-MD5 layer while preserving the legacy API."""
    image = bytes(image)
    if len(image) != 0x100000:
        return T8Layer1Inspection(False, None, b"", b"", "T8 image must be exactly 1 MiB")
    offset = int.from_bytes(image[0x20140:0x20144], "big")
    if not 0x20000 < offset <= len(image) - 0x100:
        return T8Layer1Inspection(False, offset, b"", b"", "checksum-area pointer lies outside the image")
    # Layer 1 can still be inspected on research fixtures that do not carry
    # parseable layer-2 metadata, so retain this bounded calculation here.
    digest = hashlib.md5(image[0x20000:offset]).digest()
    calculated = bytes((((value ^ 0x21) - 0xD6) & 0xFF) for value in digest)
    stored = image[offset + 2:offset + 18]
    return T8Layer1Inspection(
        stored == calculated,
        offset,
        stored,
        calculated,
        "layer 1 matches" if stored == calculated else "layer 1 differs",
    )


def t8_last_used_address(image: bytes) -> int:
    """Return the bounded T8 header pointer plus its observed 0x200 margin."""
    if len(image) != 0x100000:
        raise ValueError("T8 image must be exactly 1 MiB")
    pointer = int.from_bytes(image[0x20140:0x20144], "big")
    last = pointer + 0x200
    if not 0x20000 < pointer < last <= len(image):
        raise ValueError("T8 last-used pointer lies outside the image")
    return last
