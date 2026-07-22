import ctypes
import platform
import struct
import winreg
from typing import List, Dict, Optional, Tuple

from .base_adapter import BaseAdapter
from logger import app_logger

# ── J2534 Constants ──────────────────────────────────────────────────
PROTOCOL_CAN = 5  # J2534 Protocol ID for raw CAN (Kvaser uses 5; some drivers use 6)
PASS_FILTER = 1
CONNECT_FLAG_NONE = 0
TX_FLAG_NONE = 0
TX_FLAG_29BIT_ID = 0x00000001

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


# ── DLL bitness helper ────────────────────────────────────────────────
def _get_dll_bitness(path: str) -> str:
    """Return '64-bit', '32-bit', or 'unknown' by reading the PE header."""
    try:
        with open(path, 'rb') as f:
            dos = f.read(64)
            if dos[:2] != b'MZ':
                return 'unknown'
            pe_offset = struct.unpack_from('<I', dos, 60)[0]
            f.seek(pe_offset)
            pe = f.read(6)
            if pe[:4] != b'PE\x00\x00':
                return 'unknown'
            machine = struct.unpack_from('<H', pe, 4)[0]
            if machine == 0x8664:
                return '64-bit'
            if machine == 0x014C:
                return '32-bit'
            return 'unknown'
    except Exception:
        return 'unknown'


# ── Device discovery ─────────────────────────────────────────────────
def get_installed_j2534_devices() -> List[Dict[str, str]]:
    """Search both 64-bit and 32-bit registry hives for installed J2534 drivers.
    
    On 64-bit Windows, 64-bit DLLs register under SOFTWARE\\PassThruSupport.04.04
    and 32-bit DLLs under SOFTWARE\\WOW6432Node\\PassThruSupport.04.04.
    We search both unconditionally, validate each DLL exists on disk,
    and skip 32-bit DLLs when running 64-bit Python (WinError 193).
    """
    import os
    devices = []
    seen_dlls: set = set()
    is_64bit_python = platform.architecture()[0] == '64bit'

    reg_paths = [
        r"SOFTWARE\PassThruSupport.04.04",
        r"SOFTWARE\WOW6432Node\PassThruSupport.04.04",
    ]

    for reg_path in reg_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path)
            num_subkeys = winreg.QueryInfoKey(key)[0]
            for i in range(num_subkeys):
                device_key_name = winreg.EnumKey(key, i)
                device_key = winreg.OpenKey(key, device_key_name)
                try:
                    name, _ = winreg.QueryValueEx(device_key, "Name")
                    dll_path, _ = winreg.QueryValueEx(device_key, "FunctionLibrary")
                    dll_path_lower = dll_path.lower()
                    if dll_path_lower in seen_dlls:
                        continue  # avoid duplicates across hive paths
                    if not os.path.isfile(dll_path):
                        app_logger.debug(f"[J2534] DLL not found on disk, skipping: {dll_path}")
                        continue
                    # Skip 32-bit DLLs when running 64-bit Python — they cannot be loaded (WinError 193)
                    bitness = _get_dll_bitness(dll_path)
                    if is_64bit_python and bitness == '32-bit':
                        app_logger.debug(
                            f"[J2534] Skipping 32-bit DLL '{name}' ({dll_path}) — "
                            f"incompatible with 64-bit Python. Install 64-bit drivers if available."
                        )
                        print(f"  [skip] {name}: 32-bit DLL, incompatible with 64-bit Python")
                        continue
                    seen_dlls.add(dll_path_lower)
                    app_logger.debug(f"[J2534] Discovered device ({bitness}): '{name}' -> {dll_path} (from {reg_path})")
                    devices.append({"name": name, "dll": dll_path, "bitness": bitness})
                except FileNotFoundError:
                    continue
                finally:
                    winreg.CloseKey(device_key)
            winreg.CloseKey(key)
        except FileNotFoundError:
            continue

    if not devices:
        app_logger.debug("[J2534] No compatible J2534 devices found in registry.")
    return devices


