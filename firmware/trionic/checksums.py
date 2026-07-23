"""Pure Trionic 7 and Trionic 8 firmware checksum strategies.

The algorithms are clean Python ports of the pinned interoperability reference
listed in :mod:`domain.trionic`. They operate on immutable byte strings and
fail closed on malformed pointers, descriptors, or footer fields.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


T7_IMAGE_SIZE = 0x80000
T8_IMAGE_SIZE = 0x100000
T7_SCAN_END = 0x7FFFF
_U32_MASK = 0xFFFFFFFF


class TrionicChecksumError(ValueError):
    """Firmware structure does not permit authoritative checksum validation."""


@dataclass(frozen=True)
class T7ChecksumResult:
    valid: bool
    fw_valid: bool
    f2_valid: bool
    fb_valid: bool
    stored_fw: int
    calculated_fw: int
    stored_f2: int
    calculated_f2: int
    stored_fb: int
    calculated_fb: int
    firmware_length: int
    firmware_checksum_address: int
    checksum_areas: Tuple[Tuple[int, int], ...]
    reason: str


@dataclass(frozen=True)
class T8ChecksumResult:
    valid: bool
    layer1_valid: bool
    layer2_valid: bool
    checksum_area_offset: int
    stored_layer1: bytes
    calculated_layer1: bytes
    stored_layer2: int
    calculated_layer2: int
    layer2_storage_offset: int
    matrix_dimension: int
    partial_address: int
    layer2_algorithm: str
    reason: str


@dataclass(frozen=True)
class _T7FooterField:
    identifier: int
    data: bytes
    logical_positions: Tuple[int, ...]


@dataclass(frozen=True)
class _T7Footer:
    fields: Dict[int, _T7FooterField]
    terminated: bool

    def u32(self, identifier: int) -> int:
        field = self.fields.get(identifier)
        if field is None or len(field.data) != 4:
            raise TrionicChecksumError(f"T7 footer field 0x{identifier:02X} is missing or not four bytes")
        return int.from_bytes(field.data, "big")


def inspect_t7_checksums(image: bytes) -> T7ChecksumResult:
    """Validate the T7 FW-area, F2, and FB checksum set."""
    image = bytes(image)
    if len(image) != T7_IMAGE_SIZE:
        raise TrionicChecksumError("T7 image must be exactly 512 KiB")
    footer = _parse_t7_footer(image)
    if not footer.terminated:
        raise TrionicChecksumError("T7 footer terminator was not found")
    stored_f2 = footer.u32(0xF2) if 0xF2 in footer.fields else 0
    stored_fb = footer.u32(0xFB)
    firmware_length = footer.u32(0xFE)
    if not 0 < firmware_length <= T7_SCAN_END:
        raise TrionicChecksumError("T7 footer firmware length lies outside the image")
    raw_sram = footer.u32(0x9C) if 0x9C in footer.fields else 0
    sram_offset = int.from_bytes(raw_sram.to_bytes(4, "big"), "little")

    area_start = _find_t7_checksum_descriptor(image)
    areas, checksum_address = _parse_t7_fw_descriptor(image, area_start)
    checksum_file_address = _map_t7_address(checksum_address, sram_offset)
    if not 0 <= checksum_file_address <= len(image) - 4:
        raise TrionicChecksumError("T7 firmware checksum storage address lies outside the image")
    stored_fw = int.from_bytes(image[checksum_file_address:checksum_file_address + 4], "big")

    calculated_fw = 0
    mapped_areas = []
    for address, length in areas:
        mapped_address = _map_t7_address(address, sram_offset)
        if length:
            calculated_fw = (calculated_fw + _t7_sum(image, mapped_address, length)) & _U32_MASK
            mapped_areas.append((mapped_address, length))
    calculated_f2 = _t7_f2(image, firmware_length)
    calculated_fb = _t7_sum(image, 0, firmware_length)

    fw_valid = stored_fw == calculated_fw
    f2_valid = stored_f2 == 0 or stored_f2 == calculated_f2
    fb_valid = stored_fb == calculated_fb
    valid = fw_valid and f2_valid and fb_valid
    failures = []
    if not fw_valid:
        failures.append("FW")
    if not f2_valid:
        failures.append("F2")
    if not fb_valid:
        failures.append("FB")
    return T7ChecksumResult(
        valid=valid,
        fw_valid=fw_valid,
        f2_valid=f2_valid,
        fb_valid=fb_valid,
        stored_fw=stored_fw,
        calculated_fw=calculated_fw,
        stored_f2=stored_f2,
        calculated_f2=calculated_f2,
        stored_fb=stored_fb,
        calculated_fb=calculated_fb,
        firmware_length=firmware_length,
        firmware_checksum_address=checksum_file_address,
        checksum_areas=tuple(mapped_areas),
        reason="all T7 checksums match" if valid else f"T7 checksum mismatch: {', '.join(failures)}",
    )


def correct_t7_checksums(image: bytes) -> bytes:
    """Return a copy with the three discoverable T7 checksum values corrected."""
    original = bytes(image)
    result = inspect_t7_checksums(original)
    footer = _parse_t7_footer(original)
    output = bytearray(original)
    output[result.firmware_checksum_address:result.firmware_checksum_address + 4] = result.calculated_fw.to_bytes(4, "big")
    if result.stored_f2 != 0:
        _write_t7_footer_u32(output, footer, 0xF2, result.calculated_f2)
    _write_t7_footer_u32(output, footer, 0xFB, result.calculated_fb)
    return bytes(output)


def inspect_t8_checksums(image: bytes) -> T8ChecksumResult:
    """Validate both transformed-MD5 and encoded layer-2 T8 checksums."""
    image = bytes(image)
    if len(image) != T8_IMAGE_SIZE:
        raise TrionicChecksumError("T8 image must be exactly 1 MiB")
    offset = int.from_bytes(image[0x20140:0x20144], "big")
    if not 0x20000 < offset <= len(image) - 0x100:
        raise TrionicChecksumError("T8 checksum-area pointer lies outside the image")

    digest = hashlib.md5(image[0x20000:offset]).digest()
    calculated_layer1 = bytes(_t8_encode_byte(value) for value in digest)
    stored_layer1 = image[offset + 2:offset + 18]
    layer1_valid = stored_layer1 == calculated_layer1

    decoded = bytes(_t8_decode_byte(value) for value in image[offset:offset + 0x100])
    marker = _find_t8_layer2_marker(decoded)
    stored_layer2 = int.from_bytes(decoded[marker + 1:marker + 5], "big")
    matrix_dimension = int.from_bytes(decoded[marker + 7:marker + 11], "big")
    partial_address = int.from_bytes(decoded[marker + 13:marker + 17], "big")
    if matrix_dimension < 0x20000 or matrix_dimension > len(image):
        raise TrionicChecksumError("T8 layer-2 matrix dimension lies outside the image")
    if partial_address >= matrix_dimension - 4:
        raise TrionicChecksumError("T8 layer-2 partial address is not below the matrix boundary")

    byte_sum = sum(image[partial_address:matrix_dimension - 4]) & _U32_MASK
    byte_sum = (byte_sum + image[matrix_dimension - 1]) & _U32_MASK
    word_sum = 0
    for position in range(partial_address, matrix_dimension - 4, 4):
        word_sum = (word_sum + int.from_bytes(image[position:position + 4], "big")) & _U32_MASK
    if (byte_sum & 0xFFF00000) != (stored_layer2 & 0xFFF00000):
        calculated_layer2 = word_sum
        algorithm = "big-endian-u32-sum"
    else:
        calculated_layer2 = byte_sum
        algorithm = "byte-sum-with-terminal-byte"
    layer2_valid = stored_layer2 == calculated_layer2
    valid = layer1_valid and layer2_valid
    failures = []
    if not layer1_valid:
        failures.append("layer 1")
    if not layer2_valid:
        failures.append("layer 2")
    return T8ChecksumResult(
        valid=valid,
        layer1_valid=layer1_valid,
        layer2_valid=layer2_valid,
        checksum_area_offset=offset,
        stored_layer1=stored_layer1,
        calculated_layer1=calculated_layer1,
        stored_layer2=stored_layer2,
        calculated_layer2=calculated_layer2,
        layer2_storage_offset=offset + marker + 1,
        matrix_dimension=matrix_dimension,
        partial_address=partial_address,
        layer2_algorithm=algorithm,
        reason="both T8 checksum layers match" if valid else f"T8 checksum mismatch: {', '.join(failures)}",
    )


def correct_t8_checksums(image: bytes) -> bytes:
    """Return a copy with T8 layer 1 and encoded layer 2 corrected."""
    original = bytes(image)
    first = inspect_t8_checksums(original)
    output = bytearray(original)
    output[first.checksum_area_offset + 2:first.checksum_area_offset + 18] = first.calculated_layer1
    after_layer1 = inspect_t8_checksums(bytes(output))
    encoded_sum = bytes(_t8_encode_byte(value) for value in after_layer1.calculated_layer2.to_bytes(4, "big"))
    output[after_layer1.layer2_storage_offset:after_layer1.layer2_storage_offset + 4] = encoded_sum
    return bytes(output)


def _parse_t7_footer(image: bytes) -> _T7Footer:
    cursor = len(image)
    fields: Dict[int, _T7FooterField] = {}
    terminated = False
    for _ in range(128):
        if cursor < 2:
            break
        length = image[cursor - 1]
        identifier = image[cursor - 2]
        cursor -= 2
        if identifier in (0xFF, 0x00):
            terminated = identifier == 0xFF
            break
        if length > cursor:
            raise TrionicChecksumError(f"T7 footer field 0x{identifier:02X} overruns the image")
        positions = tuple(cursor - 1 - index for index in range(length))
        data = bytes(image[position] for position in positions)
        fields.setdefault(identifier, _T7FooterField(identifier, data, positions))
        cursor -= length
    return _T7Footer(fields, terminated)


def _write_t7_footer_u32(output: bytearray, footer: _T7Footer, identifier: int, value: int) -> None:
    field = footer.fields.get(identifier)
    if field is None or len(field.logical_positions) != 4:
        raise TrionicChecksumError(f"Cannot update missing T7 footer field 0x{identifier:02X}")
    for position, byte in zip(field.logical_positions, value.to_bytes(4, "big")):
        output[position] = byte


def _find_t7_checksum_descriptor(image: bytes) -> int:
    sequence = bytes.fromhex(
        "48 E7 00 3C 24 7C 00 F0 00 00 26 7C 00 00 00 00 28 7C 00 F0 00 00 2A 7C"
    )
    mask = bytes((1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 1, 1, 1, 0, 0, 1, 1))
    limit = min(len(image), T7_SCAN_END)
    for start in range(0, limit - len(sequence) + 1):
        if all(not mask[index] or image[start + index] == expected for index, expected in enumerate(sequence)):
            return start
    raise TrionicChecksumError("T7 firmware checksum descriptor signature was not found")


def _parse_t7_fw_descriptor(image: bytes, start: int) -> Tuple[Tuple[Tuple[int, int], ...], int]:
    areas = [[0, 0] for _ in range(16)]
    area_number = 0
    base_address = 0
    cursor = start + 22
    checksum_address: Optional[int] = None
    limit = min(len(image), T7_SCAN_END)
    while cursor + 2 <= limit:
        opcode = int.from_bytes(image[cursor:cursor + 2], "big")
        cursor += 2
        if opcode in (0x486D, 0x4878):
            if cursor + 2 > limit:
                break
            operand = int.from_bytes(image[cursor:cursor + 2], "big")
            cursor += 2
            if area_number >= len(areas):
                raise TrionicChecksumError("T7 checksum descriptor declares more than 16 areas")
            if opcode == 0x4878:
                areas[area_number][1] = operand
            else:
                areas[area_number][0] = base_address + operand
                area_number += 1
        elif opcode in (0x4879, 0x2A7C, 0xB0B9):
            if cursor + 4 > limit:
                break
            operand = int.from_bytes(image[cursor:cursor + 4], "big")
            cursor += 4
            if opcode == 0x2A7C:
                if operand < 0xF00000:
                    base_address = operand
            elif opcode == 0x4879:
                if area_number >= len(areas):
                    raise TrionicChecksumError("T7 checksum descriptor declares more than 16 areas")
                areas[area_number][0] = operand
                area_number += 1
            else:
                checksum_address = operand
                break
    if checksum_address is None:
        raise TrionicChecksumError("T7 firmware checksum storage instruction was not found")
    return tuple((address, length) for address, length in areas if length), checksum_address


def _map_t7_address(address: int, sram_offset: int) -> int:
    if address >= T7_IMAGE_SIZE and sram_offset:
        return address - sram_offset
    return address


def _t7_sum(image: bytes, start: int, length: int) -> int:
    if start < 0 or length < 0 or start + length > len(image):
        raise TrionicChecksumError(f"T7 checksum range 0x{start:X}+0x{length:X} lies outside the image")
    end = min(start + length, T7_SCAN_END)
    position = start
    checksum = 0
    dword_end = position + ((end - position) // 4) * 4
    while position < dword_end:
        checksum = (checksum + int.from_bytes(image[position:position + 4], "big")) & _U32_MASK
        position += 4
    tail = sum(image[position:end]) & 0xFF
    return (checksum + tail) & _U32_MASK


def _t7_f2(image: bytes, length: int) -> int:
    if length % 4:
        raise TrionicChecksumError("T7 F2 firmware length is not four-byte aligned")
    xor_table = (0x81184224, 0x24421881, 0xC33C6666, 0x3CC3C3C3, 0x11882244, 0x18241824, 0x84211248, 0x12345678)
    checksum = 0
    xor_count = 1
    for position in range(0, min(length, T7_SCAN_END), 4):
        word = int.from_bytes(image[position:position + 4], "big")
        checksum = (checksum + (word ^ xor_table[xor_count])) & _U32_MASK
        xor_count = 0 if xor_count == 7 else xor_count + 1
    checksum ^= 0x40314081
    return (checksum - 0x7FEFDFD0) & _U32_MASK


def _t8_encode_byte(value: int) -> int:
    return ((value ^ 0x21) - 0xD6) & 0xFF


def _t8_decode_byte(value: int) -> int:
    return ((value + 0xD6) & 0xFF) ^ 0x21


def _find_t8_layer2_marker(decoded: bytes) -> int:
    for index in range(0, len(decoded) - 0x10):
        if decoded[index] == 0xFB and decoded[index + 6] == 0xFC and decoded[index + 0x0C] == 0xFD:
            return index
    raise TrionicChecksumError("T8 encoded layer-2 metadata markers were not found")
