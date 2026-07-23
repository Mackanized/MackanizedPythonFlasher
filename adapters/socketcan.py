"""
Linux SocketCAN Hardware Adapter Implementation.
"""

import socket
import struct
from typing import Tuple
from .base_adapter import BaseAdapter
from domain.errors import AdapterDisconnectedError, AdapterError, AdapterOpenError, ConfigurationError
from logger import app_logger


class SocketCANAdapter(BaseAdapter):
    """Native Linux SocketCAN adapter interface with CAN-FD buffer sizing."""

    def __init__(self, interface: str = "can0", configured_bitrate: int = 500000):
        super().__init__()
        self.interface = interface
        self.sock: socket.socket = None
        self.configured_bitrate = configured_bitrate

    def connect(self, baudrate: int = 500000) -> bool:
        with self._bus_lock:
            if baudrate != self.configured_bitrate:
                raise ConfigurationError(
                    f"SocketCAN interface {self.interface} was declared at "
                    f"{self.configured_bitrate} bit/s, not requested {baudrate} bit/s. "
                    "Configure it with the operating system before connecting."
                )
            try:
                self.sock = socket.socket(socket.AF_CAN, socket.SOCK_RAW, socket.CAN_RAW)
                self.sock.bind((self.interface,))
                app_logger.info(f"[SocketCAN] Connected to {self.interface}.")
                return True
            except OSError as e:
                app_logger.error(f"[SocketCAN] Connection error on {self.interface}: {e}")
                raise AdapterOpenError(f"Unable to bind SocketCAN interface {self.interface}: {e}") from e

    def is_connected(self) -> bool:
        return self.sock is not None

    def disconnect(self) -> None:
        with self._bus_lock:
            if self.sock:
                try:
                    self.sock.close()
                except OSError as exc:
                    app_logger.error(f"[SocketCAN] Disconnect error: {exc}")
                self.sock = None
                app_logger.info(f"[SocketCAN] Disconnected from {self.interface}.")

    def send_frame(self, can_id: int, data: bytes) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            if not self.sock:
                raise AdapterDisconnectedError("SocketCAN interface is disconnected")
            if not 1 <= len(data) <= 8:
                raise ValueError("Classic SocketCAN frames must contain 1..8 data bytes")
            if not 0 <= can_id <= 0x1FFFFFFF:
                raise ValueError("CAN identifier is outside the 29-bit range")
            try:
                can_pkt = struct.pack("=IB3x8s", can_id, len(data), data.ljust(8, b'\x00'))
                self.sock.send(can_pkt)
                self._record_tx(len(data))
                return True
            except OSError as e:
                raise AdapterError(f"SocketCAN send failed: {e}", retry_safe=False) from e

    def read_frame(self, timeout_ms: int = 1000) -> Tuple[int, bytes]:
        with self._bus_lock:
            self._assert_channel_access()
            if not self.sock:
                raise AdapterDisconnectedError("SocketCAN interface is disconnected")

            self.sock.settimeout(timeout_ms / 1000.0)
            try:
                can_pkt = self.sock.recv(72)
                if len(can_pkt) == 16:
                    can_id, length, data = struct.unpack("=IB3x8s", can_pkt[:16])
                    if length > 8:
                        raise AdapterError(f"SocketCAN returned invalid classic-CAN DLC {length}")
                    can_id &= 0x1FFFFFFF
                    payload = data[:length]
                    self._record_rx(len(payload))
                    return can_id, payload
                raise AdapterError(f"SocketCAN returned malformed frame length {len(can_pkt)}")
            except socket.timeout:
                return 0, b""
            except OSError as e:
                raise AdapterError(f"SocketCAN read failed: {e}", retry_safe=False) from e
