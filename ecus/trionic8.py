from typing import Dict, List, Tuple
from domain.memory_map import AddressRange
from domain.protocol_metadata import ProtocolFamily, AddressingMode
from domain.trionic import TrionicGeneration, get_trionic_profile
from .base_ecu import BaseECU, EcuCapabilities, Step


class Trionic8(BaseECU):
    NAME = "Trionic 8"
    REGISTRY_KEY = "t8"
    CAN_ID_TX = 0x7E0
    CAN_ID_RX = 0x7E8
    PROTOCOL_FAMILY = ProtocolFamily.GMLAN
    ADDRESSING_MODE = AddressingMode.NORMAL_11_BIT
    SECURITY_LEVEL = 0x01
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
    )

    SEED_KEY_STEPS = [
        Step(0x6B, 0x65, 0x07),
        Step(0x4C, 0x0A, 0x77),
        Step(0x7E, 0xF8, 0xDA),
        Step(0x98, 0x3F, 0x52),
    ]

    ERASE_SIZE = 0x0E0000

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
