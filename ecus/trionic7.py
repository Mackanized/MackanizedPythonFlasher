"""Hardware-enabled Trionic 7 ECU definition."""

from typing import Dict, List, Tuple

from domain.memory_map import AddressRange
from domain.protocol_metadata import AddressingMode, ProtocolFamily
from domain.trionic import TrionicGeneration, get_trionic_profile
from ecus.base_ecu import BaseECU, EcuCapabilities


class Trionic7(BaseECU):
    NAME = "Trionic 7"
    REGISTRY_KEY = "t7"
    CAN_ID_TX = 0x240
    CAN_ID_RX = 0x258
    PROTOCOL_FAMILY = ProtocolFamily.KWP2000_SAAB_CAN
    ADDRESSING_MODE = AddressingMode.KWP2000_SAAB_ROWS
    NOMINAL_BITRATE = 500_000
    SECURITY_LEVEL = 0x05
    TOTAL_FLASH_SIZE = 0x80000
    FLASH_SIZE = TOTAL_FLASH_SIZE
    READ_HIGH_SPEED_CHUNK = 0x40
    WRITE_BLOCK_SIZE = 0x80
    WRITE_ALIGNMENT = 0x80
    REQUIRE_TRANSFER_EXIT = False
    PHYSICAL_WRITE_EVIDENCE_REQUIRED = False
    PHYSICAL_PROGRAMMING_CANDIDATE_IMPLEMENTED = True
    PHYSICAL_PROGRAMMING_IMPLEMENTED = True
    SECURITY_KEY_VARIANT = 0
    GAPS = [(0x7B000, 0x7FE00)]
    PROFILE = get_trionic_profile(TrionicGeneration.T7)
    CHECKSUM_STRATEGY = "Trionic 7 FW/F2/FB checksum set"
    PROGRAMMING_STRATEGY = "Saab KWP rows, erase 0x52/0x53, primary/footer downloads, strict readback"
    RECOVERY_STRATEGY = "restart only after KWP/programming-state assessment; never repeat erase blindly"
    STRICT_SIMULATION_CHECKSUM_REGIONS = ("full",)
    CAPABILITIES = EcuCapabilities(
        supports_identification=True,
        supports_full_read=True,
        supports_full_write=True,
        supports_calibration_write=False,
        supports_recovery=True,
        supports_checksum_validation=True,
        development_status="hardware-enabled-upstream-derived",
    )

    def get_flash_addresses(self) -> List[AddressRange]:
        return [AddressRange(0x000000, self.TOTAL_FLASH_SIZE)]

    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "full": (0x000000, self.TOTAL_FLASH_SIZE, "Trionic7_Full.bin"),
        }

    def get_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return self.get_flash_regions()

    def get_simulation_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return self.get_write_regions()

    def get_unreadable_ranges(self) -> List[Tuple[int, int]]:
        # The reference reader dumps all 512 KiB. This gap is a programming
        # exclusion, not an unreadable address range.
        return []

    def get_protected_ranges(self) -> List[Tuple[int, int]]:
        return list(self.GAPS)

    def validate_programming_checksum(self, data: bytes, region_name: str) -> bool:
        if region_name != "full":
            return False
        from firmware.trionic.checksums import TrionicChecksumError, inspect_t7_checksums
        try:
            return inspect_t7_checksums(data).valid
        except TrionicChecksumError:
            return False

    def is_identity_compatible(self, live_identity: Dict[str, str]) -> bool:
        family = live_identity.get("ecu_family", "").strip().lower()
        vin = live_identity.get("vin", "").strip()
        hardware = live_identity.get("hardware_type", "").strip()
        return family == self.NAME.lower() and (len(vin) == 17 or bool(hardware))
