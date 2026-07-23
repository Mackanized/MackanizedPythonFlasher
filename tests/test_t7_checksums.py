"""Regression tests for Trionic 7 checksum inspection/correction.

Uses synthetic images built to exercise the exact structural cases that
matter, rather than real (copyrighted) ECU firmware: a checksum-storage
pointer expressed either as a plain file offset or as an SRAM-relative
address, and a checksum area whose address falls outside the scannable
file range and must be skipped rather than remapped.
"""

from __future__ import annotations

import pytest

from firmware.trionic.checksums import (
    T7_IMAGE_SIZE,
    T7_SCAN_END,
    inspect_t7_checksums,
    correct_t7_checksums,
    _t7_sum,
    _t7_f2,
)

_SIGNATURE = bytes.fromhex(
    "48E7003C247C00F0000026" "7C" "00000000" "287C00F00000" "2A7C"
)
assert len(_SIGNATURE) == 24

_DESCRIPTOR_START = 0x2000
_AREA_A_ADDR = 0x300
_AREA_A_LEN = 8
_AREA_B_ADDR = 0x000F0000  # deliberately unreachable within the scan window
_AREA_B_LEN = 8
_TARGET_FILE_OFFSET = 0x600
_FW_LENGTH = 0x10000


def _footer_field(identifier: int, value: int) -> bytes:
    """Forward TLV bytes such that ``footer.u32(identifier) == value``."""
    return value.to_bytes(4, "little") + bytes([identifier, 4])


def _byteswap32(value: int) -> int:
    return int.from_bytes(value.to_bytes(4, "big")[::-1], "big")


def _build_t7_image(sram_relative: bool) -> bytes:
    img = bytearray(T7_IMAGE_SIZE)
    img[_DESCRIPTOR_START:_DESCRIPTOR_START + 24] = _SIGNATURE
    cursor = _DESCRIPTOR_START + 24

    img[cursor:cursor + 4] = (0).to_bytes(4, "big")
    cursor += 4

    img[cursor:cursor + 2] = (0x4878).to_bytes(2, "big"); cursor += 2
    img[cursor:cursor + 2] = _AREA_A_LEN.to_bytes(2, "big"); cursor += 2
    img[cursor:cursor + 2] = (0x486D).to_bytes(2, "big"); cursor += 2
    img[cursor:cursor + 2] = _AREA_A_ADDR.to_bytes(2, "big"); cursor += 2

    img[cursor:cursor + 2] = (0x4878).to_bytes(2, "big"); cursor += 2
    img[cursor:cursor + 2] = _AREA_B_LEN.to_bytes(2, "big"); cursor += 2
    img[cursor:cursor + 2] = (0x4879).to_bytes(2, "big"); cursor += 2
    img[cursor:cursor + 4] = _AREA_B_ADDR.to_bytes(4, "big"); cursor += 4

    if sram_relative:
        checksum_address = 0x00090500
        sram_offset = checksum_address - _TARGET_FILE_OFFSET
    else:
        checksum_address = _TARGET_FILE_OFFSET
        sram_offset = 0
    img[cursor:cursor + 2] = (0xB0B9).to_bytes(2, "big"); cursor += 2
    img[cursor:cursor + 4] = checksum_address.to_bytes(4, "big"); cursor += 4

    for i in range(_AREA_A_LEN):
        img[_AREA_A_ADDR + i] = (0x10 + i) & 0xFF

    calculated_fw = _t7_sum(bytes(img), _AREA_A_ADDR, _AREA_A_LEN) & 0xFFFFFFFF
    img[_TARGET_FILE_OFFSET:_TARGET_FILE_OFFSET + 4] = calculated_fw.to_bytes(4, "big")

    footer = bytearray()
    footer += bytes([0xFF, 0x00])
    footer += _footer_field(0xFE, _FW_LENGTH)
    footer += _footer_field(0xFB, _t7_sum(bytes(img), 0, _FW_LENGTH))
    footer += _footer_field(0xF2, _t7_f2(bytes(img), _FW_LENGTH))
    if sram_relative:
        footer += _footer_field(0x9C, _byteswap32(sram_offset))
    img[len(img) - len(footer):] = footer
    return bytes(img)


@pytest.mark.parametrize("sram_relative", [True, False])
def test_t7_checksum_pipeline_valid(sram_relative: bool) -> None:
    image = _build_t7_image(sram_relative)
    result = inspect_t7_checksums(image)
    assert result.valid, result.reason
    assert result.misc_valid
    assert result.f2_valid
    assert result.fb_valid


@pytest.mark.parametrize("sram_relative", [True, False])
def test_t7_out_of_range_area_is_skipped_not_remapped(sram_relative: bool) -> None:
    """The bug: an SRAM-style area address used to get "corrected" onto the
    wrong file offset instead of being treated as unreachable and skipped.
    """
    image = _build_t7_image(sram_relative)
    result = inspect_t7_checksums(image)
    assert result.checksum_areas == ((_AREA_A_ADDR, _AREA_A_LEN),)


@pytest.mark.parametrize("sram_relative", [True, False])
def test_t7_checksum_round_trip_after_corruption(sram_relative: bool) -> None:
    data = bytearray(_build_t7_image(sram_relative))
    data[_AREA_A_ADDR] ^= 0xFF
    corrupted = bytes(data)
    assert not inspect_t7_checksums(corrupted).valid

    fixed = correct_t7_checksums(corrupted)
    assert inspect_t7_checksums(fixed).valid


def test_t7_sum_truncates_out_of_range_start_instead_of_raising() -> None:
    """Matches the reference: a start position at/past the scan boundary
    contributes zero rather than being treated as an error — some checksum
    area addresses legitimately point outside the scannable file range.
    """
    image = bytes(T7_IMAGE_SIZE)
    assert _t7_sum(image, T7_SCAN_END, 4) == 0
    assert _t7_sum(image, 0x90000, 100) == 0


def test_t7_sum_rejects_negative_range() -> None:
    image = bytes(T7_IMAGE_SIZE)
    with pytest.raises(Exception):
        _t7_sum(image, -1, 4)
