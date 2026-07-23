"""Hardware-enabled Trionic 5.2 and 5.5 ECU definitions."""

from typing import Dict, List, Tuple

from domain.memory_map import AddressRange
from domain.protocol_metadata import AddressingMode, ProtocolFamily
from domain.trionic import TrionicGeneration, get_trionic_profile
from ecus.base_ecu import BaseECU, EcuCapabilities


class _Trionic5Base(BaseECU):
    REGISTER_ECU = False
    CAN_ID_TX = 0x005
    CAN_ID_RX = 0x00C
    PROTOCOL_FAMILY = ProtocolFamily.TRIONIC5_BOOTLOADER
    ADDRESSING_MODE = AddressingMode.TRIONIC5_NATIVE
    NOMINAL_BITRATE = 500_000
    READ_HIGH_SPEED_CHUNK = 6
    WRITE_BLOCK_SIZE = 0x80
    WRITE_ALIGNMENT = 0x80
    REQUIRE_TRANSFER_EXIT = False
    PHYSICAL_WRITE_EVIDENCE_REQUIRED = False
    PHYSICAL_PROGRAMMING_CANDIDATE_IMPLEMENTED = True
    PHYSICAL_PROGRAMMING_IMPLEMENTED = True
    CHECKSUM_STRATEGY = "T5 footer end pointer plus 32-bit additive checksum"
    PROGRAMMING_STRATEGY = "native T5 SRAM loader, whole-chip erase, sparse 0x80-byte blocks, C8 checksum, readback"
    RECOVERY_STRATEGY = "retain stable power and resume only after native-loader state assessment"
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
        return [AddressRange(0, self.TOTAL_FLASH_SIZE)]

    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "full": (0x000000, self.TOTAL_FLASH_SIZE, f"{self.NAME}_Full.bin"),
        }

    def get_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return self.get_flash_regions()

    def get_simulation_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return self.get_write_regions()

    def validate_programming_checksum(self, data: bytes, region_name: str) -> bool:
        if region_name != "full":
            return False
        from domain.trionic_firmware import inspect_t5_checksum
        return inspect_t5_checksum(data).valid

    def is_identity_compatible(self, live_identity: Dict[str, str]) -> bool:
        family = live_identity.get("ecu_family", "").strip().lower()
        chip = live_identity.get("flash_chip_id", "").strip()
        base = live_identity.get("physical_flash_base", "").strip()
        return family == self.NAME.lower() and bool(chip) and bool(base)


class Trionic52(_Trionic5Base):
    REGISTER_ECU = True
    NAME = "Trionic 5.2"
    REGISTRY_KEY = "t52"
    TOTAL_FLASH_SIZE = 0x20000
    FLASH_SIZE = TOTAL_FLASH_SIZE
    PROFILE = get_trionic_profile(TrionicGeneration.T5_2)


class Trionic55(_Trionic5Base):
    REGISTER_ECU = True
    NAME = "Trionic 5.5"
    REGISTRY_KEY = "t55"
    TOTAL_FLASH_SIZE = 0x40000
    FLASH_SIZE = TOTAL_FLASH_SIZE
    PROFILE = get_trionic_profile(TrionicGeneration.T5_5)
