import ctypes
import platform
from pathlib import Path
try:
    import winreg
except ImportError:
    winreg = None  # Non-Windows platform fallback
from typing import List, Dict, Optional, Tuple

from .base_adapter import BaseAdapter
from domain.errors import AdapterError, AdapterOpenError, ConfigurationError
from logger import app_logger

RX_STATUS_TX_MSG_TYPE = 0x01
PROTOCOL_CAN = 5  # J2534 Protocol ID for raw CAN (Kvaser uses 5; some drivers use 6)
PASS_FILTER = 1
CONNECT_FLAG_NONE = 0
TX_FLAG_NONE = 0
TX_FLAG_29BIT_ID = 0x00000001


def get_pe_architecture(dll_path: str):
    """Analyze a DLL file header to determine if it is 32-bit (x86) or 64-bit (x64)."""
    try:
        with open(dll_path, "rb") as handle:
            header = handle.read(4096)
            if header[:2] != b"MZ":
                return "unknown"
            pe_offset = int.from_bytes(header[0x3C:0x40], "little")
            machine = int.from_bytes(header[pe_offset + 4:pe_offset + 6], "little")
            if machine == 0x014C:
                return 32
            elif machine == 0x8664:
                return 64
    except Exception:
        pass
    return "unknown"


STATUS_NOERROR = 0x00
ERR_NOT_SUPPORTED = 0x16  # Code 22
ERR_TIMEOUT = 0x18         # Code 24
ERR_BUFFER_EMPTY = 0x28    # Code 40
ERR_INVALID_MSG = 0x77     # Code 119
ERR_BUFFER_FULL = 0x0B     # Code 11
ERR_FAILED = 0x10          # Code 16
ERR_INVALID_IOCTL = 0x17   # Code 23

IOCTL_CLEAR_RX_BUFFER = 5
IOCTL_CLEAR_TX_BUFFER = 6
IOCTL_SET_CONFIG = 3

# CONFIG structure for IOCTL_SET_CONFIG
class SCONFIG(ctypes.Structure):
    _fields_ = [
        ("Parameter", ctypes.c_ulong),
        ("Value", ctypes.c_ulong),
    ]

class SCONFIG_LIST(ctypes.Structure):
    _fields_ = [
        ("NumOfParams", ctypes.c_ulong),
        ("ConfigPtr", ctypes.POINTER(SCONFIG)),
    ]

# J2534 Config Parameter IDs
CONFIG_PINS = 0x04
CONFIG_LOOPBACK = 0x05
CONFIG_FILTER = 0x08

# ── PASSTHRU_MSG structure ───────────────────────────────────────────
class PASSTHRU_MSG(ctypes.Structure):
    _fields_ = [
        ("ProtocolID", ctypes.c_ulong),
        ("RxStatus", ctypes.c_ulong),
        ("TxFlags", ctypes.c_ulong),
        ("Timestamp", ctypes.c_ulong),
        ("DataSize", ctypes.c_ulong),
        ("ExtraDataIndex", ctypes.c_ulong),
        ("Data", ctypes.c_ubyte * 4128)
    ]


# ── Device discovery ─────────────────────────────────────────────────
def get_installed_j2534_devices(registry_module=None) -> List[Dict[str, str]]:
    """Return registered J2534 devices, or an empty list off Windows."""
    reg = winreg if registry_module is None else registry_module
    if reg is None:
        return []

    devices = []
    seen_dlls = set()
    process_bits = ctypes.sizeof(ctypes.c_void_p) * 8
    reg_paths = [
        r"SOFTWARE\PassThruSupport.04.04",
        r"SOFTWARE\WOW6432Node\PassThruSupport.04.04",
    ]

    for reg_path in reg_paths:
        try:
            key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, reg_path)
        except (FileNotFoundError, OSError):
            continue

        try:
            num_subkeys = reg.QueryInfoKey(key)[0]
            for i in range(num_subkeys):
                device_key_name = reg.EnumKey(key, i)
                try:
                    device_key = reg.OpenKey(key, device_key_name)
                except (FileNotFoundError, OSError):
                    continue
                try:
                    name, _ = reg.QueryValueEx(device_key, "Name")
                    dll_path, _ = reg.QueryValueEx(device_key, "FunctionLibrary")
                    normalized = str(dll_path).lower()
                    if normalized in seen_dlls:
                        continue
                    if not Path(dll_path).is_file():
                        continue
                    architecture = get_pe_architecture(dll_path)
                    if architecture != "unknown" and architecture != process_bits:
                        continue
                    seen_dlls.add(normalized)
                    devices.append({
                        "name": name,
                        "dll": dll_path,
                        "architecture": str(architecture),
                    })
                except (FileNotFoundError, OSError):
                    continue
                finally:
                    reg.CloseKey(device_key)
        finally:
            reg.CloseKey(key)
    return devices


