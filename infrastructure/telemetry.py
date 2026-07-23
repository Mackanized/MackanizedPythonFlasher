"""Measured process and adapter telemetry; unavailable values remain unknown."""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, Signal

from adapters.base_adapter import BaseAdapter
from logger import app_logger

try:
    import resource
except ImportError:  # Windows does not provide the POSIX resource module.
    resource = None


class TelemetryEngine(QObject):
    telemetry_updated = Signal(dict)

    def __init__(
        self,
        parent=None,
        adapter_provider: Optional[Callable[[], Optional[BaseAdapter]]] = None,
    ):
        super().__init__(parent)
        self._adapter_provider = adapter_provider or (lambda: None)
        self._is_running = False
        self._thread: Optional[threading.Thread] = None
        self.telemetry_listeners: list[Callable[[Dict[str, Any]], None]] = []
        self._transfer_rate = 0.0
        self._active_transfer = False
        self._voltage_override: Optional[float] = None
        self._last_wall = time.monotonic()
        self._last_cpu = time.process_time()
        self._last_adapter_sample = None
        self._latest_payload: Dict[str, Any] = self._unknown_payload()

    @staticmethod
    def _unknown_payload() -> Dict[str, Any]:
        return {
            "voltage": None,
            "voltage_status": "unknown",
            "can_fps": None,
            "can_bus_load": None,
            "cpu_usage_pct": None,
            "memory_usage_mb": None,
            "tx_fps": None,
            "rx_fps": None,
            "is_simulation": False,
            "source": "unavailable",
        }

    def set_adapter_provider(self, provider: Callable[[], Optional[BaseAdapter]]) -> None:
        self._adapter_provider = provider
        self._last_adapter_sample = None

    def set_voltage_override(self, voltage: Optional[float]) -> None:
        self._voltage_override = voltage

    def get_snapshot(self) -> Dict[str, Any]:
        return dict(self._latest_payload)

    def add_listener(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        if callback not in self.telemetry_listeners:
            self.telemetry_listeners.append(callback)

    def start_monitoring(self) -> None:
        if not self._is_running:
            self._is_running = True
            self._thread = threading.Thread(target=self._loop, daemon=True, name="telemetry")
            self._thread.start()

    def stop_monitoring(self) -> None:
        self._is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None

    def set_transfer_active(self, active: bool, rate_kbs: float = 0.0) -> None:
        self._active_transfer = active
        self._transfer_rate = rate_kbs if active else 0.0

    def _loop(self) -> None:
        while self._is_running:
            self._sample_telemetry()
            time.sleep(0.5)

    def _sample_telemetry(self) -> None:
        now = time.monotonic()
        wall_delta = max(now - self._last_wall, 1e-9)
        process_cpu = time.process_time()
        cpu_usage = max(0.0, (process_cpu - self._last_cpu) / wall_delta * 100.0 / max(1, os.cpu_count() or 1))
        self._last_wall, self._last_cpu = now, process_cpu

        memory_mb = None
        if resource is not None:
            usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            memory_mb = usage / (1024 * 1024) if os.sys.platform == "darwin" else usage / 1024

        voltage = round(self._voltage_override, 2) if self._voltage_override is not None else None
        voltage_status = "unknown" if voltage is None else ("critical" if voltage < 11.4 else "warning" if voltage < 12.4 else "normal")

        adapter = self._adapter_provider()
        tx_fps = rx_fps = can_fps = bus_load = None
        is_simulation = bool(adapter and adapter.is_simulation)
        source = "host-process"
        if adapter is not None:
            current = adapter.statistics()
            previous = self._last_adapter_sample
            if previous is not None:
                sample_delta = max(current.sampled_at - previous.sampled_at, 1e-9)
                tx_delta = max(0, current.tx_frames - previous.tx_frames)
                rx_delta = max(0, current.rx_frames - previous.rx_frames)
                byte_delta = max(0, current.tx_bytes + current.rx_bytes - previous.tx_bytes - previous.rx_bytes)
                tx_fps = round(tx_delta / sample_delta, 1)
                rx_fps = round(rx_delta / sample_delta, 1)
                can_fps = round(tx_fps + rx_fps, 1)
                frame_delta = tx_delta + rx_delta
                estimated_bits = byte_delta * 8 + frame_delta * 47
                bus_load = round(min(100.0, estimated_bits / sample_delta / current.nominal_bitrate * 100), 2)
            self._last_adapter_sample = current
            source = "adapter-counters+host-process"

        payload: Dict[str, Any] = {
            "voltage": voltage,
            "voltage_status": voltage_status,
            "transfer_rate_kbs": round(self._transfer_rate, 1),
            "can_fps": can_fps,
            "can_bus_load": bus_load,
            "cpu_usage_pct": round(cpu_usage, 2),
            "memory_usage_mb": None if memory_mb is None else round(memory_mb, 2),
            "timestamp": time.time(),
            "tx_fps": tx_fps,
            "rx_fps": rx_fps,
            "is_simulation": is_simulation,
            "source": source,
        }
        self._latest_payload = dict(payload)
        self.telemetry_updated.emit(payload)
        for callback in list(self.telemetry_listeners):
            try:
                callback(payload)
            except (RuntimeError, TypeError, ValueError) as exc:
                app_logger.warning("Telemetry listener rejected a sample: %s", exc)
