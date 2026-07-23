"""Regression tests for Trionic 5 checksum/footer inspection.

Synthetic images only — same rationale as tests/test_t7_checksums.py.
"""

from __future__ import annotations

from firmware.trionic.checksums import extract_t5_footer_identifiers, inspect_t5_checksum

T5_IMAGE_SIZE = 0x20000


def _build_t5_checksum_image(file_end: int) -> bytearray:
    """A minimal image whose footer end-pointer chain resolves on the first
    container (no backward-chain walking needed) to ``file_end``.
    """
    image = bytearray(T5_IMAGE_SIZE)
    location = T5_IMAGE_SIZE - 5
    image[location - 1] = 0xFE  # end-pointer container marker, found immediately

    physical_end = file_end + (0x7FFFF - T5_IMAGE_SIZE)
    marker_text = f"{physical_end:06X}".encode("ascii")
    marker_length = len(marker_text)
    image[location] = marker_length
    # Stored reversed: image[location-marker_length-1:location-1][::-1] == marker_text
    image[location - marker_length - 1:location - 1] = marker_text[::-1]

    calculated = sum(image[:file_end]) & 0xFFFFFFFF
    image[-4:] = calculated.to_bytes(4, "big")
    return image


def test_t5_checksum_valid_synthetic_image() -> None:
    image = _build_t5_checksum_image(file_end=0x10000)
    result = inspect_t5_checksum(bytes(image))
    assert result.valid, result.reason
    assert result.last_used_file_address == 0x10000


def test_t5_checksum_detects_corruption() -> None:
    image = _build_t5_checksum_image(file_end=0x10000)
    image[0x100] ^= 0xFF
    result = inspect_t5_checksum(bytes(image))
    assert not result.valid
    assert result.reason == "stored checksum differs"


def test_t5_checksum_rejects_wrong_length() -> None:
    result = inspect_t5_checksum(bytes(123))
    assert not result.valid
    assert result.reason == "unsupported T5 image length"


def _text_field(tag: int, text: str) -> bytes:
    data = text.encode("ascii")
    return data + bytes((tag, len(data)))


def test_t5_footer_identifiers_synthetic() -> None:
    image = bytearray(T5_IMAGE_SIZE)
    footer = bytearray(0x80)
    fields = _text_field(0x01, "1234567") + _text_field(0x03, "ABCDEFGHIJKL")
    end = len(footer) - 4
    footer[end - len(fields):end] = fields
    image[-0x80:] = footer

    identifiers = extract_t5_footer_identifiers(bytes(image))
    assert identifiers == {
        "part_number": "1234567",
        "software_version": "ABCDEFGHIJKL",
    }


def test_t5_footer_identifiers_empty_for_short_image() -> None:
    assert extract_t5_footer_identifiers(bytes(10)) == {}