class J2534Adapter(BaseAdapter):
    """J2534 PassThru adapter with software-side diagnostic ID filtering."""

    DIAG_IDS = {0x101, 0x7E0, 0x7E1, 0x7E2, 0x7E3, 0x7E4, 0x7E5,
                0x7E6, 0x7E7, 0x7E8, 0x7E9, 0x7EA, 0x7EB, 0x7EC,
                0x7ED, 0x7EE, 0x7EF}

    def __init__(self, dll_path: Optional[str] = None, channel: int = 0):
        super().__init__()
        self.dll_path = dll_path
        self.dll = None
        self.device_id = ctypes.c_ulong(0)
        self.channel_id = ctypes.c_ulong(0)
        self.filter_id = ctypes.c_ulong(0)
        self._connected = False
        self._protocol_id = PROTOCOL_CAN
        self._last_tx_frame: Optional[Tuple[int, bytes]] = None

    def load_dll(self, dll_path: str) -> bool:
        architecture = get_pe_architecture(dll_path)
        process_bits = ctypes.sizeof(ctypes.c_void_p) * 8
        if architecture != "unknown" and architecture != process_bits:
            raise ConfigurationError(
                f"J2534 DLL architecture {architecture}-bit does not match the current Python process ({process_bits}-bit)."
            )
        try:
            self.dll = ctypes.WinDLL(dll_path)
            self._setup_prototypes()
            self.dll_path = dll_path
            return True
        except Exception as e:
            print(f"[J2534] Error loading DLL ({dll_path}): {e}")
            return False

    def _setup_prototypes(self):
        self.dll.PassThruOpen.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        self.dll.PassThruOpen.restype = ctypes.c_long
        self.dll.PassThruClose.argtypes = [ctypes.c_ulong]
        self.dll.PassThruClose.restype = ctypes.c_long
        self.dll.PassThruConnect.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
        self.dll.PassThruConnect.restype = ctypes.c_long
        self.dll.PassThruDisconnect.argtypes = [ctypes.c_ulong]
        self.dll.PassThruDisconnect.restype = ctypes.c_long
        self.dll.PassThruReadMsgs.restype = ctypes.c_long
        self.dll.PassThruWriteMsgs.restype = ctypes.c_long
        self.dll.PassThruStartMsgFilter.restype = ctypes.c_long
        self.dll.PassThruIoctl.argtypes = [ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p]
        self.dll.PassThruIoctl.restype = ctypes.c_long

    def connect(self, baudrate: int = 500000) -> bool:
        if not self.dll_path:
            devices = get_installed_j2534_devices()
            if not devices:
                print("[J2534] Error: No installed PassThru devices found in registry.")
                return False
            self.dll_path = devices[0]["dll"]
            print(f"[J2534] Selected Driver: {devices[0]['name']}")

        if not self.dll and not self.load_dll(self.dll_path):
            return False

        res = self.dll.PassThruOpen(None, ctypes.byref(self.device_id))
        if res != STATUS_NOERROR:
            print(f"[J2534] PassThruOpen failed: {res}")
            return False

        res = self.dll.PassThruConnect(
            self.device_id, PROTOCOL_CAN, CONNECT_FLAG_NONE,
            baudrate, ctypes.byref(self.channel_id)
        )
        used_protocol = PROTOCOL_CAN
        if res != STATUS_NOERROR:
            print(f"[J2534] PassThruConnect failed: {res} (0x{res:02X})")
            self.dll.PassThruClose(self.device_id)
            raise AdapterOpenError("J2534 raw CAN PassThruConnect failed", vendor_code=res)
        app_logger.debug(f"[J2534] Connected with protocol={used_protocol}, channel={self.channel_id.value}")
        self._protocol_id = used_protocol

        # Set CAN pin voltage to normal (pin 6/14) via IOCTL_SET_CONFIG
        # Note: Some drivers (e.g. Kvaser) don't support this and return error; safe to ignore
        config = SCONFIG()
        config.Parameter = CONFIG_PINS
        config.Value = 0x0001  # J1962 pins 6 and 14 (CAN-H/CAN-L)
        config_list = SCONFIG_LIST()
        config_list.NumOfParams = 1
        config_list.ConfigPtr = ctypes.pointer(config)
        res = self.dll.PassThruIoctl(
            self.channel_id, IOCTL_SET_CONFIG,
            ctypes.byref(config_list), None
        )
        if res != STATUS_NOERROR:
            app_logger.debug(f"[J2534] IOCTL_SET_CONFIG (pins) failed: {res} (0x{res:02X}) — ignoring")

        if not self._setup_pass_all_filter():
            self.disconnect()
            return False

        # Clear RX buffer after filter setup
        self.dll.PassThruIoctl(self.channel_id, IOCTL_CLEAR_RX_BUFFER, None, None)

        self._connected = True
        print(f"[J2534] Connected successfully at {baudrate} bps.")
        return True

    def _setup_pass_all_filter(self) -> bool:
        # Pass-all filter. Some J2534 drivers require both mask and pattern to
        # be zero for raw CAN reception.
        mask_msg = PASSTHRU_MSG()
        ctypes.memset(ctypes.byref(mask_msg), 0, ctypes.sizeof(mask_msg))
        mask_msg.ProtocolID = self._protocol_id
        mask_msg.DataSize = 4
        mask_msg.Data[0] = 0x00
        mask_msg.Data[1] = 0x00
        mask_msg.Data[2] = 0x00
        mask_msg.Data[3] = 0x00

        pattern_msg = PASSTHRU_MSG()
        ctypes.memset(ctypes.byref(pattern_msg), 0, ctypes.sizeof(pattern_msg))
        pattern_msg.ProtocolID = self._protocol_id
        pattern_msg.DataSize = 4
        pattern_msg.Data[0] = 0x00
        pattern_msg.Data[1] = 0x00
        pattern_msg.Data[2] = 0x00
        pattern_msg.Data[3] = 0x00

        res = self.dll.PassThruStartMsgFilter(
            self.channel_id, PASS_FILTER,
            ctypes.byref(mask_msg), ctypes.byref(pattern_msg),
            None, ctypes.byref(self.filter_id)
        )
        app_logger.debug(f"[J2534] PassThruStartMsgFilter: res={res} (0x{res:02X}), filter_id={self.filter_id.value}")

        if res not in (STATUS_NOERROR, ERR_NOT_SUPPORTED):
            print(f"[J2534] Filter setup failed with status code: {res} (0x{res:02X})")
            self.disconnect()
            return False
        if res == ERR_NOT_SUPPORTED:
            app_logger.debug("[J2534] Pass-all filter not supported, continuing without filter.")

        return True

    def disconnect(self) -> None:
        if self.channel_id.value:
            self.dll.PassThruDisconnect(self.channel_id)
            self.channel_id = ctypes.c_ulong(0)
        if self.device_id.value:
            self.dll.PassThruClose(self.device_id)
            self.device_id = ctypes.c_ulong(0)
        self._connected = False
        print("[J2534] Disconnected.")

    def flush_rx_buffer(self) -> None:
        if self._connected and self.dll:
            self.dll.PassThruIoctl(self.channel_id, IOCTL_CLEAR_RX_BUFFER, None, None)

    def check_bus_status(self):
        """J2534 does not expose hardware bus status flags like Kvaser."""
        print("  [OK] J2534 bus status not available (handled by PassThru driver).")
        return self._connected

    def read_battery_voltage(self):
        if not self._connected or not self.dll:
            return None
        return None

    def send_frame(self, can_id: int, data: bytes) -> bool:
        if not self._connected:
            return False
        if len(data) > 8:
            return False

        msg = PASSTHRU_MSG()
        ctypes.memset(ctypes.byref(msg), 0, ctypes.sizeof(msg))
        msg.ProtocolID = self._protocol_id
        msg.RxStatus = 0
        msg.TxFlags = TX_FLAG_NONE
        msg.Timestamp = 0
        msg.ExtraDataIndex = 0
        msg.DataSize = 4 + len(data)
        # CAN ID in big-endian (4 bytes)
        msg.Data[0] = (can_id >> 24) & 0xFF
        msg.Data[1] = (can_id >> 16) & 0xFF
        msg.Data[2] = (can_id >> 8) & 0xFF
        msg.Data[3] = can_id & 0xFF
        for i, b in enumerate(data):
            msg.Data[4 + i] = b

        num_msgs = ctypes.c_ulong(1)
        res = self.dll.PassThruWriteMsgs(
            self.channel_id, ctypes.byref(msg),
            ctypes.byref(num_msgs), 1000
        )
        if res == STATUS_NOERROR:
            self._last_tx_frame = (can_id, bytes(data))
            self._record_tx(len(data))
            return True
        if res == ERR_TIMEOUT and can_id == 0x101:
            app_logger.debug(f"[J2534] Functional TX on 0x{can_id:03X} returned ERR_TIMEOUT (expected for broadcast)")
            self._last_tx_frame = (can_id, bytes(data))
            self._record_tx(len(data))
            return True
        app_logger.debug(f"[J2534] send_frame FAILED: can_id=0x{can_id:03X}, res=0x{res:02X}, data={data.hex()}")
        return False

    def read_frame(self, timeout_ms: int = 1000) -> Tuple[int, bytes]:
        if not self._connected:
            return 0, b""

        msg = PASSTHRU_MSG()
        ctypes.memset(ctypes.byref(msg), 0, ctypes.sizeof(msg))
        msg.ProtocolID = self._protocol_id
        num_msgs = ctypes.c_ulong(1)
        if not hasattr(self, '_read_debug_done'):
            self._read_debug_done = True
            app_logger.debug(f"[J2534] read_frame first call: proto={self._protocol_id}, ch={self.channel_id.value}, msg_size={ctypes.sizeof(msg)}, timeout={timeout_ms}")
        res = self.dll.PassThruReadMsgs(
            self.channel_id, ctypes.byref(msg),
            ctypes.byref(num_msgs), timeout_ms
        )

        if res == STATUS_NOERROR and num_msgs.value > 0:
            # CAN ID from first 4 bytes (big-endian)
            rx_can_id = (
                (msg.Data[0] << 24) |
                (msg.Data[1] << 16) |
                (msg.Data[2] << 8) |
                msg.Data[3]
            )
            payload_len = msg.DataSize - 4
            if payload_len <= 0:
                return 0, b""
            payload = bytes(msg.Data[4:4 + payload_len])

            if msg.RxStatus & RX_STATUS_TX_MSG_TYPE:
                app_logger.debug("[J2534] Discarded PassThru TX echo frame.")
                return 0, b""
            if msg.RxStatus & 0x20:
                if self._last_tx_frame == (rx_can_id, payload):
                    app_logger.debug("[J2534] Discarded vendor-marked exact TX echo frame.")
                    return 0, b""
                raise AdapterError("J2534 RX error indication", vendor_code=msg.RxStatus)

            # Filter to diagnostic IDs only (matching Kvaser behavior)
            if rx_can_id in self.DIAG_IDS:
                self._record_rx(len(payload))
                return rx_can_id, payload

            return 0, b""

        if res not in (STATUS_NOERROR, ERR_BUFFER_EMPTY, ERR_TIMEOUT):
            app_logger.debug(f"[J2534] read_frame: res=0x{res:02X}, num_msgs={num_msgs.value}")

        if res not in (STATUS_NOERROR, ERR_BUFFER_EMPTY, ERR_TIMEOUT, ERR_FAILED):
            app_logger.debug(f"[J2534] read_frame: unexpected error res=0x{res:02X}")

        return 0, b""
