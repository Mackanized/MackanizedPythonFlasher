from typing import Dict, List, Tuple
from domain.memory_map import AddressRange
from .base_ecu import BaseECU, EcuCapabilities, Step


class Motronic961(BaseECU):
    NAME = "Bosch ME9.6.1"
    REGISTRY_KEY = "me961"
    CAN_ID_TX = 0x7E0
    CAN_ID_RX = 0x7E8
    TOTAL_FLASH_SIZE = 0x200000
    FLASH_SIZE = TOTAL_FLASH_SIZE
    CAPABILITIES = EcuCapabilities(
        supports_identification=True,
        supports_full_read=True,
        supports_calibration_read=True,
        supports_full_write=True,
        supports_calibration_write=True,
        supports_recovery=True,
        supports_checksum_validation=True,
        development_status="production-hardware-read-write",
        evidence_reference="MED9.6.1 diagnostic profile; physical hardware read and write enabled",
    )

    PHYSICAL_PROGRAMMING_IMPLEMENTED = True
    PROGRAMMING_STRATEGY = "MED9.6.1 CCP calibration programming"
    CHECKSUM_STRATEGY = "MED9.6.1 CCP 0xC001 CRC"
    RECOVERY_STRATEGY = "CCP recovery session"

    READ_HIGH_SPEED_CHUNK = 0xFA  # 250 bytes

    SEED_KEY_STEPS = [
        Step(0xF8, 0x1F, 0x80),
        Step(0x05, 0x31, 0x6B),
        Step(0x2A, 0x03, 0x4D),
        Step(0x75, 0x68, 0x15),
    ]

    ERASE_SIZE = 0x180000
    GAPS = [(0x1C0000, 0x1C2000)]

    def get_flash_addresses(self) -> List[AddressRange]:
        start = 0x000000
        total = 0x200000
        chunk_size = 0x10000
        ranges = []
        while start < total:
            length = min(chunk_size, total - start)
            ranges.append(AddressRange.from_start_and_length(start, length))
            start += length
        return ranges

    # ── Checksum / CVN info (from A2L 430LDY6000_MED9.6.1) ───────────
    # CCP checksum algorithm: 0xC001 (manufacturer-specific, CRC table variant 2)
    # CCP BUILD_CHKSUM command: 0x0D, result via RequestRoutineResults, RNC 0x23 = busy
    # Checksum scope: ACTIVE_PAGE (active calibration page only)
    #
    # CVN (Calibration Verification Number) — SAE J1979 Mode $09 VIT $06
    # Stored in RAM, computed at runtime by ECU over calibration data:
    #   cvn2h_w  0x7FC6BA  (2 bytes)  2nd CVN high word
    #   cvn2l_w  0x7FC6BC  (2 bytes)  2nd CVN low word
    #   cvn3h_w  0x7FC6BE  (2 bytes)  3rd CVN high word
    #   cvn3l_w  0x7FC6C0  (2 bytes)  3rd CVN low word
    #   cvn4h_w  0x7FC6C2  (2 bytes)  4th CVN high word
    #   cvn4l_w  0x7FC6C4  (2 bytes)  4th CVN low word
    #   cvnh_w   0x7FC6C6  (2 bytes)  1st CVN high word
    #   cvnl_w   0x7FC6C8  (2 bytes)  1st CVN low word
    #
    # Checksum status flags (RAM):
    #   B_cksbrdy  0x7FC6B8  (1 byte)  checksum calculation ready
    #   B_cksnew   (nearby)            checksum is current
    #
    # Program checksum (ETK):
    #   CODE_CHK  prg_data=0x9021A0 (2 bytes)  prg_eram=0x90039C (2 bytes)
    #
    # Calibration IDs (RAM):
    #   calibid1  0x80331A  (16 bytes)
    #   calibid2  0x80332A  (16 bytes)
    #   calibid3  0x80333A  (16 bytes)

    def is_identity_compatible(self, live_identity: Dict[str, str]) -> bool:
        vin = live_identity.get("vin", "").strip()
        hardware = live_identity.get("hardware_type", "").strip()
        return len(vin) == 17 or bool(hardware)

    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "calibration": (0x1C2000, 0x1F0000, "ME961_Calibration_Backup.bin"),
            "full": (0x000000, 0x200000, "ME961_Full_ECU_Backup.bin"),
        }

    def get_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "calibration": (0x1C2000, 0x1F0000, "ME961_Calibration_Backup.bin"),
            "full": (0x040000, 0x200000, "ME961_Full_ECU_Backup.bin"),
        }

    def get_verify_pids(self) -> Dict[str, Tuple[int, str]]:
        return {
            "engine_calib": (0xC2, "Engine Calib"),
            "system_calib": (0xC3, "System Calib"),
            "speedo_calib": (0xC4, "Speedo Calib"),
        }

    def get_info_pids(self) -> List[str]:
        return [
            "vin", "serial", "diag_address", "programming_date",
            "end_pn", "base_pn",
            "main_os", "engine_calib", "system_calib", "speedo_calib",
            "calibration_set", "codefile_version",
            "diag_data_id", "tester_serial",
        ]
