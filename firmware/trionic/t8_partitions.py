"""Trionic 8 partitioning, byte-order, and block-encoding helpers.

Covers both T8 flashable targets:

* The main GMLAN/stock-bootloader image (device byte 6) — partition
  boundaries plus MD5 helpers, used by the alternate-bootloader ("Legion")
  live client for partition-comparison and by offline tooling.
* MCP, the secondary co-processor (device byte 5) — a distinct ~256 KiB
  region with its own partition layout and independent byte-order
  (verified against a real MCP dump), compared by per-partition MD5
  against a connected ECU rather than an embedded checksum.

Plus the block write-encoding (rotating XOR + checksum trailer) shared by
both targets' Legion write path.

These are pure, offline helpers with no CAN I/O.
"""

from __future__ import annotations

import hashlib
from typing import Dict, Tuple

from firmware.trionic.checksums import t8_last_used_address

# ---- main T8 image (device byte 6) ----------------------------------------

T8_MAIN_IMAGE_SIZE = 0x100000

# 1-indexed partition boundaries for the main T8 image. Partitions 10-12 are
# not physical partitions: they are "from this address to the last used
# address" ranges used to compare only the programmed portion of a region
# against a candidate file, rather than the whole (mostly 0xFF) remainder.
_T8_MAIN_BOUNDS: Tuple[int, ...] = (
    0x000000, 0x004000, 0x006000, 0x008000, 0x020000,
    0x040000, 0x060000, 0x080000, 0x0C0000, 0x100000,
)
_T8_MAIN_RANGE_START: Dict[int, int] = {10: 0x000000, 11: 0x004000, 12: 0x020000}


def t8_main_partition_range(image: bytes, partition: int) -> Tuple[int, int]:
    """Return the (start, end) byte range for a 0-12 main-image partition.

    Partition 0 is the whole image; 1-9 are the physical flash partitions;
    10-12 are "start address to last used address" ranges (see module
    docstring).
    """
    if partition == 0:
        return 0, _T8_MAIN_BOUNDS[9]
    if 1 <= partition <= 9:
        return _T8_MAIN_BOUNDS[partition - 1], _T8_MAIN_BOUNDS[partition]
    if partition in _T8_MAIN_RANGE_START:
        return _T8_MAIN_RANGE_START[partition], t8_last_used_address(image)
    raise ValueError("T8 main partition must be 0-12")


def t8_main_partition_md5(image: bytes, partition: int) -> str:
    """Hex MD5 of one main-image partition range."""
    if len(image) != T8_MAIN_IMAGE_SIZE:
        raise ValueError(f"T8 main image must be exactly {T8_MAIN_IMAGE_SIZE} bytes, got {len(image)}")
    start, end = t8_main_partition_range(image, partition)
    return hashlib.md5(image[start:end]).hexdigest()


# ---- MCP secondary co-processor (device byte 5) ----------------------------

MCP_IMAGE_SIZE = 0x40100
MCP_PARTITION_COUNT = 9
MCP_PARTITION_SIZE = 0x8000  # partitions 1-8; partition 9 is the 0x100-byte tail

_MCP_SWAPPED_MARKER = (0x08, 0x00, 0x00, 0x20)


def mcp_is_byte_swapped(image: bytes) -> bool:
    """True if the image's leading bytes match the known 16-bit-word-swapped marker.

    Real dumps have been observed in both this swapped order and normal
    order; per-partition MD5s must be computed against a consistent,
    canonical byte order regardless of which one a given source file is in.
    """
    return len(image) >= 4 and tuple(image[:4]) == _MCP_SWAPPED_MARKER


def _swap_words(data: bytes) -> bytes:
    """Swap each adjacent byte pair (16-bit word byte-swap)."""
    out = bytearray(len(data))
    for i in range(0, len(data), 2):
        out[i], out[i + 1] = data[i + 1], data[i]
    return bytes(out)


def mcp_partition_range(partition: int) -> Tuple[int, int]:
    """Return the (start, end) byte range for a 1-indexed MCP partition (1-9)."""
    if not 1 <= partition <= MCP_PARTITION_COUNT:
        raise ValueError(f"MCP partition must be 1-{MCP_PARTITION_COUNT}")
    if partition == MCP_PARTITION_COUNT:
        return 0x40000, MCP_IMAGE_SIZE
    end = partition << 15
    return end - MCP_PARTITION_SIZE, end


def mcp_partition_md5(image: bytes, partition: int) -> str:
    """Hex MD5 of one partition, normalized to canonical (non-swapped) byte order."""
    if len(image) != MCP_IMAGE_SIZE:
        raise ValueError(f"MCP image must be exactly {MCP_IMAGE_SIZE} bytes, got {len(image)}")
    start, end = mcp_partition_range(partition)
    chunk = image[start:end]
    if mcp_is_byte_swapped(image):
        chunk = _swap_words(chunk)
    return hashlib.md5(chunk).hexdigest()


def mcp_all_partition_md5(image: bytes) -> Dict[int, str]:
    """MD5 of every MCP partition, keyed by 1-indexed partition number."""
    return {partition: mcp_partition_md5(image, partition) for partition in range(1, MCP_PARTITION_COUNT + 1)}


# ---- shared: partition-mask test / Legion block write-encoding ------------

def erased_region(address: int, device: int, format_mask: int) -> bool:
    """True if ``address`` falls in a partition selected by ``format_mask``.

    ``device`` is 6 for the main T8 image, 5 for MCP. The mask's bit N
    corresponds to partition N+1 (bit 0 = partition 1).
    """
    if device == 6:
        part = 0
        for index in range(8, 0, -1):
            if address >= _T8_MAIN_BOUNDS[index]:
                part = index
                break
    elif device == 5:
        part = (address >> 15) & 0xF
    else:
        return False
    return bool((format_mask >> part) & 1)


def ff_block(data: bytes, address: int, size: int) -> bool:
    """True if the ``size`` bytes at ``address`` are all erased (0xFF)."""
    end = min(address + size, len(data))
    if end <= address:
        return False
    return all(value == 0xFF for value in data[address:end])


def get_current_block(data: bytes, block_number: int, byteswapped: bool) -> bytes:
    """Return one 0x88-byte encoded write block (0x80 data + 8 trailer bytes).

    Uses the same rotating-XOR block coding as the stock T8 write path
    (:meth:`protocols.trionic.codecs.Trionic8Codec.code_block`). The
    trailer's first two bytes are a checksum the caller fills in; the
    remaining six are left zero, matching the block layout the alternate
    bootloader expects.
    """
    from protocols.trionic.codecs import Trionic8Codec

    address = block_number * 0x80
    raw = data[address:address + 0x80]
    if byteswapped:
        swapped = bytearray(len(raw))
        for i in range(0, len(raw) - 1, 2):
            swapped[i], swapped[i + 1] = raw[i + 1], raw[i]
        raw = bytes(swapped)
    encoded = Trionic8Codec.code_block(raw)
    return encoded.ljust(0x88, b"\x00")
