"""Bounded raw-CAN helpers shared by the Trionic physical candidates."""

from __future__ import annotations

from typing import Optional, Tuple

from adapters.base_adapter import BaseAdapter
from domain.cancellation import CancellationToken
from domain.clock import Clock
from domain.errors import OperationCancelled, TransportError


class BoundedCanTransport:
    """Small classic-CAN transaction helper with one absolute deadline."""

    def __init__(self, adapter: BaseAdapter, cancel: CancellationToken, clock: Clock) -> None:
        self.adapter = adapter
        self.cancel = cancel
        self.clock = clock

    def require_connection(self) -> None:
        if not self.adapter.is_connected():
            raise TransportError("Trionic operation requires a connected adapter")

    def send(self, can_id: int, data: bytes) -> None:
        self.require_connection()
        if self.cancel.should_interrupt:
            raise OperationCancelled("Trionic operation cancelled before CAN transmit")
        if not self.adapter.send_frame(can_id, bytes(data)):
            raise TransportError(f"CAN transmit on 0x{can_id:03X} failed")

    def receive(self, can_id: int, timeout_s: float) -> bytes:
        self.require_connection()
        deadline = self.clock.monotonic() + timeout_s
        while self.clock.monotonic() < deadline:
            if self.cancel.should_interrupt:
                raise OperationCancelled("Trionic operation cancelled while awaiting CAN response")
            remaining = deadline - self.clock.monotonic()
            rx_id, data = self.adapter.read_frame(
                timeout_ms=max(1, min(100, int(remaining * 1000)))
            )
            if rx_id == can_id and data:
                return bytes(data)
        raise TimeoutError(f"No response from CAN ID 0x{can_id:03X} within {timeout_s:.3f}s")

    def exchange(self, tx_id: int, data: bytes, rx_id: int, timeout_s: float) -> bytes:
        self.send(tx_id, data)
        return self.receive(rx_id, timeout_s)

    def receive_optional(self, can_id: int, timeout_s: float) -> Optional[bytes]:
        try:
            return self.receive(can_id, timeout_s)
        except TimeoutError:
            return None
