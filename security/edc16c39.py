"""EDC16C39 level-05 SecurityAccess implementation."""

from __future__ import annotations

from security.seed_key import ISecurityProvider


TABLE_ENTRY_2 = 0x0A24C4C1


def edc16c39_etas_key_bytes(seed: bytes) -> bytes:
    """Return the four-byte key produced by the archived ``SEED.DLL``."""
    if len(seed) != 6:
        raise ValueError("EDC16C39 ETAS SecurityAccess requires a six-byte seed")

    register = int.from_bytes(seed[1:5], "big")
    # The original x86 signed division truncates toward zero.  Python's //
    # floors negative values, so spell out the only negative case explicitly.
    numerator = seed[0] - 1
    table_index = abs(numerator) // 2 * (-1 if numerator < 0 else 1)
    polynomial = TABLE_ENTRY_2 if table_index == 2 else 0
    iterations = min(seed[5] + 0x23, 0xFF)

    for _ in range(iterations):
        msb_was_set = bool(register & 0x80000000)
        register = (register << 1) & 0xFFFFFFFF
        if msb_was_set:
            register ^= polynomial
    return register.to_bytes(4, "big")


class Edc16C39EtasSecurityProvider(ISecurityProvider):
    """Adapter for the integer-based application SecurityAccess interface."""

    def calculate_key(self, seed: int) -> int:
        if not 0 <= seed < (1 << 48):
            raise ValueError("EDC16C39 ETAS seed must fit in 48 bits")
        return int.from_bytes(edc16c39_etas_key_bytes(seed.to_bytes(6, "big")), "big")
