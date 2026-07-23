"""Seed-Key Security Access Interfaces, Models, and Algorithms."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Step:
    """Represents a single 3-byte transformation step for GMLAN Seed/Key."""
    p1: int
    p2: int
    p3: int


@dataclass(frozen=True)
class SecurityAccessPolicy:
    """Security Access policy contract per diagnostic session level."""
    request_level: int = 0x01
    response_level: int = 0x02
    seed_length: int = 2
    key_length: int = 2
    max_attempts_per_connection: int = 3
    required_delay_seconds: float = 10.0


class ISecurityProvider(ABC):
    """Abstract interface for SecurityAccess seed-key providers."""

    @abstractmethod
    def calculate_key(self, seed: int) -> int:
        pass


class GmlanSecurityProvider(ISecurityProvider):
    """Standard GMLAN 4-step shift/XOR seed-key calculation provider."""

    def __init__(self, security_level: int = 0x01, steps: List[Step] = None):
        self.security_level = security_level
        self.steps = steps or []

    def calculate_key(self, seed: int) -> int:
        if self.steps:
            key = seed & 0xFFFF
            for step in self.steps:
                key = self._apply_step(key, step)
            return key & 0xFFFF

        seed_val = seed & 0xFFFF
        key = ((seed_val >> 5) | (seed_val << 11)) & 0xFFFF
        key = (key + 0xB988) & 0xFFFF
        if self.security_level == 0x01:
            key ^= 0x16FB
        return key & 0xFFFF

    @staticmethod
    def _apply_step(key: int, step: Step) -> int:
        d = (key >> 8) & 0xFF
        e = key & 0xFF
        t1 = (d + step.p1) & 0xFF
        t2 = (e + step.p2) & 0xFF
        return ((t1 << 8) | t2) ^ step.p3
