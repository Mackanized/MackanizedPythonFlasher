"""Declarative diagnostic protocol metadata owned by the domain layer."""

from dataclasses import dataclass
from enum import Enum


class ProtocolFamily(str, Enum):
    GMLAN = "gmlan"
    KWP2000_ISOTP = "kwp2000-isotp"
    TRIONIC5_BOOTLOADER = "trionic5-bootloader"
    KWP2000_SAAB_CAN = "kwp2000-saab-can"


class AddressingMode(str, Enum):
    NORMAL_11_BIT = "normal-11-bit"
    TRIONIC5_NATIVE = "trionic5-native"
    KWP2000_SAAB_ROWS = "kwp2000-saab-rows"


@dataclass(frozen=True)
class ProtocolMetadata:
    family: ProtocolFamily
    addressing: AddressingMode
    nominal_bitrate: int
    request_can_id: int
    response_can_id: int
    p2_timeout_s: float = 1.0
    p2_star_timeout_s: float = 10.0
    evidence_reference: str = ""

    def __post_init__(self) -> None:
        if self.nominal_bitrate <= 0:
            raise ValueError("Protocol bitrate must be positive")
        for label, can_id in (("request", self.request_can_id), ("response", self.response_can_id)):
            if not 0 <= can_id <= 0x7FF:
                raise ValueError(f"{label} CAN ID is not an 11-bit identifier")
        if self.request_can_id == self.response_can_id:
            raise ValueError("Protocol request and response CAN IDs must differ")
        if self.p2_timeout_s <= 0 or self.p2_star_timeout_s < self.p2_timeout_s:
            raise ValueError("Protocol timing values are inconsistent")