class J2534Adapter(BaseAdapter):
    """J2534 PassThru adapter with software-side diagnostic ID filtering."""

    DIAG_IDS = {0x101, 0x7E0, 0x7E1, 0x7E2, 0x7E3, 0x7E4, 0x7E5,
                0x7E6, 0x7E7, 0x7E8, 0x7E9, 0x7EA, 0x7EB, 0x7EC,
                0x7ED, 0x7EE, 0x7EF}

    def __init__(self, dll_path: Optional[str] = None, channel: int = 0):
        self.dll_path = dll_path
        self.dll = None
        self.device_id = ctypes.c_ulong(0)
        self.channel_id = ctypes.c_ulong(0)
        self.filter_id = ctypes.c_ulong(0)
        self._connected = False
        self._protocol_id = PROTOCOL_CAN

    def load_dll(self, dll_path: str) -> bool:
        try:
            self.dll = ctypes.WinDLL(dll_path)
            self._setup_prototypes()
            self.dll_path = dll_path
            return True
        except OSError as e:
            if getattr(e, 'winerror', None) == 193:
                print(
                    f"[J2534] Cannot load DLL: {dll_path}\n"
                    f"  Reason: 32-bit DLL cannot be loaded by 64-bit Python (WinError 193).\n"
                    f"  Install the 64-bit version of your J2534 device drivers."
                )
            else:
                print(f"[J2534] Error loading DLL ({dll_path}): {e}")
            return False
        except Exception as e:
            print(f"[J2534] Error loading DLL ({dll_path}): {e}")
            return False

    def _setup_prototypes(self):
        self.dll.PassThruOpen.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        self.dll.PassThruOpen.restype = ctypes.c_long
        self.dll.PassThruClose.argtypes = [ctypes.c_ulong]
        self.dll.PassThruClose.restype = ctypes.c_long
        self.dll.PassThruConnect.argtypes = [
            ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong,
            ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)
        ]
        self.dll.PassThruConnect.restype = ctypes.c_long
        self.dll.PassThruDisconnect.argtypes = [ctypes.c_ulong]
        self.dll.PassThruDisconnect.restype = ctypes.c_long
        # Fix: PassThruReadMsgs and PassThruWriteMsgs previously had only restype set.
        # Missing argtypes causes silent 64-bit pointer/struct corruption on Windows x64.
        self.dll.PassThruReadMsgs.argtypes = [
            ctypes.c_ulong,                    # ChannelID
            ctypes.POINTER(PASSTHRU_MSG),      # pMsg
            ctypes.POINTER(ctypes.c_ulong),    # pNumMsgs
            ctypes.c_ulong,                    # Timeout (ms)
        ]
        self.dll.PassThruReadMsgs.restype = ctypes.c_long
        self.dll.PassThruWriteMsgs.argtypes = [
            ctypes.c_ulong,                    # ChannelID
            ctypes.POINTER(PASSTHRU_MSG),      # pMsg
            ctypes.POINTER(ctypes.c_ulong),    # pNumMsgs
            ctypes.c_ulong,                    # Timeout (ms)
        ]
        self.dll.PassThruWriteMsgs.restype = ctypes.c_long
        self.dll.PassThruStartMsgFilter.argtypes = [
            ctypes.c_ulong,                    # ChannelID
            ctypes.c_ulong,                    # FilterType
            ctypes.POINTER(PASSTHRU_MSG),      # pMaskMsg
            ctypes.POINTER(PASSTHRU_MSG),      # pPatternMsg
            ctypes.c_void_p,                   # pFlowControlMsg (NULL for raw CAN)
            ctypes.POINTER(ctypes.c_ulong),    # pFilterID
        ]
        self.dll.PassThruStartMsgFilter.restype = ctypes.c_long
        self.dll.PassThruIoctl.argtypes = [
            ctypes.c_ulong, ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p
        ]
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
            app_logger.debug(f"[J2534] Connect with proto={PROTOCOL_CAN} failed: {res} (0x{res:02X}), trying proto=6")
            res = self.dll.PassThruConnect(
                self.device_id, 6, CONNECT_FLAG_NONE,
                baudrate, ctypes.byref(self.channel_id)
            )
            used_protocol = 6
        if res != STATUS_NOERROR:
            print(f"[J2534] PassThruConnect failed: {res} (0x{res:02X})")
            self.dll.PassThruClose(self.device_id)
            return False
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

        # Set up a pass-all filter for CAN IDs
        # Mask=0x00000000, Pattern=0x00000000 → (ID & 0) == (Pattern & 0) evaluates 0 == 0 (true for all IDs)
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

        # Clear RX buffer after filter setup
        self.dll.PassThruIoctl(self.channel_id, IOCTL_CLEAR_RX_BUFFER, None, None)

        self._connected = True
        print(f"[J2534] Connected successfully at {baudrate} bps.")
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
            return True
        if res == ERR_TIMEOUT and can_id == 0x101:
            app_logger.debug(f"[J2534] Functional TX on 0x{can_id:03X} returned ERR_TIMEOUT (expected for broadcast)")
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

            # Verbose debug: log every raw frame before filtering.
            # This is essential for diagnosing CAN ID packing differences between
            # J2534 driver implementations (Kvaser vs Scanmatik vs Tactrix).
            app_logger.debug(
                f"[J2534] RX raw: can_id=0x{rx_can_id:08X} "
                f"RxStatus=0x{msg.RxStatus:08X} "
                f"DataSize={msg.DataSize} "
                f"Data={bytes(msg.Data[:max(msg.DataSize, 1)]).hex()}"
            )

            # J2534 spec §7.3.4: RxStatus bit 0x20 (TX_MSG_TYPE) means this is
            # a TX echo / loopback — the adapter confirming it sent our own frame.
            # SM2 USB (and most J2534 devices) populate this bit; Kvaser typically
            # does not echo at all.  We must discard these echoes so they are never
            # mistaken for ECU responses (which would cause enter_programming_mode
            # and all PID reads to fail with "Unknown").
            TX_MSG_TYPE = 0x20
            if msg.RxStatus & TX_MSG_TYPE:
                app_logger.debug(
                    f"[J2534] TX echo discarded: can_id=0x{rx_can_id:03X} "
                    f"RxStatus=0x{msg.RxStatus:08X}"
                )
                return 0, b""

            if payload_len <= 0:
                return 0, b""

            # Filter to diagnostic IDs only (matching Kvaser behavior)
            if rx_can_id in self.DIAG_IDS:
                payload = bytes(msg.Data[4:4 + payload_len])
                return rx_can_id, payload

            # Frame received but CAN ID not in diagnostic set — log for diagnosis
            app_logger.debug(
                f"[J2534] RX filtered out: can_id=0x{rx_can_id:08X} not in DIAG_IDS. "
                f"If this is a valid ECU response, the DIAG_IDS set or CAN ID decoding may need updating."
            )
            return 0, b""

        if res not in (STATUS_NOERROR, ERR_BUFFER_EMPTY, ERR_TIMEOUT, ERR_FAILED):
            app_logger.debug(f"[J2534] read_frame: unexpected error res=0x{res:02X}, num_msgs={num_msgs.value}")

        return 0, b""