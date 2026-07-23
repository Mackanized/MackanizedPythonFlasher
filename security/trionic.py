"""Trionic-specific SecurityAccess primitives."""

from typing import Tuple


def trionic7_candidate_keys(seed: int) -> Tuple[int, int]:
    """Return the two known T7 0x05/0x06 key candidates.

    Selection must be driven by a verified ECU identity or replay trace.  The
    caller must not try both automatically on hardware because repeated wrong
    keys can trigger a lockout.
    """
    if not 0 <= seed <= 0xFFFF:
        raise ValueError("T7 seed must fit in 16 bits")

    def calculate(xor_value: int, subtract_value: int) -> int:
        return ((((seed << 2) & 0xFFFF) ^ xor_value) - subtract_value) & 0xFFFF

    return (
        calculate(0x8142, 0x2356),
        calculate(0x4081, 0x1F6F),
    )
