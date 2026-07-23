"""Regression tests for firmware/trionic/t8_partitions.py.

Synthetic images only — same rationale as tests/test_t7_checksums.py.
"""

from __future__ import annotations

import hashlib

import pytest

from firmware.trionic.checksums import T8_IMAGE_SIZE
from firmware.trionic.t8_partitions import (
    MCP_IMAGE_SIZE,
    MCP_PARTITION_COUNT,
    erased_region,
    ff_block,
    get_current_block,
    mcp_all_partition_md5,
    mcp_is_byte_swapped,
    mcp_partition_md5,
    mcp_partition_range,
    t8_main_partition_md5,
    t8_main_partition_range,
)


def test_mcp_byte_swap_detection() -> None:
    swapped = bytes((0x08, 0x00, 0x00, 0x20)) + bytes(MCP_IMAGE_SIZE - 4)
    not_swapped = bytes(MCP_IMAGE_SIZE)
    assert mcp_is_byte_swapped(swapped)
    assert not mcp_is_byte_swapped(not_swapped)


def test_mcp_partition_range_boundaries() -> None:
    assert mcp_partition_range(1) == (0x0000, 0x8000)
    assert mcp_partition_range(8) == (0x38000, 0x40000)
    assert mcp_partition_range(9) == (0x40000, MCP_IMAGE_SIZE)
    with pytest.raises(ValueError):
        mcp_partition_range(0)
    with pytest.raises(ValueError):
        mcp_partition_range(10)


def test_mcp_partition_md5_matches_hashlib_directly_when_not_swapped() -> None:
    image = bytes((i * 3) & 0xFF for i in range(MCP_IMAGE_SIZE))
    assert not mcp_is_byte_swapped(image)
    start, end = mcp_partition_range(3)
    expected = hashlib.md5(image[start:end]).hexdigest()
    assert mcp_partition_md5(image, 3) == expected


def test_mcp_partition_md5_normalizes_swapped_input() -> None:
    canonical = bytearray((i * 3) & 0xFF for i in range(MCP_IMAGE_SIZE))
    canonical[0:4] = bytes(4)  # keep the swap marker out of the data itself
    swapped = bytearray(len(canonical))
    for i in range(0, len(canonical) - 1, 2):
        swapped[i], swapped[i + 1] = canonical[i + 1], canonical[i]
    swapped[0:4] = bytes((0x08, 0x00, 0x00, 0x20))  # now looks swapped
    canonical[0:4] = bytes((0x08, 0x00, 0x00, 0x20))

    start, end = mcp_partition_range(2)
    expected = hashlib.md5(canonical[start:end]).hexdigest()
    assert mcp_partition_md5(bytes(swapped), 2) == expected


def test_mcp_all_partition_md5_covers_every_partition() -> None:
    image = bytes(MCP_IMAGE_SIZE)
    result = mcp_all_partition_md5(image)
    assert set(result.keys()) == set(range(1, MCP_PARTITION_COUNT + 1))


def test_t8_main_partition_range_and_md5() -> None:
    image = bytearray(T8_IMAGE_SIZE)
    image[0x20140:0x20144] = (0x30000).to_bytes(4, "big")  # last-used pointer
    image = bytes(image)

    assert t8_main_partition_range(image, 1) == (0x000000, 0x004000)
    assert t8_main_partition_range(image, 9) == (0x0C0000, 0x100000)
    assert t8_main_partition_range(image, 0) == (0, T8_IMAGE_SIZE)
    # Partition 10 is "start of image to last-used address" (pointer + 0x200 margin)
    assert t8_main_partition_range(image, 10) == (0x000000, 0x30200)

    start, end = t8_main_partition_range(image, 5)
    expected = hashlib.md5(image[start:end]).hexdigest()
    assert t8_main_partition_md5(image, 5) == expected


def test_erased_region_main_image_partition_boundaries() -> None:
    # 0x1000 falls in partition 1's range [0, 0x4000) -> bit 0 of the mask
    assert erased_region(0x1000, device=6, format_mask=0b1)
    assert not erased_region(0x1000, device=6, format_mask=0b10)
    # 0xC0000 falls in partition 9's range [0xC0000, 0x100000) -> bit 8
    assert erased_region(0xC0000, device=6, format_mask=1 << 8)
    assert not erased_region(0xC0000, device=6, format_mask=1 << 7)


def test_erased_region_mcp_partition_boundaries() -> None:
    # MCP partitions are address>>15 & 0xF; partition index 1 covers [0x8000, 0x10000)
    assert erased_region(0x8000, device=5, format_mask=0b10)
    assert not erased_region(0x8000, device=5, format_mask=0b1)


def test_ff_block() -> None:
    data = bytes((0xFF,) * 0x80) + bytes((0x00,) * 0x80)
    assert ff_block(data, 0, 0x80)
    assert not ff_block(data, 0x80, 0x80)
    assert not ff_block(data, 0x40, 0x80)  # straddles the boundary


def test_get_current_block_matches_stock_codec_encoding() -> None:
    from protocols.trionic.codecs import Trionic8Codec

    data = bytes(range(0x80))
    block = get_current_block(data, block_number=0, byteswapped=False)
    assert len(block) == 0x88
    assert block[:0x80] == Trionic8Codec.code_block(data)
    assert block[0x80:] == bytes(8)  # trailer left zero for the caller to fill in
