"""Fail-closed Bosch MED17/EDC17 checksum parsing and validation.

The block structure and CRC32/ADD32/ADD16 algorithms are derived from the
MIT-licensed ``ConnorHowell/medc17-checksum-tool`` at commit
``4ebf4c3216aebc6112de5d1aba3b7b0b62c20628``. This module intentionally does
not implement CVN manipulation or RSA signature forging.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional, Tuple


SOURCE_COMMIT = "4ebf4c3216aebc6112de5d1aba3b7b0b62c20628"
SOURCE_URL = f"https://github.com/ConnorHowell/medc17-checksum-tool/tree/{SOURCE_COMMIT}"
CRC32_POLYNOMIAL = 0xEDB88320
DEFAULT_START_VALUE = 0xFADECAFE
DEFAULT_ADD_TARGET = 0xCAFEAFFE
DEFAULT_CRC_TARGET = 0x35015001
_U32_MASK = 0xFFFFFFFF
_STRUCTURE_SIZE = 32


class MEDC17ChecksumError(ValueError):
    """The binary cannot be authoritatively interpreted as a MEDC17 image."""


class MEDC17Algorithm(IntEnum):
    CRC32 = 0x00
    ADD32 = 0x01
    ADD16 = 0x10


BLOCK_NAMES = {
    0x10: "Startup Block",
    0x20: "Tuning protection",
    0x30: "Customer Block",
    0x40: "Application software #0",
    0x50: "Application software #1",
    0x60: "Dataset #0",
    0x70: "Dataset #1",
    0x80: "Variant dataset",
    0x90: "Customer Tuning protection",
    0xA0: "Application software #2",
    0xB0: "Application software #3",
    0xC0: "Absolute constants #0",
    0xD0: "Emulation extension chip",
    0xE0: "Customer specific",
    0xF0: "Ramloader",
    0xF1: "Application Attestation",
}


@dataclass(frozen=True)
class MEDC17ChecksumDescriptor:
    offset: int
    block_id: int
    memory_start: int
    memory_end_inclusive: int
    initial_value: int
    expected_value: int
    block_id_reference: int
    block_id_address: int
    algorithm_id: int

    @property
    def algorithm(self) -> Optional[MEDC17Algorithm]:
        try:
            return MEDC17Algorithm(self.algorithm_id)
        except ValueError:
            return None


@dataclass(frozen=True)
class MEDC17Block:
    file_start: int
    file_end_inclusive: int
    memory_start: int
    memory_end_inclusive: int
    identifier: int
    name: str
    size: int
    software_identifier: bytes
    checksum_adjust: int
    stored_footer_checksum: int
    descriptors: Tuple[MEDC17ChecksumDescriptor, ...]

    @property
    def type_id(self) -> int:
        return self.identifier & 0xFF


@dataclass(frozen=True)
class MEDC17ChecksumValidation:
    block_name: str
    descriptor_offset: int
    algorithm_id: int
    algorithm_name: str
    file_start: Optional[int]
    file_end_inclusive: Optional[int]
    initial_value: int
    expected_value: Optional[int]
    calculated_value: Optional[int]
    valid: bool
    reason: str


@dataclass(frozen=True)
class MEDC17ChecksumInspection:
    valid: bool
    complete: bool
    variant: Optional[str]
    blocks: Tuple[MEDC17Block, ...]
    validations: Tuple[MEDC17ChecksumValidation, ...]
    reason: str


@dataclass(frozen=True)
class MEDC17CorrectionResult:
    image: bytes
    corrected_count: int
    inspection: MEDC17ChecksumInspection


def calculate_medc17_crc32(
    data: bytes,
    start: int,
    end_inclusive: int,
    initial_value: int,
) -> int:
    """TriCore little-endian, reflected CRC32 without a final XOR."""
    _validate_dword_range(data, start, end_inclusive)
    crc = initial_value & _U32_MASK
    for position in range(start, end_inclusive + 1, 4):
        dword = int.from_bytes(data[position:position + 4], "little")
        for _ in range(32):
            xor_result = dword ^ crc
            dword >>= 1
            crc = ((crc >> 1) ^ CRC32_POLYNOMIAL) if xor_result & 1 else crc >> 1
    return crc & _U32_MASK


def calculate_medc17_add32(
    data: bytes,
    start: int,
    end_inclusive: int,
    initial_value: int,
) -> int:
    """Add little-endian 32-bit words with unsigned 32-bit wraparound."""
    _validate_dword_range(data, start, end_inclusive)
    checksum = initial_value & _U32_MASK
    for position in range(start, end_inclusive + 1, 4):
        checksum = (checksum + int.from_bytes(data[position:position + 4], "little")) & _U32_MASK
    return checksum


def calculate_medc17_add16(
    data: bytes,
    start: int,
    end_inclusive: int,
    initial_value: int,
) -> int:
    """Bosch ADD16: sum words, treating the terminal word as the high half."""
    _validate_dword_range(data, start, end_inclusive)
    checksum = initial_value & _U32_MASK
    terminal_word = end_inclusive - 1
    for position in range(start, terminal_word, 2):
        checksum = (checksum + int.from_bytes(data[position:position + 2], "little")) & _U32_MASK
    last = int.from_bytes(data[terminal_word:terminal_word + 2], "little")
    return (checksum + (last << 16)) & _U32_MASK


def inspect_medc17_checksums(image: bytes) -> MEDC17ChecksumInspection:
    """Discover Bosch blocks and validate every supported checksum descriptor."""
    image = bytes(image)
    if not image or all(value == 0 for value in image):
        raise MEDC17ChecksumError("MEDC17 image is empty or entirely zero-filled")
    blocks = _find_blocks(image)
    if not blocks:
        raise MEDC17ChecksumError("No structurally valid Bosch MEDC17 blocks were found")
    if not any(block.descriptors for block in blocks):
        raise MEDC17ChecksumError("Bosch blocks contain no checksum descriptors")

    validations = tuple(
        _validate_descriptor(image, block, descriptor)
        for block in blocks
        for descriptor in block.descriptors
    )
    complete = all(item.calculated_value is not None for item in validations)
    valid = complete and bool(validations) and all(item.valid for item in validations)
    invalid = sum(not item.valid for item in validations)
    variant = _identify_variant(image, blocks)
    return MEDC17ChecksumInspection(
        valid=valid,
        complete=complete,
        variant=variant,
        blocks=blocks,
        validations=validations,
        reason=(
            f"all {len(validations)} MEDC17 checksum structures match"
            if valid
            else f"{invalid} of {len(validations)} MEDC17 checksum structures are invalid or unsupported"
        ),
    )


def correct_medc17_additive_checksums(image: bytes) -> MEDC17CorrectionResult:
    """Correct invalid ADD32/ADD16 adjustment dwords and revalidate.

    CRC32 structures are inspection-only because the referenced corrector also
    forges an RSA signature. Signature forging and CVN manipulation are outside
    PythonFlasher's safety boundary.
    """
    working = bytearray(image)
    initial = inspect_medc17_checksums(bytes(working))
    corrected = 0
    for validation in initial.validations:
        if validation.valid or validation.algorithm_id not in (
            MEDC17Algorithm.ADD32,
            MEDC17Algorithm.ADD16,
        ):
            continue
        if (
            validation.file_start is None
            or validation.file_end_inclusive is None
            or validation.calculated_value is None
            or validation.expected_value is None
        ):
            continue
        current_data = bytes(working)
        if validation.algorithm_id == MEDC17Algorithm.ADD32:
            current_value = calculate_medc17_add32(
                current_data,
                validation.file_start,
                validation.file_end_inclusive,
                validation.initial_value,
            )
        else:
            current_value = calculate_medc17_add16(
                current_data,
                validation.file_start,
                validation.file_end_inclusive,
                validation.initial_value,
            )
        patch_offset = validation.file_end_inclusive - 3
        old_value = int.from_bytes(working[patch_offset:patch_offset + 4], "little")
        difference = (validation.expected_value - current_value) & _U32_MASK
        new_value = (old_value + difference) & _U32_MASK
        working[patch_offset:patch_offset + 4] = new_value.to_bytes(4, "little")
        corrected += 1
    inspection = inspect_medc17_checksums(bytes(working))
    return MEDC17CorrectionResult(bytes(working), corrected, inspection)


def _find_blocks(image: bytes) -> Tuple[MEDC17Block, ...]:
    blocks = []
    cursor = 0
    while cursor < len(image):
        while cursor < len(image) and image[cursor] == 0:
            cursor += 1
        if cursor >= len(image):
            break
        block = _try_parse_block(image, cursor)
        if block is None:
            cursor += 1
            continue
        blocks.append(block)
        cursor = block.file_end_inclusive + 1
    return tuple(blocks)


def _try_parse_block(image: bytes, offset: int) -> Optional[MEDC17Block]:
    if offset < 0 or offset + 0x40 > len(image):
        return None
    identifier = _u32_le(image, offset)
    type_id = identifier & 0xFF
    if type_id not in BLOCK_NAMES:
        return None
    size = _u32_le(image, offset + 4)
    if size < 0x40 or offset + size > len(image):
        return None
    if _u32_le(image, offset + size - 4) != 0xDEADBEEF:
        return None
    memory_end_dword = _u32_le(image, offset + 0x0C)
    memory_start = memory_end_dword + 4 - size
    memory_end = memory_end_dword + 3
    if not (_is_flash_address(memory_start) and _is_flash_address(memory_end)):
        return None
    count = _u32_le(image, offset + 0x2C)
    if count > 100:
        return None
    table_start = offset + 0x34
    table_end = table_start + count * _STRUCTURE_SIZE
    if table_end + 4 > offset + size - 4:
        return None
    descriptors = []
    for index in range(count):
        structure = table_start + index * _STRUCTURE_SIZE
        descriptors.append(MEDC17ChecksumDescriptor(
            offset=structure,
            block_id=image[structure],
            memory_start=_u32_le(image, structure + 4),
            memory_end_inclusive=_u32_le(image, structure + 8),
            initial_value=_u32_le(image, structure + 12),
            expected_value=_u32_le(image, structure + 16),
            block_id_reference=_u32_le(image, structure + 20),
            block_id_address=_u32_le(image, structure + 24),
            algorithm_id=_u16_le(image, structure + 28) & 0xFF,
        ))
    return MEDC17Block(
        file_start=offset,
        file_end_inclusive=offset + size - 1,
        memory_start=memory_start,
        memory_end_inclusive=memory_end,
        identifier=identifier,
        name=BLOCK_NAMES[type_id],
        size=size,
        software_identifier=image[offset + 0x1A:offset + 0x24],
        checksum_adjust=_u32_le(image, offset + 0x30),
        stored_footer_checksum=_u32_le(image, table_end),
        descriptors=tuple(descriptors),
    )


def _validate_descriptor(
    image: bytes,
    block: MEDC17Block,
    descriptor: MEDC17ChecksumDescriptor,
) -> MEDC17ChecksumValidation:
    algorithm = descriptor.algorithm
    algorithm_name = algorithm.name if algorithm is not None else f"UNKNOWN_0x{descriptor.algorithm_id:02X}"
    start = descriptor.memory_start - block.memory_start + block.file_start
    end = descriptor.memory_end_inclusive - block.memory_start + block.file_start
    if (
        start < block.file_start
        or end > block.file_end_inclusive
        or start >= end
        or (end - start + 1) % 4
    ):
        return MEDC17ChecksumValidation(
            block.name, descriptor.offset, descriptor.algorithm_id, algorithm_name,
            None, None, descriptor.initial_value, None, None, False,
            "checksum memory range is outside its block or not dword-aligned",
        )
    if algorithm is None:
        return MEDC17ChecksumValidation(
            block.name, descriptor.offset, descriptor.algorithm_id, algorithm_name,
            start, end, descriptor.initial_value, None, None, False,
            "unsupported MEDC17 checksum algorithm",
        )
    if algorithm is MEDC17Algorithm.CRC32:
        if descriptor.expected_value != DEFAULT_ADD_TARGET:
            return MEDC17ChecksumValidation(
                block.name, descriptor.offset, descriptor.algorithm_id, algorithm_name,
                start, end, descriptor.initial_value, None, None, False,
                "CRC32 descriptor target is not the reference 0xCAFEAFFE complement",
            )
        expected = DEFAULT_CRC_TARGET
        calculated = calculate_medc17_crc32(image, start, end, descriptor.initial_value)
    elif algorithm is MEDC17Algorithm.ADD32:
        expected = descriptor.expected_value
        calculated = calculate_medc17_add32(image, start, end, descriptor.initial_value)
    else:
        expected = descriptor.expected_value
        calculated = calculate_medc17_add16(image, start, end, descriptor.initial_value)
    valid = calculated == expected
    return MEDC17ChecksumValidation(
        block.name, descriptor.offset, descriptor.algorithm_id, algorithm_name,
        start, end, descriptor.initial_value, expected, calculated, valid,
        "checksum matches" if valid else "calculated checksum differs",
    )


def _identify_variant(image: bytes, blocks: Tuple[MEDC17Block, ...]) -> Optional[str]:
    dataset = next((block for block in blocks if block.identifier == 0x60), None)
    if dataset is None:
        return None
    start = dataset.file_start + 0x78
    end = min(start + 100, dataset.file_end_inclusive + 1)
    if start >= end:
        return None
    value = image[start:end].split(b"\x00", 1)[0].decode("ascii", errors="ignore")
    return next(
        (field.strip() for field in value.split("/") if any(tag in field.upper() for tag in ("MED17", "EDC17", "MEDC17"))),
        None,
    )


def _validate_dword_range(data: bytes, start: int, end_inclusive: int) -> None:
    if start < 0 or start > end_inclusive or end_inclusive >= len(data):
        raise MEDC17ChecksumError("Checksum range lies outside the image")
    if (end_inclusive - start + 1) % 4:
        raise MEDC17ChecksumError("Checksum range must contain complete dwords")


def _is_flash_address(value: int) -> bool:
    return 0x80000000 <= value <= 0x8FFFFFFF


def _u16_le(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 2], "little")


def _u32_le(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset:offset + 4], "little")
