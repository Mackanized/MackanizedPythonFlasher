from abc import ABC, abstractmethod
from typing import Tuple

class BaseAdapter(ABC):
    """Abstract class for CAN interfaces (J2534, Kvaser, ELM327)."""

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
