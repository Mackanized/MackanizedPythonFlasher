"""Trionic protocol primitives.

These codecs are intentionally separate from executable hardware clients.
They are used by the hardware-enabled Trionic clients and can be validated
against replay traces and semantic mocks before bench flashing.
"""

from .codecs import KwpCanCodec, T5CommandCodec, Trionic8Codec
from .t5_client import Trionic5Client
from .t7_client import Trionic7Client
from .t8_client import Trionic8Client

__all__ = [
    "KwpCanCodec", "T5CommandCodec", "Trionic8Codec",
    "Trionic5Client", "Trionic7Client", "Trionic8Client",
]
