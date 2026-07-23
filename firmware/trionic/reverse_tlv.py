"""Generic reverse tag-length-value footer walker.

Both the T5 and T7 firmware footers use the same underlying layout: fields
are stored forward as ``[...value bytes...][identifier][length]``, repeated,
and read backward starting near the end of the image. T5 and T7 previously
each carried their own independent implementation of this same walk; this
module is the one shared primitive, parameterized just enough (start
position, terminator identifiers) to cover both.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass(frozen=True)
class ReverseTlvField:
    identifier: int
    # Value bytes in *reverse* file order — position 0 is the byte closest
    # to the identifier/length pair (the forward-order *last* value byte).
    # This is the natural order fields are encountered walking backward;
    # callers that want forward order do ``bytes(reversed(field.data))``.
    data: bytes
    # File positions of `data`, in the same (reverse) order. Empty for a
    # terminator field.
    positions: Tuple[int, ...]


def walk_reverse_tlv(
    data: bytes,
    *,
    end: Optional[int] = None,
    terminators: Tuple[int, ...] = (),
    max_fields: int = 128,
) -> Tuple[ReverseTlvField, ...]:
    """Walk a reverse TLV footer backward from ``end`` (default ``len(data)``).

    Yields one :class:`ReverseTlvField` per ``(identifier, length, value)``
    triple encountered, closest-to-``end`` first. Stops — without raising —
    at whichever comes first:

    * a field whose identifier is in ``terminators``, which is itself
      appended as the final field (with empty ``data``/``positions``) so
      callers can tell "properly terminated" apart from "ran out"  by
      checking whether the last returned field's identifier is a terminator;
    * a field whose declared length overruns the remaining buffer;
    * ``max_fields`` fields; or
    * the buffer being exhausted.

    A malformed or unterminated footer is a legitimate thing for a caller
    to detect and reject — this just reports what it found and lets the
    caller decide what that means.
    """
    cursor = len(data) if end is None else end
    fields = []
    while cursor >= 2 and len(fields) < max_fields:
        length = data[cursor - 1]
        identifier = data[cursor - 2]
        cursor -= 2
        if identifier in terminators:
            fields.append(ReverseTlvField(identifier, b"", ()))
            break
        if length > cursor:
            break
        positions = tuple(cursor - 1 - index for index in range(length))
        value = bytes(data[position] for position in positions)
        fields.append(ReverseTlvField(identifier, value, positions))
        cursor -= length
    return tuple(fields)
