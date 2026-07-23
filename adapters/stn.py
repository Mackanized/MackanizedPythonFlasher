"""
STN11xx / STN22xx / OBDLink MX+ Hardware Adapter Implementation.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

from adapters.base_adapter import BaseAdapter
from domain.errors import (
    AdapterDisconnectedError,
    AdapterError,
    AdapterOpenError,
    ConfigurationError,
)
from logger import app_logger

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    serial = None
    HAS_SERIAL = False


class STNAdapter(BaseAdapter):
    """Native STN11xx / STN22xx / OBDLink MX+ CAN adapter interface."""

    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        initial_baud: int = 115200,
        target_baud: int = 2000000,
    ):
        super().__init__()
        self.port = port
        self.initial_baud = initial_baud
        self.target_baud = target_baud
        self._serial: Optional[serial.Serial] = None
        self._connected = False

    def connect(self, baudrate: int = 500000) -> bool:
        if not HAS_SERIAL:
            raise ConfigurationError(
                "pyserial is required for STN11xx/OBDLink hardware support. "
                "Install with `pip install pyserial`."
            )

        with self._bus_lock:
            try:
                self._serial = serial.Serial(self.port, self.initial_baud, timeout=0.5)
                self._send_command("AT Z", wait_ms=500)
                self._send_command("ATE0")  # Echo off
                self._send_command("ATL0")  # Linefeeds off
                self._send_command("ATH1")  # Headers on
                self._send_command("ATS0")  # Spaces off

                # Try high-speed baudrate negotiation if target_baud != initial_baud
                if self.target_baud != self.initial_baud:
                    try:
                        self._send_command(f"STPBR {self.target_baud}")
                        self._serial.baudrate = self.target_baud
                        time.sleep(0.1)
                        resp = self._send_command("ATI")
                        if "STN" in resp or "OBDLink" in resp or "ELM" in resp:
                            app_logger.info(
                                f"[STN] Switched port {self.port} to high-speed {self.target_baud} baud."
                            )
                    except Exception as e:
                        app_logger.warning(f"[STN] High-speed baud rate switch failed, using {self.initial_baud}: {e}")

                # Configure CAN protocol mode (STP 6 = CAN 11/500k, STP 33 = GMLAN SW-CAN)
                if baudrate == 33333:
                    self._send_command("STP 33")  # GMLAN SW-CAN
                else:
                    self._send_command("STP 6")   # ISO 15765-4 CAN 11/500k

                self._connected = True
                app_logger.info(f"[STN] Connected to {self.port} at {baudrate} CAN baud.")
                return True
            except (serial.SerialException, OSError) as e:
                app_logger.error(f"[STN] Connection error on {self.port}: {e}")
                self.disconnect()
                raise AdapterOpenError(f"Unable to open STN adapter port {self.port}: {e}") from e

    def is_connected(self) -> bool:
        return self._connected and self._serial is not None and self._serial.is_open

    def disconnect(self) -> None:
        with self._bus_lock:
            if self._serial:
                try:
                    self._send_command("AT Z")
                    self._serial.close()
                except Exception as exc:
                    app_logger.error(f"[STN] Disconnect error: {exc}")
                self._serial = None
            self._connected = False
            app_logger.info(f"[STN] Disconnected from {self.port}.")

    def send_frame(self, can_id: int, data: bytes) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            if not self.is_connected():
                raise AdapterDisconnectedError("STN adapter is disconnected")

            try:
                header_cmd = f"AT SH {can_id:03X}" if can_id <= 0x7FF else f"AT CP {can_id:08X}"
                self._send_command(header_cmd)

                payload_hex = data.hex().upper()
                resp = self._send_command(payload_hex)
                self._record_tx(len(data))
                return "OK" in resp or "7E" in resp or len(resp) > 0
            except Exception as e:
                raise AdapterError(f"STN frame transmit failed: {e}", retry_safe=False) from e

    def read_frame(self, timeout_ms: int = 1000) -> Tuple[int, bytes]:
        with self._bus_lock:
            self._assert_channel_access()
            if not self.is_connected():
                raise AdapterDisconnectedError("STN adapter is disconnected")

            try:
                line = self._readline(timeout_ms / 1000.0)
                if not line:
                    return 0, b""

                # Parse frame format: "7E80641C2000000" or header + payload
                clean = line.replace(" ", "").strip()
                if len(clean) >= 6:
                    can_id = int(clean[:3], 16)
                    payload = bytes.fromhex(clean[3:])
                    self._record_rx(len(payload))
                    return can_id, payload
                return 0, b""
            except Exception:
                return 0, b""

    def _send_command(self, cmd: str, wait_ms: int = 100) -> str:
        if not self._serial:
            return ""
        self._serial.reset_input_buffer()
        self._serial.write(f"{cmd}\r".encode("ascii"))
        time.sleep(wait_ms / 1000.0)
        return self._readline(0.2)

    def _readline(self, timeout_s: float) -> str:
        if not self._serial:
            return ""
        self._serial.timeout = timeout_s
        raw = self._serial.read_until(b">")
        return raw.decode("ascii", errors="ignore").replace(">", "").strip()
