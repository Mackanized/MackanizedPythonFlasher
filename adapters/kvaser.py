from typing import List, Optional, Tuple

try:
    from canlib import canlib, Frame
    HAS_KVASER = True
except ImportError:
    canlib = None
    Frame = None
    HAS_KVASER = False
from .base_adapter import BaseAdapter
from domain.errors import ConfigurationError

class KvaserAdapter(BaseAdapter):
    """Native Kvaser CANlib adapter interface with software-side diagnostic ID filtering."""

    DIAG_IDS = {0x101, 0x7E0, 0x7E1, 0x7E2, 0x7E3, 0x7E4, 0x7E5, 0x7E6, 0x7E7, 0x7E8, 0x7E9, 0x7EA, 0x7EB, 0x7EC, 0x7ED, 0x7EE, 0x7EF}

    def __init__(self, channel: int = 0):
        super().__init__()
        self.channel_num = channel
        self.channel = None

    def connect(self, baudrate: int = 500000) -> bool:
        if not HAS_KVASER:
            raise ConfigurationError(
                "The Kvaser canlib SDK/package is not installed. "
                "Install it with `pip install canlib` and the Kvaser driver package."
            )
        # Every fixed bitrate canlib's Bitrate enum exposes. 33333 (GMLAN
        # single-wire low-speed) has no canlib preset, so it is intentionally
        # absent here rather than silently connecting at the wrong speed.
        bitrate_map = {
            1000000: canlib.Bitrate.BITRATE_1M,
            500000: canlib.Bitrate.BITRATE_500K,
            250000: canlib.Bitrate.BITRATE_250K,
            125000: canlib.Bitrate.BITRATE_125K,
            100000: canlib.Bitrate.BITRATE_100K,
            83333: canlib.Bitrate.BITRATE_83K,
            62000: canlib.Bitrate.BITRATE_62K,
            50000: canlib.Bitrate.BITRATE_50K,
            10000: canlib.Bitrate.BITRATE_10K,
        }
        if baudrate not in bitrate_map:
            raise ConfigurationError(
                f"Kvaser canlib has no fixed bitrate preset for {baudrate} bps "
                f"(supported: {', '.join(str(b) for b in sorted(bitrate_map))}). "
                "GMLAN single-wire 33.3 kbps requires a different adapter (e.g. STN/OBDLink)."
            )
        try:
            self.channel = canlib.openChannel(self.channel_num, canlib.Open.ACCEPT_VIRTUAL)
            self.channel.setBusParams(bitrate_map[baudrate])
            self.channel.busOn()
            print(f"[Kvaser] Connected on Channel {self.channel_num} at {baudrate} bps.")
            return True
        except canlib.CanError as e:
            print(f"[Kvaser] Connection error: {e}")
            return False

    def disconnect(self) -> None:
        if self.channel:
            try:
                self.channel.busOff()
                self.channel.close()
                print("[Kvaser] Disconnected.")
            except canlib.CanError as e:
                print(f"[Kvaser] Disconnect error: {e}")
            finally:
                self.channel = None

    def flush_rx_buffer(self) -> None:
        if not self.channel:
            return
        try:
            while True:
                self.channel.read(timeout=0)
        except Exception:
            pass

    def send_frame(self, can_id: int, data: bytes) -> bool:
        if not self.channel:
            return False
        import time
        frame = Frame(id_=can_id, data=list(data))
        for _ in range(20):
            try:
                self.channel.write(frame)
                return True
            except canlib.CanError as e:
                # Error code -13 / TXBUFOFL indicates transmit buffer overflow
                if getattr(e, 'status', None) == canlib.ErrorNumber.TXBUFOFL or e.args[0] == -13:
                    time.sleep(0.001)
                    continue
                print(f"[Kvaser] TX error: {e}")
                return False
        return False

    def read_frame(self, timeout_ms: int = 1000) -> Tuple[int, bytes]:
        if not self.channel:
            return 0, b""
        
        import time
        deadline = time.time() + (timeout_ms / 1000.0)
        
        try:
            while True:
                remaining_ms = int((deadline - time.time()) * 1000)
                if remaining_ms <= 0:
                    return 0, b""
                
                frame = self.channel.read(timeout=max(1, remaining_ms))
                if frame.id in KvaserAdapter.DIAG_IDS:
                    return frame.id, bytes(frame.data)
        except canlib.CanNoMsg:
            return 0, b""
        except canlib.CanError:
            return 0, b""

    def check_bus_status(self):
        """Inspects Kvaser hardware bus flags for physical layer errors."""
        if not self.channel:
            return False
        status = self.channel.readStatus()
        print(f"\n[Hardware Status Flags]: {status}")
        if status & canlib.Stat.BUS_OFF:
            print("  [WARN] BUS-OFF: Critical physical error! Check 120 Ω resistor or CAN-H/CAN-L wiring.")
        elif status & canlib.Stat.ERROR_PASSIVE:
            print("  [WARN] BUS-PASSIVE: Transceiver not receiving ACK bits from ECU.")
        elif status & canlib.Stat.ERROR_WARNING:
            print("  [WARN] BUS-WARNING: High frame error count detected.")
        else:
            print("  [OK] Physical bus state is NORMAL.")
        return True