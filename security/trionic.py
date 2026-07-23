"""Trionic-specific SecurityAccess primitives."""

from typing import Tuple


def trionic7_candidate_keys(seed: int) -> Tuple[int, int]:
    """Return the two known T7 0x05/0x06 key candidates.

    Trionic7Client.authenticate() tries both in sequence, matching the
    reference TrionicCANLib (KWPHandler.requestSequrityAccess), which does
    the same. Unlike the reference, which ignores negative-response codes
    entirely, the caller must abort immediately on a lockout-indicating NRC
    (0x36 exceeded attempts, 0x37 required time delay not expired) rather
    than feed it a second live key attempt; only NRC 0x35 (invalid key)
    justifies trying the other candidate.
    """
    if not 0 <= seed <= 0xFFFF:
        raise ValueError("T7 seed must fit in 16 bits")

    def calculate(xor_value: int, subtract_value: int) -> int:
        return ((((seed << 2) & 0xFFFF) ^ xor_value) - subtract_value) & 0xFFFF

    return (
        calculate(0x8142, 0x2356),
        calculate(0x4081, 0x1F6F),
    )
