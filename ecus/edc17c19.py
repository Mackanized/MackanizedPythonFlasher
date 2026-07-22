from typing import Dict, List, Tuple
from .base_ecu import BaseECU, Step


class EDC17C19(BaseECU):
    NAME = "Bosch EDC17C19"
    CAN_ID_TX = 0x7E0
    CAN_ID_RX = 0x7E8
    SECURITY_LEVEL = 0x01

    SEED_KEY_STEPS = [
        Step(0x75, 0x50, 0xB0),
        Step(0x6B, 0x2C, 0x01),
        Step(0x05, 0xC3, 0x42),
        Step(0x14, 0x40, 0x93),
    ]

    ERASE_SIZE = 0x180000

    def get_flash_addresses(self) -> List[Tuple[int, int]]:
        return [(0x000000, 0x200000)]

    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "full": (0x000000, 0x200000, "EDC17C19_Full_Backup.bin"),
        }
