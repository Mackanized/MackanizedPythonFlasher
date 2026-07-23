from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from security.seed_key import SecurityAccessPolicy


@dataclass(frozen=True)
class EcuCapabilities:
    """Declarative capability contract for ECU modules."""
    supports_identification: bool = False
    supports_full_read: bool = False
    supports_calibration_read: bool = False
    supports_calibration_write: bool = False
    supports_full_write: bool = False
    supports_recovery: bool = False
    supports_dtc_read: bool = False
    supports_checksum_validation: bool = False
    development_status: str = "incomplete"
    evidence_reference: str = ""


class Step:
    """Represents a single 3-byte transformation step for GMLAN Seed/Key."""
    def __init__(self, p1: int, p2: int, p3: int):
        self.p1 = p1
        self.p2 = p2
        self.p3 = p3


class BaseECU(ABC):
    """Base abstract class for GMLAN ECU modules."""

    NAME: str = "Generic ECU"
    CAN_ID_TX: int = 0x7E0
    CAN_ID_RX: int = 0x7E8
    SECURITY_LEVEL: int = 0x01
    SECURITY_POLICY: SecurityAccessPolicy = SecurityAccessPolicy()
    ADDR_LEN_IDENTIFIER: int = 0x00

    SEED_KEY_STEPS: List[Step] = []
    CAPABILITIES: EcuCapabilities = EcuCapabilities()
    PROGRAMMING_STRATEGY: str = ""
    CHECKSUM_STRATEGY: str = ""
    RECOVERY_STRATEGY: str = ""
    STRICT_SIMULATION_CHECKSUM_REGIONS: Tuple[str, ...] = ()
    PHYSICAL_PROGRAMMING_IMPLEMENTED: bool = False
    PHYSICAL_PROGRAMMING_CANDIDATE_IMPLEMENTED: bool = False

    # ── Flash configuration ──────────────────────────────────────────
    TOTAL_FLASH_SIZE: int = 0x200000
    FLASH_SIZE: int = TOTAL_FLASH_SIZE

    READ_HIGH_SPEED_CHUNK: int = 0x80
    READ_FALLBACK_CHUNK: int = 0x02
    READ_FALLBACK_TIMEOUT: float = 0.5

    WRITE_BLOCK_SIZE: int = 4088
    WRITE_ALIGNMENT: int = 1
    ERASE_SIZE: int = 0x180000
    ERASE_TIMEOUT: float = 40.0
    POST_ERASE_DELAY: float = 0.0
    WRITE_TIMEOUT: float = 15.0
    TRANSFER_REQUEST_OVERHEAD: int = 5
    P2_TIMEOUT_S: float = 1.0
    P2_STAR_TIMEOUT_S: float = 10.0

    GAPS: List[Tuple[int, int]] = []

    def calculate_key(self, seed: int) -> int:
        if self.SEED_KEY_STEPS:
            key = seed & 0xFFFF
            for step in self.SEED_KEY_STEPS:
                key = self._apply_step(key, step)
            return key & 0xFFFF

        seed_val = seed & 0xFFFF
        key = ((seed_val >> 5) | (seed_val << 11)) & 0xFFFF
        key = (key + 0xB988) & 0xFFFF
        if self.SECURITY_LEVEL == 0x01:
            key ^= 0x16FB
        return key & 0xFFFF

    @staticmethod
    def _rotate_left(value: int, count: int, bits: int = 16) -> int:
        value &= (1 << bits) - 1
        return ((value << count) | (value >> (bits - count))) & ((1 << bits) - 1)

    @staticmethod
    def _rotate_right(value: int, count: int, bits: int = 16) -> int:
        value &= (1 << bits) - 1
        return ((value >> count) | (value << (bits - count))) & ((1 << bits) - 1)

    @classmethod
    def _apply_step(cls, key: int, step: "Step") -> int:
        op, p0, p1 = step.p1, step.p2, step.p3
        key &= 0xFFFF

        if op == 0x05:
            return cls._rotate_left(key, 8)
        if op == 0x14:
            return (key + (p1 + (p0 << 8))) & 0xFFFF
        if op == 0x2A:
            if p0 < p1:
                return (~key + 1) & 0xFFFF
            return (~key) & 0xFFFF
        if op == 0x37:
            return key & (p0 + (p1 << 8)) & 0xFFFF
        if op == 0x4C:
            return cls._rotate_left(key, p0)
        if op == 0x52:
            return (key | (p0 + (p1 << 8))) & 0xFFFF
        if op == 0x6B:
            return cls._rotate_right(key, p1)
        if op == 0x75:
            return (key + (p0 + (p1 << 8))) & 0xFFFF
        if op == 0x7E:
            rl = cls._rotate_left(key, 8)
            if p0 >= p1:
                return (rl + p1 + (p0 << 8)) & 0xFFFF
            return (rl + p0 + (p1 << 8)) & 0xFFFF
        if op == 0x98:
            return (key - (p1 + (p0 << 8))) & 0xFFFF
        if op == 0xF8:
            return (key - (p0 + (p1 << 8))) & 0xFFFF
        return key

    @abstractmethod
    def get_flash_addresses(self) -> List[Tuple[int, int]]:
        """Returns target memory ranges (start_address, size) for flashing."""
        pass

    @abstractmethod
    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        """
        Returns named flash regions for reading.

        Each entry maps a region name to (start_address, end_address, default_filename).
        """
        pass

    def get_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        if not self.PHYSICAL_PROGRAMMING_IMPLEMENTED:
            return {}
        return self.get_flash_regions()

    def get_simulation_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return self.get_flash_regions()

    def suggest_region_for_file_size(self, file_size: int, *, is_simulation: bool = False) -> Optional[str]:
        """
        Suggest a writable region whose mapped size matches a binary.

        This helper is intentionally write-oriented because it is used by file
        selection before programming preflight. It must not suggest read-only
        partitions as write targets.
        """
        regions = self.get_simulation_write_regions() if is_simulation else self.get_write_regions()
        exact_matches = [
            name
            for name, (start, end, _filename) in regions.items()
            if file_size == end - start
        ]
        if exact_matches:
            return exact_matches[0]
        if file_size == self.TOTAL_FLASH_SIZE and "full" in regions:
            return "full"
        return None

    def get_protected_ranges(self) -> List[Tuple[int, int]]:
        return []

    def get_unreadable_ranges(self) -> List[Tuple[int, int]]:
        return []

    def is_identity_compatible(self, live_identity: Dict[str, str]) -> bool:
        return False

    def validate_programming_checksum(self, data: bytes, region_name: str) -> bool:
        return False

    @property
    def protocol_metadata(self):
        from domain.protocol_metadata import ProtocolMetadata, ProtocolFamily, AddressingMode
        return ProtocolMetadata(
            family=getattr(self, "PROTOCOL_FAMILY", ProtocolFamily.GMLAN),
            addressing=getattr(self, "ADDRESSING_MODE", AddressingMode.NORMAL_11_BIT),
            nominal_bitrate=getattr(self, "NOMINAL_BITRATE", 500_000),
            request_can_id=self.CAN_ID_TX,
            response_can_id=self.CAN_ID_RX,
            p2_timeout_s=getattr(self, "P2_TIMEOUT_S", 1.0),
            p2_star_timeout_s=getattr(self, "P2_STAR_TIMEOUT_S", 10.0),
            evidence_reference=self.CAPABILITIES.evidence_reference,
        )

    def get_verify_pids(self) -> Dict[str, Tuple[int, str]]:
        """
        PIDs to verify before flashing: {name: (pid, description)}.

        Used to search the binary image for matching version numbers,
        ensuring the file is compatible with the target ECU.
        Override in subclass for ECU-specific verification.
        """
        return {}

    def get_info_pids(self) -> List[str]:
        """
        Keys to query in read_ecu_info(). Override to list only PIDs
        supported by this ECU, avoiding slow timeouts on unsupported ones.
        """
        return [
            "vin", "serial", "hardware_type", "supplier", "diag_address",
            "build_date", "programming_date", "main_os", "engine_calib",
            "system_calib", "speedo_calib", "slave_os", "top_speed",
            "radum", "pmc_w", "saab_pn", "end_pn", "base_pn",
        ]

    def is_in_gap(self, address: int) -> bool:
        """Check if an address falls inside a known unreadable/unwritable gap."""
        for gap_start, gap_end in self.GAPS:
            if gap_start <= address < gap_end:
                return True
        return False

    def skip_gaps_forward(self, address: int) -> int:
        """Advance address past any gap it currently sits in."""
        for gap_start, gap_end in self.GAPS:
            if gap_start <= address < gap_end:
                return gap_end
        return address
