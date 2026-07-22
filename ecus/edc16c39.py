from typing import Dict, List, Tuple
from .base_ecu import BaseECU, Step


class EDC16C39(BaseECU):
    NAME = "Bosch EDC16C39"
    CAN_ID_TX = 0x7E0
    CAN_ID_RX = 0x7E8
    SECURITY_LEVEL = 0x01

    FORMAT_C_SERIES_AS_ASCII = True

    SEED_KEY_STEPS = [
        Step(0x6B, 0x7A, 0x04),
        Step(0x7E, 0x82, 0x74),
        Step(0x4C, 0x05, 0x43),
        Step(0x05, 0x1B, 0x9D),
    ]

    ERASE_SIZE = 0x180000

    # ── Flash layout (from A2L P_581_UO54JD11_EDC16C39_corr2_TTiD_Z19DTR) ──
    #   Pst10000  CODE FLASH    0x100000  0x140000   (0x100000 - 0x150000)
    #   Dst150000 RESERVED      0x150000  0x70000    (0x150000 - 0x1C0000)
    #   Dst1C0000 DATA FLASH    0x1C0000  0x3DF78    (0x1C0000 - 0x1FDF78)  calibration
    #   Dst1FDF78 RESERVED       0x1FDF78  0x88       (0x1FDF78 - 0x1FE000)
    #   EPK at 0x1C01A4
    TOTAL_FLASH_SIZE = 0x200000

    # Calibration region is the DATA FLASH segment; ends at the A2L boundary
    # (0x1FDF78). Padded to a round 0x1FE000 for a clean read/write footprint
    # that preserves the trailing reserved segment without crossing 0x200000.
    CALIB_START = 0x1C0000
    CALIB_END = 0x1FE000

    def get_flash_addresses(self) -> List[Tuple[int, int]]:
        start = 0x000000
        total = self.TOTAL_FLASH_SIZE
        chunk_size = 0x10000
        ranges: List[Tuple[int, int]] = []
        while start < total:
            length = min(chunk_size, total - start)
            ranges.append((start, length))
            start += length
        return ranges

    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "calibration": (self.CALIB_START, self.CALIB_END, "EDC16C39_Calibration_Backup.bin"),
            "full": (0x000000, self.TOTAL_FLASH_SIZE, "EDC16C39_Full_Backup.bin"),
        }

    def get_write_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "calibration": (self.CALIB_START, self.CALIB_END, "EDC16C39_Calibration_Backup.bin"),
            "full": (0x040000, self.TOTAL_FLASH_SIZE, "EDC16C39_Full_Backup.bin"),
        }

    def get_verify_pids(self) -> Dict[str, Tuple[int, str]]:
        return {
            "main_os": (0xC1, "Main OS"),
        }

    def get_info_pids(self) -> List[str]:
        return [
            "vin", "serial", "diag_address", "programming_date",
            "end_pn", "saab_pn",
            "main_os",
            "calibration_set", "codefile_version",
            "hardware_type", "supplier",
            "diag_data_id", "tester_serial",
        ]