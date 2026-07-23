"""Trionic family definitions and generation profiles.

All checksum and framing rules are cleanly separated per generation.

Pinned upstream loader artifacts are imported under ``firmware/trionic`` with
SHA-256 validation and attribution. The profiles describe the upstream-derived
physical read/write contract; runtime preflight still requires live identity,
voltage, checksum, operator confirmation, backup confirmation, and readback.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple

from domain.memory_map import AddressRange


SOURCE_COMMIT = "4d4c332a166f89c1a9627cd3c9c231fe5a0ed0b9"
SOURCE_URL = f"https://github.com/roffe/Trionic/tree/{SOURCE_COMMIT}"


class EvidenceLevel(str, Enum):
    VERIFIED = "verified"
    STRONGLY_INFERRED = "strongly-inferred"
    EXPERIMENTAL = "experimental"
    UNVERIFIED = "unverified"


class TrionicGeneration(str, Enum):
    T5_2 = "t5.2"
    T5_5 = "t5.5"
    T7 = "t7"
    T8 = "t8"


class TrionicTransport(str, Enum):
    T5_NATIVE_BOOTLOADER = "t5-native-bootloader"
    T7_KWP2000_ROWS = "t7-kwp2000-rows"
    T8_GMLAN_ISOTP = "t8-gmlan-isotp"


@dataclass(frozen=True)
class TrionicPartition:
    name: str
    address_range: AddressRange
    writable_by_stock_flow: bool
    safety_note: str = ""


@dataclass(frozen=True)
class TrionicFlashProfile:
    generation: TrionicGeneration
    transport: TrionicTransport
    image_size: int
    physical_flash_base: int
    request_ids: Tuple[int, ...]
    response_ids: Tuple[int, ...]
    read_block_size: int
    write_block_size: int
    security_seed_level: int
    security_key_level: int
    partitions: Tuple[TrionicPartition, ...]
    programming_phases: Tuple[str, ...]
    checksum_strategy: str
    recovery_strategy: str
    evidence: EvidenceLevel
    physical_read_enabled: bool = False
    physical_write_enabled: bool = False
    requires_external_bootloader: bool = False

    def __post_init__(self) -> None:
        if self.image_size <= 0:
            raise ValueError("Trionic image size must be positive")
        if self.read_block_size <= 0 or self.write_block_size <= 0:
            raise ValueError("Trionic transfer block sizes must be positive")
        if self.security_seed_level <= 0 or self.security_key_level != self.security_seed_level + 1:
            raise ValueError("Trionic SecurityAccess levels are inconsistent")
        for partition in self.partitions:
            if partition.address_range.end_exclusive > self.image_size:
                raise ValueError(f"Partition {partition.name} exceeds the image boundary")

    @property
    def source_reference(self) -> str:
        return SOURCE_URL

    @property
    def writable_ranges(self) -> Tuple[AddressRange, ...]:
        return tuple(
            partition.address_range
            for partition in self.partitions
            if partition.writable_by_stock_flow
        )


T5_PHASES = (
    "connect",
    "identify-flash-device",
    "upload-sram-bootloader",
    "start-sram-bootloader",
    "erase",
    "program-nonblank-blocks",
    "ecu-checksum",
    "reset",
)

T7_PHASES = (
    "connect",
    "start-kwp-session",
    "security-access-05-06",
    "validate-firmware-checksums",
    "erase-routine-52",
    "erase-routine-53",
    "download-primary-region",
    "download-footer-region",
    "readback-verify",
    "stop-session",
)

T8_PHASES = (
    "connect",
    "enter-programming-session",
    "disable-normal-communication",
    "report-programmed-state",
    "enable-programming-mode",
    "security-access-01-02",
    "upload-sram-loader",
    "start-sram-loader",
    "select-and-erase-partitions",
    "program-encoded-blocks",
    "md5-or-readback-verify",
    "loader-exit",
    "reconnect-and-identify",
)


TRIONIC_PROFILES: Dict[TrionicGeneration, TrionicFlashProfile] = {
    TrionicGeneration.T5_2: TrionicFlashProfile(
        generation=TrionicGeneration.T5_2,
        transport=TrionicTransport.T5_NATIVE_BOOTLOADER,
        image_size=0x20000,
        physical_flash_base=0x60000,
        request_ids=(0x005,),
        response_ids=(0x00C,),
        read_block_size=6,
        write_block_size=0x80,
        security_seed_level=0x01,
        security_key_level=0x02,
        partitions=(
            TrionicPartition("application", AddressRange(0, 0x20000), True),
        ),
        programming_phases=T5_PHASES,
        checksum_strategy="T5 footer end pointer plus 32-bit additive checksum",
        recovery_strategy="SRAM loader remains the recovery boundary while stable power is maintained",
        evidence=EvidenceLevel.STRONGLY_INFERRED,
        physical_read_enabled=True,
        physical_write_enabled=True,
        requires_external_bootloader=True,
    ),
    TrionicGeneration.T5_5: TrionicFlashProfile(
        generation=TrionicGeneration.T5_5,
        transport=TrionicTransport.T5_NATIVE_BOOTLOADER,
        image_size=0x40000,
        physical_flash_base=0x40000,
        request_ids=(0x005,),
        response_ids=(0x00C,),
        read_block_size=6,
        write_block_size=0x80,
        security_seed_level=0x01,
        security_key_level=0x02,
        partitions=(
            TrionicPartition("application", AddressRange(0, 0x40000), True),
        ),
        programming_phases=T5_PHASES,
        checksum_strategy="T5 footer end pointer plus 32-bit additive checksum",
        recovery_strategy="SRAM loader remains the recovery boundary while stable power is maintained",
        evidence=EvidenceLevel.STRONGLY_INFERRED,
        physical_read_enabled=True,
        physical_write_enabled=True,
        requires_external_bootloader=True,
    ),
    TrionicGeneration.T7: TrionicFlashProfile(
        generation=TrionicGeneration.T7,
        transport=TrionicTransport.T7_KWP2000_ROWS,
        image_size=0x80000,
        physical_flash_base=0,
        request_ids=(0x220, 0x240, 0x266),
        response_ids=(0x238, 0x258),
        read_block_size=0x40,
        write_block_size=0x80,
        security_seed_level=0x05,
        security_key_level=0x06,
        partitions=(
            TrionicPartition("primary", AddressRange(0x00000, 0x7B000), True),
            TrionicPartition(
                "protected-gap",
                AddressRange(0x7B000, 0x7FE00),
                False,
                "Readable in the reference flow but deliberately omitted from programming",
            ),
            TrionicPartition("footer", AddressRange(0x7FE00, 0x80000), True),
        ),
        programming_phases=T7_PHASES,
        checksum_strategy="T7 FW, F2, and FB checksum set with footer metadata",
        recovery_strategy="Restart KWP session only after determining ECU state; no blind erase retry",
        evidence=EvidenceLevel.STRONGLY_INFERRED,
        physical_read_enabled=True,
        physical_write_enabled=True,
    ),
    TrionicGeneration.T8: TrionicFlashProfile(
        generation=TrionicGeneration.T8,
        transport=TrionicTransport.T8_GMLAN_ISOTP,
        image_size=0x100000,
        physical_flash_base=0,
        request_ids=(0x101, 0x7E0),
        response_ids=(0x7E8, 0x311),
        read_block_size=0x80,
        write_block_size=0x80,
        security_seed_level=0x01,
        security_key_level=0x02,
        partitions=(
            TrionicPartition("boot", AddressRange(0x000000, 0x004000), False, "Critical boot partition"),
            TrionicPartition("nvdm-1", AddressRange(0x004000, 0x006000), False, "VIN/key data risk"),
            TrionicPartition("nvdm-2", AddressRange(0x006000, 0x008000), False, "VIN/key data risk"),
            TrionicPartition("hwio", AddressRange(0x008000, 0x020000), False, "Hardware configuration"),
            TrionicPartition("app-0", AddressRange(0x020000, 0x040000), True),
            TrionicPartition("app-1", AddressRange(0x040000, 0x060000), True),
            TrionicPartition("app-2", AddressRange(0x060000, 0x080000), True),
            TrionicPartition("app-3", AddressRange(0x080000, 0x0C0000), True),
            TrionicPartition("app-4", AddressRange(0x0C0000, 0x100000), True),
        ),
        programming_phases=T8_PHASES,
        checksum_strategy="T8 transformed MD5 layer plus encoded layer-2 checksum metadata",
        recovery_strategy="Broadcast recovery path on 0x011/0x311 with loader-active state detection",
        evidence=EvidenceLevel.STRONGLY_INFERRED,
        physical_read_enabled=True,
        physical_write_enabled=True,
        requires_external_bootloader=True,
    ),
}


def get_trionic_profile(generation: TrionicGeneration) -> TrionicFlashProfile:
    return TRIONIC_PROFILES[generation]
