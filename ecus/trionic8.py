from typing import Dict, List, Tuple
from .base_ecu import BaseECU, Step


class Trionic8(BaseECU):
    NAME = "Trionic 8"
    CAN_ID_TX = 0x7E0
    CAN_ID_RX = 0x7E8
    SECURITY_LEVEL = 0x01
    TOTAL_FLASH_SIZE = 0x100000

    SEED_KEY_STEPS = [
        Step(0x6B, 0x65, 0x07),
        Step(0x4C, 0x0A, 0x77),
        Step(0x7E, 0xF8, 0xDA),
        Step(0x98, 0x3F, 0x52),
    ]

    ERASE_SIZE = 0x0E0000

    def get_flash_addresses(self) -> List[Tuple[int, int]]:
        return [
            (0x000000, 0x020000),
            (0x020000, 0x100000),
        ]

    def get_flash_regions(self) -> Dict[str, Tuple[int, int, str]]:
        return {
            "boot": (0x000000, 0x020000, "Trionic8_Boot.bin"),
            "main": (0x020000, 0x100000, "Trionic8_Main.bin"),
            "full": (0x000000, 0x100000, "Trionic8_Full.bin"),
        }
