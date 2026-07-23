"""Trionic-specific SecurityAccess primitives."""

from typing import Tuple


def trionic7_candidate_keys(seed: int) -> Tuple[int, int, int, int, int]:
    """Return the five known T7 0x05/0x06 key candidates (methods 0-4).

    Different physical T7 ECUs accept different candidates, so
    Trionic7Client.authenticate() tries them in sequence, stopping at the
    first one that's accepted. The caller must abort immediately on a
    lockout-indicating negative response (NRC 0x36 exceeded attempts, 0x37
    required time delay not expired) rather than feed it another live key
    attempt; only NRC 0x35 (invalid key) justifies trying the next
    candidate.
    """
    if not 0 <= seed <= 0xFFFF:
        raise ValueError("T7 seed must fit in 16 bits")

    def calculate(xor_value: int, subtract_value: int) -> int:
        return ((((seed << 2) & 0xFFFF) ^ xor_value) - subtract_value) & 0xFFFF

    return (
        calculate(0x8142, 0x2356),
        calculate(0x4081, 0x1F6F),
        calculate(0x03DC, 0x2356),
        calculate(0x03D7, 0x2356),
        calculate(0x0409, 0x2356),
    )
