from typing import Dict, List, Tuple
from .base_ecu import BaseECU, Step


class Motronic96(BaseECU):
    NAME = "Bosch ME9.6"
    CAN_ID_TX = 0x7E0
    CAN_ID_RX = 0x7E8
    SECURITY_LEVEL = 0x01

    SEED_KEY_STEPS = [
        Step(0x98, 0x38, 0x08),
        Step(0x7E, 0xF2, 0x94),
        Step(0x6B, 0xE0, 0x02),
        Step(0x4C, 0x03, 0x48),
    ]

    ERASE_SIZE = 0x180000

    def get_flash_addresses(self) -> List[Tuple[int, int]]:
        return [(0x000000, 0x200000)]

    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "full": (0x000000, 0x200000, "ME96_Full_Backup.bin"),
        }
