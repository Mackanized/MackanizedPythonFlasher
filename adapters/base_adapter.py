from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from threading import RLock
import time
from typing import Tuple


@dataclass(frozen=True)
class AdapterStatistics:
    tx_frames: int
    rx_frames: int
    tx_bytes: int
    rx_bytes: int
    sampled_at: float
    nominal_bitrate: int


class BaseAdapter(ABC):
    """Abstract class for CAN interfaces (J2534, Kvaser, ELM327)."""

    def __init__(self) -> None:
        self._bus_lock = RLock()
        self._nominal_bitrate = 500000
        self._tx_frames = 0
        self._rx_frames = 0
        self._tx_bytes = 0
        self._rx_bytes = 0
        self._channel_leased = False

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def send_frame(self, can_id: int, data: bytes) -> bool:
        pass

    @abstractmethod
    def read_frame(self, timeout_ms: int = 1000) -> Tuple[int, bytes]:
        pass

    def flush_rx_buffer(self) -> None:
        """Clear the receive buffer. Override if the adapter supports this."""
        pass

    def check_bus_status(self):
        """Check physical bus status. Override if the adapter supports this."""
        pass

    @property
    def is_simulation(self) -> bool:
        return False

    @property
    def is_replay(self) -> bool:
        return False

    @property
    def supply_voltage(self):
        return None

    @contextmanager
    def exclusive_channel(self):
        with self._bus_lock:
            if self._channel_leased:
                raise RuntimeError("Adapter channel is already leased by another operation")
            self._channel_leased = True
        try:
            yield self
        finally:
            with self._bus_lock:
                self._channel_leased = False

    def is_connected(self) -> bool:
        return bool(self.check_bus_status())

    def _set_nominal_bitrate(self, baudrate: int) -> None:
        self._nominal_bitrate = int(baudrate)

    def _record_tx(self, byte_count: int) -> None:
        self._tx_frames += 1
        self._tx_bytes += int(byte_count)

    def _record_rx(self, byte_count: int) -> None:
        self._rx_frames += 1
        self._rx_bytes += int(byte_count)

    def statistics(self) -> AdapterStatistics:
        return AdapterStatistics(
            tx_frames=self._tx_frames,
            rx_frames=self._rx_frames,
            tx_bytes=self._tx_bytes,
            rx_bytes=self._rx_bytes,
            sampled_at=time.monotonic(),
            nominal_bitrate=self._nominal_bitrate,
        )

    def _assert_channel_access(self) -> None:
        return None

    def _require_connected(self) -> None:
        if not self.is_connected():
            raise RuntimeError("Adapter is not connected")
