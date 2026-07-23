"""Pure EDC16C39 firmware checksum strategy.

Checksum ranges are read from each image's own
info block. They operate on immutable byte strings.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


SEED = 0xFADECAFE
REFERENCE = 0xCAFEAFFE
SENTINEL = bytes.fromhex("FADECAFECAFEAFFE")
EXPECTED_IMAGE_SIZE = 0x200000
_U32_MASK = 0xFFFFFFFF


class EDC16C39ChecksumError(ValueError):
    """The input cannot be authoritatively interpreted as a C39 image."""


@dataclass(frozen=True)
class EDC16C39ChecksumBlock:
    sum_start: int
    sum_end: int
    store_offsets: Tuple[int, ...]
    main_region: bool
    predecessor_end: int
    cross_store_offset: int


@dataclass(frozen=True)
class EDC16C39ChecksumValidation:
    block: EDC16C39ChecksumBlock
    calculated: int
    stored_values: Tuple[int, ...]
    valid: bool


@dataclass(frozen=True)
class EDC16C39ChecksumInspection:
    valid: bool
    complete: bool
    blocks: Tuple[EDC16C39ChecksumBlock, ...]
    validations: Tuple[EDC16C39ChecksumValidation, ...]
    reason: str


def _u32_be(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise EDC16C39ChecksumError(f"32-bit field at 0x{offset:X} lies outside the image")
    return int.from_bytes(data[offset:offset + 4], "big")


def _be32_sum(data: bytes, start: int, end: int) -> int:
    if not 0 <= start < end <= len(data) or (end - start) % 4:
        raise EDC16C39ChecksumError(
            f"invalid checksum range 0x{start:X}-0x{end:X}"
        )
    total = 0
    for offset in range(start, end, 4):
        total = (total + int.from_bytes(data[offset:offset + 4], "big")) & _U32_MASK
    return total


def _checksum(data: bytes, block: EDC16C39ChecksumBlock) -> int:
    return (REFERENCE - ((SEED + _be32_sum(data, block.sum_start, block.sum_end)) & _U32_MASK)) & _U32_MASK


def _dependency_order(blocks: list[EDC16C39ChecksumBlock]) -> Tuple[EDC16C39ChecksumBlock, ...]:
    remaining = list(blocks)
    ordered: list[EDC16C39ChecksumBlock] = []
    while remaining:
        selected = next(
            (
                candidate
                for candidate in remaining
                if not any(
                    other is not candidate
                    and any(candidate.sum_start <= store < candidate.sum_end for store in other.store_offsets)
                    for other in remaining
                )
            ),
            None,
        )
        if selected is None:
            raise EDC16C39ChecksumError("checksum info blocks contain a cyclic storage dependency")
        remaining.remove(selected)
        ordered.append(selected)
    return tuple(ordered)


def discover_edc16c39_checksum_blocks(data: bytes) -> Tuple[EDC16C39ChecksumBlock, ...]:
    """Discover variant-specific checksum records in a two-megabyte image."""
    if len(data) != EXPECTED_IMAGE_SIZE:
        raise EDC16C39ChecksumError(
            f"EDC16C39 full image must be {EXPECTED_IMAGE_SIZE} bytes, got {len(data)}"
        )

    blocks: list[EDC16C39ChecksumBlock] = []
    for base in range(0, len(data), 0x10000):
        header_length = _u32_be(data, base)
        if not 0x40 <= header_length <= 0x200 or base + header_length > len(data):
            continue
        for offset in range(base, base + header_length - 15, 4):
            if data[offset:offset + 8] != SENTINEL or offset < 8:
                continue
            start = _u32_be(data, offset - 8)
            end = _u32_be(data, offset - 4)
            predecessor_end = _u32_be(data, offset + 8)
            cross_store = _u32_be(data, offset + 12)
            main = start & 0xFFFF == 0 and end >= start and end - start > 0x8000
            if main:
                sum_start = start + header_length
                sum_end = (end & ~0xFF) + 0x78
            else:
                sum_start = start
                sum_end = end & ~0x03
            if not (0 <= sum_start < sum_end <= len(data)) or sum_end + 4 > len(data):
                continue
            blocks.append(
                EDC16C39ChecksumBlock(
                    sum_start=sum_start,
                    sum_end=sum_end,
                    store_offsets=(sum_end,),
                    main_region=main,
                    predecessor_end=predecessor_end,
                    cross_store_offset=cross_store,
                )
            )

    if not blocks:
        raise EDC16C39ChecksumError("no valid EDC16C39 checksum info blocks were found")

    end_to_index = {
        block.sum_end: index for index, block in enumerate(blocks) if block.main_region
    }
    for block in tuple(blocks):
        if not block.main_region or not 0 < block.cross_store_offset <= len(data) - 4:
            continue
        predecessor_index = end_to_index.get(block.predecessor_end)
        if predecessor_index is None:
            continue
        predecessor = blocks[predecessor_index]
        if block.cross_store_offset not in predecessor.store_offsets:
            blocks[predecessor_index] = EDC16C39ChecksumBlock(
                sum_start=predecessor.sum_start,
                sum_end=predecessor.sum_end,
                store_offsets=predecessor.store_offsets + (block.cross_store_offset,),
                main_region=predecessor.main_region,
                predecessor_end=predecessor.predecessor_end,
                cross_store_offset=predecessor.cross_store_offset,
            )
    return _dependency_order(blocks)


def inspect_edc16c39_checksums(data: bytes) -> EDC16C39ChecksumInspection:
    blocks = discover_edc16c39_checksum_blocks(data)
    validations = []
    for block in blocks:
        calculated = _checksum(data, block)
        stored = tuple(_u32_be(data, offset) for offset in block.store_offsets)
        validations.append(
            EDC16C39ChecksumValidation(
                block=block,
                calculated=calculated,
                stored_values=stored,
                valid=bool(stored) and all(value == calculated for value in stored),
            )
        )
    valid = bool(validations) and all(item.valid for item in validations)
    return EDC16C39ChecksumInspection(
        valid=valid,
        complete=True,
        blocks=blocks,
        validations=tuple(validations),
        reason="all SUMMBIGEND checksums match" if valid else "one or more SUMMBIGEND checksums differ",
    )


def correct_edc16c39_checksums(data: bytes) -> bytes:
    """Return a corrected copy and verify that the resulting image is valid."""
    corrected = bytearray(data)
    blocks = discover_edc16c39_checksum_blocks(data)
    for block in blocks:
        value = _checksum(corrected, block)
        encoded = value.to_bytes(4, "big")
        for offset in block.store_offsets:
            corrected[offset:offset + 4] = encoded
    result = bytes(corrected)
    inspection = inspect_edc16c39_checksums(result)
    if not inspection.valid:
        raise EDC16C39ChecksumError("checksum correction did not produce a stable valid image")
    return result
