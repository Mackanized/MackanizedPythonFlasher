"""Hardware construction port used by the application service."""

from typing import Protocol

from adapters.base_adapter import BaseAdapter


class AdapterFactory(Protocol):
    def create(self, adapter_key: str, dll_path: str = "") -> BaseAdapter: ...
