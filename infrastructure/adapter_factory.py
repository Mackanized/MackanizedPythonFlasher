"""Concrete adapter composition owned by infrastructure."""

import sys
from adapters.base_adapter import BaseAdapter
from adapters.j2534 import J2534Adapter
from adapters.kvaser import KvaserAdapter
from adapters.mock_adapter import MockAdapter
from adapters.stn import STNAdapter
from adapters.socketcan import SocketCANAdapter
from adapters.replay import ReplayAdapter, ReplayTrace, TraceFrame


class DefaultAdapterFactory:
    def create(
        self,
        adapter_key: str,
        dll_path: str = "",
        port: str = "",
        interface: str = "",
    ) -> BaseAdapter:
        key = adapter_key.casefold().strip()
        if key in ("mock", "simulator"):
            return MockAdapter()
        if key == "kvaser":
            return KvaserAdapter()
        if key == "j2534":
            return J2534Adapter(dll_path=dll_path)
        if key in ("stn", "elm327", "obdlink"):
            default_port = port or ("COM3" if sys.platform == "win32" else "/dev/ttyUSB0")
            return STNAdapter(port=default_port)
        if key == "socketcan":
            return SocketCANAdapter(interface=interface or "can0")
        if key == "replay":
            trace = ReplayTrace(
                name="synthetic_replay",
                ecu="Generic",
                evidence="synthetic-test",
                source_reference="Automated test suite",
                frames=(
                    TraceFrame("tx", 0x7E0, b"\x02\x10\x01\x00\x00\x00\x00\x00", "Start session"),
                    TraceFrame("rx", 0x7E8, b"\x06\x50\x01\x00\x32\x01\xF4\x00", "Positive response"),
                ),
            )
            return ReplayAdapter(trace)
        raise ValueError(f"Unsupported adapter: {adapter_key}")

