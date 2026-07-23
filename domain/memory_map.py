"""Validated, half-open ECU address ranges and memory maps."""

from dataclasses import dataclass
from typing import Iterable, Optional, Tuple


@dataclass(frozen=True, order=True)
class AddressRange:
    """A non-empty ``[start, end_exclusive)`` address range."""

    start: int
    end_exclusive: int

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("Address range start cannot be negative")
        if self.end_exclusive <= self.start:
            raise ValueError("Address range end must be greater than start")

    @classmethod
    def from_start_and_length(cls, start: int, length: int) -> "AddressRange":
        if length <= 0:
            raise ValueError("Address range length must be positive")
        return cls(start, start + length)

    @property
    def length(self) -> int:
        return self.end_exclusive - self.start

    def contains(self, address: int) -> bool:
        return self.start <= address < self.end_exclusive

    def overlaps(self, other: "AddressRange") -> bool:
        return self.start < other.end_exclusive and other.start < self.end_exclusive

    def as_tuple(self) -> Tuple[int, int]:
        return self.start, self.end_exclusive


@dataclass(frozen=True)
class MemoryRegion:
    """Named ECU memory range; size is always derived from its boundaries."""

    name: str
    start_address: int
    end_address: int
    filename: str = ""
    is_readable: bool = True
    is_writable: bool = False
    is_protected: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Memory region name is required")
        AddressRange(self.start_address, self.end_address)
        if self.is_protected and self.is_writable:
            raise ValueError("A protected memory region cannot be writable")

    @property
    def address_range(self) -> AddressRange:
        return AddressRange(self.start_address, self.end_address)

    @property
    def size(self) -> int:
        return self.end_address - self.start_address

    @property
    def hex_start(self) -> str:
        return f"0x{self.start_address:08X}"

    @property
    def hex_end(self) -> str:
        return f"0x{self.end_address:08X}"

    @property
    def size_kb(self) -> float:
        return round(self.size / 1024.0, 1)


class MemoryMap:
    """Validated immutable view of an ECU address space."""

    def __init__(self, ecu_name: str, total_flash_size: int, regions: Iterable[MemoryRegion]):
        if not ecu_name.strip():
            raise ValueError("ECU name is required")
        if total_flash_size <= 0:
            raise ValueError("Total flash size must be positive")
        ordered = tuple(sorted(regions, key=lambda region: (region.start_address, region.end_address)))
        for region in ordered:
            if region.end_address > total_flash_size:
                raise ValueError(f"Region {region.name!r} exceeds the ECU flash boundary")
        self.ecu_name = ecu_name
        self.total_flash_size = total_flash_size
        self._regions = ordered

    @property
    def regions(self) -> Tuple[MemoryRegion, ...]:
        return self._regions

    def get_region_by_name(self, name: str) -> Optional[MemoryRegion]:
        normalized = name.casefold()
        return next((region for region in self._regions if region.name.casefold() == normalized), None)

    def find_region_for_address(self, address: int) -> Optional[MemoryRegion]:
        return next((region for region in self._regions if region.address_range.contains(address)), None)
