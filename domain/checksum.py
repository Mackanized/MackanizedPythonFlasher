"""
Domain Layer - Checksum & Binary Verification Engine

Provides fingerprints and explicitly labelled, non-authoritative arithmetic sums.
"""

import zlib
import hashlib
from typing import Dict, Tuple


class ChecksumCalculator:
    """Calculates and verifies automotive ECU firmware checksums."""

    @staticmethod
    def calculate_crc32(data: bytes) -> int:
        """Calculate standard 32-bit CRC (zlib)."""
        return zlib.crc32(data) & 0xFFFFFFFF

    @staticmethod
    def calculate_md5(data: bytes) -> str:
        """Legacy compatibility fingerprint. Do not use as a trust decision."""
        return hashlib.md5(data).hexdigest()

    @staticmethod
    def calculate_sha256(data: bytes) -> str:
        """Calculate a collision-resistant artifact fingerprint."""
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def calculate_bosch16_sum(data: bytes, start_offset: int = 0, end_offset: int = 0) -> int:
        """
        Calculate 16-bit big-endian word summation (Bosch ME7/ME9 calibration sum).
        """
        if end_offset <= 0 or end_offset > len(data):
            end_offset = len(data)

        chk_sum = 0
        for i in range(start_offset, end_offset - 1, 2):
            word = (data[i] << 8) | data[i + 1]
            chk_sum = (chk_sum + word) & 0xFFFF
        return chk_sum

    @staticmethod
    def calculate_bosch32_sum(data: bytes, start_offset: int = 0, end_offset: int = 0) -> int:
        """
        Calculate 32-bit big-endian double-word summation (Bosch EDC16/EDC17 calibration sum).
        """
        if end_offset <= 0 or end_offset > len(data):
            end_offset = len(data)

        chk_sum = 0
        for i in range(start_offset, end_offset - 3, 4):
            dword = (data[i] << 24) | (data[i + 1] << 16) | (data[i + 2] << 8) | data[i + 3]
            chk_sum = (chk_sum + dword) & 0xFFFFFFFF
        return chk_sum

    @classmethod
    def inspect_binary(cls, data: bytes) -> Tuple[bool, Dict[str, str]]:
        """
        Verify binary integrity and compute checksum metadata.

        Returns (is_valid, metadata_dict).
        """
        if not data or len(data) == 0:
            return False, {"error": "Empty binary data"}

        # Empty image check (all 0xFF or 0x00)
        if all(b == 0xFF for b in data) or all(b == 0x00 for b in data):
            return False, {"error": "Binary consists entirely of blank padding (all 0xFF or 0x00)"}

        crc32_val = cls.calculate_crc32(data)
        sha256_val = cls.calculate_sha256(data)
        bosch16 = cls.calculate_bosch16_sum(data)
        bosch32 = cls.calculate_bosch32_sum(data)

        meta = {
            "crc32": f"0x{crc32_val:08X}",
            "sha256": sha256_val,
            "word_sum16_non_authoritative": f"0x{bosch16:04X}",
            "word_sum32_non_authoritative": f"0x{bosch32:08X}",
            "size_bytes": str(len(data)),
            "ecu_checksum_validated": "false",
        }

        return True, meta

    @classmethod
    def verify_checksum(cls, data: bytes) -> Tuple[bool, Dict[str, str]]:
        """Compatibility alias for structural inspection, not ECU checksum proof."""
        return cls.inspect_binary(data)
