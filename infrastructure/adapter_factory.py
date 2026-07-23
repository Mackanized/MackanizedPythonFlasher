"""Concrete adapter composition owned by infrastructure."""

from adapters.base_adapter import BaseAdapter
from adapters.j2534 import J2534Adapter
from adapters.kvaser import KvaserAdapter
from adapters.mock_adapter import MockAdapter


class DefaultAdapterFactory:
    def create(self, adapter_key: str, dll_path: str = "") -> BaseAdapter:
        key = adapter_key.casefold().strip()
        if key == "mock":
            return MockAdapter()
        if key == "kvaser":
            return KvaserAdapter()
        if key == "j2534":
            return J2534Adapter(dll_path=dll_path)
        raise ValueError(f"Unsupported adapter: {adapter_key}")
