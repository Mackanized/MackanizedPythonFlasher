from typing import Dict, List, Optional, Tuple
from domain.memory_map import AddressRange
from domain.protocol_metadata import ProtocolFamily, AddressingMode
from domain.trionic import TrionicGeneration, get_trionic_profile
from security.seed_key import SecurityAccessPolicy
from .base_ecu import BaseECU, EcuCapabilities


class Trionic8(BaseECU):
    NAME = "Trionic 8"
    REGISTRY_KEY = "t8"
    CAN_ID_TX = 0x7E0
    CAN_ID_RX = 0x7E8
    PROTOCOL_FAMILY = ProtocolFamily.GMLAN
    ADDRESSING_MODE = AddressingMode.NORMAL_11_BIT
    # 0xFD is the SecurityAccess level real T8 hardware expects for this
    # flow (0xFB is a known alternate for some ECU variants; see
    # calculate_key below). BaseECU's SECURITY_LEVEL alone does not affect
    # the wire byte — Trionic8 overrides calculate_key() directly, and the
    # actual 0x27 request byte comes from SECURITY_POLICY.request_level.
    SECURITY_LEVEL = 0xFD
    SECURITY_POLICY = SecurityAccessPolicy(request_level=0xFD, response_level=0xFE)
    TOTAL_FLASH_SIZE = 0x100000
    FLASH_SIZE = TOTAL_FLASH_SIZE
    READ_HIGH_SPEED_CHUNK = 0x80
    WRITE_BLOCK_SIZE = 0xEA
    WRITE_ALIGNMENT = 0x80
    PHYSICAL_WRITE_EVIDENCE_REQUIRED = False
    PHYSICAL_PROGRAMMING_CANDIDATE_IMPLEMENTED = True
    PHYSICAL_PROGRAMMING_IMPLEMENTED = True
    PROFILE = get_trionic_profile(TrionicGeneration.T8)
    CHECKSUM_STRATEGY = "T8 transformed MD5 layer plus encoded layer-2 checksum metadata"
    PROGRAMMING_STRATEGY = "GMLAN programming session, stock SRAM loader upload, app partition erase/program, readback"
    RECOVERY_STRATEGY = "0x011/0x311 recovery session/security path with stock loader state detection"
    STRICT_SIMULATION_CHECKSUM_REGIONS = ("full",)

    CAPABILITIES = EcuCapabilities(
        supports_identification=True,
        supports_full_read=True,
        supports_full_write=True,
        supports_calibration_write=False,
        supports_checksum_validation=True,
        supports_recovery=True,
        development_status="hardware-enabled-upstream-derived",
        evidence_reference=(
            "Trionic 8 GMLAN stock SRAM loader read/write ported from the pinned upstream "
            "reference implementation (see firmware/trionic loader manifest); physical hardware "
            "read and write enabled, gated by standard operator/voltage/checksum/readback preflight."
        ),
    )

    ERASE_SIZE = 0x0E0000

    def calculate_key(self, seed: int, level: Optional[int] = None) -> int:
        """T8 seed-to-key transform for SecurityAccess levels 0x01/0xFB/0xFD.

        Verified against two independent implementations, which agree
        exactly across multiple test seeds. Overrides BaseECU's generic
        SEED_KEY_STEPS chain, which does not apply to T8 — that path
        produced a different, non-functional key.

        ``level`` defaults to this ECU's configured SECURITY_POLICY level
        (0xFD); callers that need a different session level — e.g. the
        alternate-bootloader entry path, which authenticates at level
        0x01 — pass it explicitly. Level 0x01 applies neither of the
        0xFD/0xFB post-transforms below, matching the reference algorithm
        for that level.
        """
        key = ((seed >> 5) | (seed << 11)) & 0xFFFF
        key = (key + 0xB988) & 0xFFFF
        if level is None:
            level = self.SECURITY_POLICY.request_level
        if level == 0xFD:
            key //= 3
            key ^= 0x8749
            key = (key + 0x0ACF) & 0xFFFF
            key ^= 0x81BF
        elif level == 0xFB:
            key ^= 0x8749
            key = (key + 0x06D3) & 0xFFFF
            key ^= 0xCFDF
        return key & 0xFFFF

    def get_flash_addresses(self) -> List[AddressRange]:
        return [
            AddressRange(0x000000, 0x020000),
            AddressRange(0x020000, 0x100000),
        ]

    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "boot": (0x000000, 0x020000, "Trionic8_Boot.bin"),
            "main": (0x020000, 0x100000, "Trionic8_Main.bin"),
            "full": (0x000000, 0x100000, "Trionic8_Full.bin"),
        }

    def get_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "full": (0x000000, 0x100000, "Trionic8_Full.bin"),
        }

    def get_simulation_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return self.get_write_regions()

    def get_protected_ranges(self) -> List[Tuple[int, int]]:
        return [
            (partition.address_range.start, partition.address_range.end_exclusive)
            for partition in self.PROFILE.partitions
            if not partition.writable_by_stock_flow
        ]

    def get_unreadable_ranges(self) -> List[Tuple[int, int]]:
        return []

    def validate_programming_checksum(self, data: bytes, region_name: str) -> bool:
        if region_name != "full" or len(data) != self.TOTAL_FLASH_SIZE:
            return False
        from firmware.trionic.checksums import TrionicChecksumError, inspect_t8_checksums
        try:
            return inspect_t8_checksums(data).valid
        except TrionicChecksumError:
            return False

    def is_identity_compatible(self, live_identity: Dict[str, str]) -> bool:
        family = live_identity.get("ecu_family", "").strip().lower()
        vin = live_identity.get("vin", "").strip()
        hardware = live_identity.get("hardware_type", "").strip()
        return family == self.NAME.lower() and (len(vin) == 17 or bool(hardware))
