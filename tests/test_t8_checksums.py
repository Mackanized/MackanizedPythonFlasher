"""Regression tests for Trionic 8 layer-1/layer-2 checksum inspection.

Synthetic images only — same rationale as tests/test_t7_checksums.py.
"""

from __future__ import annotations

import hashlib

from firmware.trionic.checksums import (
    T8_IMAGE_SIZE,
    _t8_encode_byte,
    inspect_t8_checksums,
    t8_last_used_address,
)

_OFFSET = 0x20200
_PARTIAL_ADDRESS = 0x1FFF0
_MATRIX_DIMENSION = 0x20000


def _encode_run(values: bytes) -> bytes:
    return bytes(_t8_encode_byte(value) for value in values)


def _build_t8_image() -> bytearray:
    image = bytearray(b"\xFF" * T8_IMAGE_SIZE)

    # A bit of deterministic "firmware" content between 0x20000 and the
    # checksum area, and in the small region the layer-2 byte sum covers.
    for i in range(0x20000, _OFFSET):
        image[i] = i & 0xFF
    for i in range(_PARTIAL_ADDRESS, _MATRIX_DIMENSION):
        image[i] = (i * 7) & 0xFF

    # Written after the content loop above so it isn't immediately
    # overwritten — 0x20140 falls inside the [0x20000, _OFFSET) range.
    image[0x20140:0x20144] = _OFFSET.to_bytes(4, "big")

    digest = hashlib.md5(image[0x20000:_OFFSET]).digest()
    calculated_layer1 = bytes(_t8_encode_byte(value) for value in digest)
    image[_OFFSET + 2:_OFFSET + 18] = calculated_layer1

    byte_sum = sum(image[_PARTIAL_ADDRESS:_MATRIX_DIMENSION - 4]) & 0xFFFFFFFF
    byte_sum = (byte_sum + image[_MATRIX_DIMENSION - 1]) & 0xFFFFFFFF
    stored_layer2 = byte_sum  # forces the byte-sum-with-terminal-byte path

    # Marker placed well past the layer-1 digest area (offset+2..offset+18)
    # within the 0x100-byte decoded region, matching real firmware layout
    # where the two don't overlap.
    marker = 0x20
    decoded = bytearray(marker + 0x11)
    decoded[marker] = 0xFB
    decoded[marker + 1:marker + 5] = stored_layer2.to_bytes(4, "big")
    decoded[marker + 6] = 0xFC
    decoded[marker + 7:marker + 11] = _MATRIX_DIMENSION.to_bytes(4, "big")
    decoded[marker + 0xC] = 0xFD
    decoded[marker + 13:marker + 17] = _PARTIAL_ADDRESS.to_bytes(4, "big")
    image[_OFFSET:_OFFSET + len(decoded)] = _encode_run(bytes(decoded))
    # Re-apply the layer-1 digest bytes in case the marker region above
    # overlapped them (it doesn't with marker=0x20, but keep this after so
    # layer-1 always wins if the two are ever moved closer together).
    image[_OFFSET + 2:_OFFSET + 18] = calculated_layer1
    return image


def test_t8_checksums_valid_synthetic_image() -> None:
    image = _build_t8_image()
    result = inspect_t8_checksums(bytes(image))
    assert result.valid, result.reason
    assert result.layer1_valid
    assert result.layer2_valid
    assert result.layer2_algorithm == "byte-sum-with-terminal-byte"
    assert result.checksum_area_offset == _OFFSET


def test_t8_checksums_detects_layer1_corruption() -> None:
    image = _build_t8_image()
    image[0x20050] ^= 0xFF  # inside the layer-1 md5'd region, outside layer-2's
    result = inspect_t8_checksums(bytes(image))
    assert not result.layer1_valid
    assert not result.valid


def test_t8_checksums_rejects_wrong_size() -> None:
    try:
        inspect_t8_checksums(bytes(100))
        assert False, "expected TrionicChecksumError"
    except Exception as exc:
        assert "1 MiB" in str(exc)


def test_t8_last_used_address_matches_pointer_plus_margin() -> None:
    image = _build_t8_image()
    assert t8_last_used_address(bytes(image)) == _OFFSET + 0x200
