from typing import Dict, List, Tuple
from .base_ecu import BaseECU, EcuCapabilities, Step
from domain.protocol_metadata import ProtocolFamily
from domain.memory_map import AddressRange
from security.edc16c39 import Edc16C39EtasSecurityProvider
from security.seed_key import SecurityAccessPolicy


class EDC16C39(BaseECU):
    NAME = "Bosch EDC16C39"
    REGISTRY_KEY = "edc16c39"
    CAN_ID_TX = 0x7E0
    CAN_ID_RX = 0x7E8
    PROTOCOL_FAMILY = ProtocolFamily.KWP2000_ISOTP
    SECURITY_LEVEL = 0x05
    SECURITY_POLICY = SecurityAccessPolicy(
        request_level=0x05,
        seed_length=6,
        key_length=4,
        max_attempts_per_connection=1,
        required_delay_seconds=10.0,
    )
    P2_STAR_TIMEOUT_S = 40.0
    TRANSFER_REQUEST_OVERHEAD = 2
    CAPABILITIES = EcuCapabilities(
        supports_identification=True,
        supports_full_read=True,
        supports_calibration_read=True,
        supports_full_write=True,
        supports_calibration_write=True,
        supports_checksum_validation=True,
        supports_recovery=True,
        development_status="production-hardware-read-write",
        evidence_reference="EDC16C39 diagnostic profile; physical hardware read and write enabled",
    )

    PROGRAMMING_STRATEGY = "Multi-phase PA/code/data/variant programming coordinator"
    CHECKSUM_STRATEGY = "EDC16C39 SUMMBIGEND self-describing info-block chain"
    RECOVERY_STRATEGY = "Multi-sector checksum and PA recovery strategy"
    PHYSICAL_PROGRAMMING_IMPLEMENTED = True

    FORMAT_C_SERIES_AS_ASCII = True
    ERASE_SIZE = 0x180000
    TOTAL_FLASH_SIZE = 0x200000

    CALIB_START = 0x1C0000
    CALIB_END = 0x1FDF78
    RESERVED_START = 0x1FDF78
    RESERVED_END = 0x1FE000

    def __init__(self):
        super().__init__()
        self._security = Edc16C39EtasSecurityProvider()

    def get_flash_addresses(self) -> List[AddressRange]:
        start = 0x000000
        total = self.TOTAL_FLASH_SIZE
        chunk_size = 0x10000
        ranges: List[AddressRange] = []
        while start < total:
            length = min(chunk_size, total - start)
            ranges.append(AddressRange.from_start_and_length(start, length))
            start += length
        return ranges

    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "calibration": (self.CALIB_START, self.RESERVED_END, "EDC16C39_Calibration_Backup.bin"),
            "full": (0x000000, self.TOTAL_FLASH_SIZE, "EDC16C39_Full_Backup.bin"),
        }

    def get_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "calibration": (self.CALIB_START, self.RESERVED_END, "EDC16C39_Calibration.bin"),
            "full": (0x000000, self.TOTAL_FLASH_SIZE, "EDC16C39_Full.bin"),
        }

    def get_simulation_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return self.get_write_regions()

    def get_protected_ranges(self) -> List[Tuple[int, int]]:
        return [(self.RESERVED_START, self.RESERVED_END)]

    def get_unreadable_ranges(self) -> List[Tuple[int, int]]:
        return []

    def get_verify_pids(self) -> Dict[str, Tuple[int, str]]:
        return {
            "main_os": (0xC1, "Main OS"),
        }

    def validate_programming_checksum(self, data: bytes, region_name: str) -> bool:
        if region_name != "full" or len(data) != self.TOTAL_FLASH_SIZE:
            return False
        from firmware.edc16c39 import EDC16C39ChecksumError, inspect_edc16c39_checksums
        try:
            return inspect_edc16c39_checksums(data).valid
        except EDC16C39ChecksumError:
            return False

    def is_identity_compatible(self, live_identity: Dict[str, str]) -> bool:
        vin = live_identity.get("vin", "").strip()
        main_os = live_identity.get("main_os", "").strip()
        return bool(vin) or bool(main_os)

    def get_info_pids(self) -> List[str]:
        return [
            "vin", "serial", "diag_address", "programming_date",
            "end_pn", "saab_pn",
            "main_os",
            "calibration_set", "codefile_version",
            "hardware_type", "supplier",
            "diag_data_id", "tester_serial",
        ]