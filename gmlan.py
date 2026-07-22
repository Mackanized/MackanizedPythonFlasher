import time
import ctypes
from typing import Optional
from adapters.base_adapter import BaseAdapter
from ecus.base_ecu import BaseECU
from logger import can_logger, app_logger

FRAME_TYPE_SF = 0x0
FRAME_TYPE_FF = 0x1
FRAME_TYPE_CF = 0x2
FRAME_TYPE_FC = 0x3

# ISO-TP physical frame padding byte is 0x00; GMLAN functional broadcast uses 0xAA
GMLAN_PADDING_BYTE = 0x00

class ISOTPTransport:
    def __init__(self, adapter: BaseAdapter, tx_id: int, rx_id: int, stmin_s: float = 0.0):
        self.adapter = adapter
        self.tx_id = tx_id
        self.rx_id = rx_id
        self.stmin_s = stmin_s

    def send_payload(self, payload: bytes) -> bool:
        length = len(payload)

        # Single Frame
        if length <= 7:
            frame_data = bytes([(FRAME_TYPE_SF << 4) | length]) + payload
            frame_data = frame_data.ljust(8, bytes([GMLAN_PADDING_BYTE]))
            can_logger.info(f"TX | 0x{self.tx_id:03X} | {frame_data.hex(' ').upper()}")
            return self.adapter.send_frame(self.tx_id, frame_data)

        # Multi-Frame First Frame
        ff_header = bytes([(FRAME_TYPE_FF << 4) | ((length >> 8) & 0x0F), length & 0xFF])
        ff_data = (ff_header + payload[:6]).ljust(8, bytes([GMLAN_PADDING_BYTE]))
        can_logger.info(f"TX | 0x{self.tx_id:03X} | {ff_data.hex(' ').upper()}")    
        if not self.adapter.send_frame(self.tx_id, ff_data):
            return False

        # Wait for Flow Control
        fc_received = False
        stmin_s = self.stmin_s
        start_time = time.time()
        while time.time() - start_time < 1.0:
            rx_id, rx_data = self.adapter.read_frame(timeout_ms=100)
            if rx_data:
                can_logger.info(f"RX | 0x{rx_id:03X} | {rx_data.hex(' ').upper()}")
            if rx_id == self.rx_id and len(rx_data) >= 3:
                if ((rx_data[0] >> 4) & 0x0F) == FRAME_TYPE_FC:
                    fc_received = True
                    stmin_byte = rx_data[2]
                    if 0x01 <= stmin_byte <= 0x7F:
                        stmin_s = max(0.0007, stmin_byte / 1000.0)
                    else:
                        # 0x00, 0xF1-0xF9, or reserved: 0.7 ms frame separation (matches OEM 410 ms per 4KB block)
                        stmin_s = 0.0007
                    break

        if not fc_received:
            app_logger.warning("[ISO-TP] Flow Control timeout waiting for ECU.")
            return False

        # Consecutive Frames
        bytes_sent = 6
        seq_num = 1
        stmin_s = max(stmin_s, 0.0012)

        winmm = None
        if hasattr(ctypes, 'windll'):
            try:
                winmm = ctypes.windll.winmm
                winmm.timeBeginPeriod(1)
            except Exception:
                pass

        try:
            while bytes_sent < length:
                chunk = payload[bytes_sent:bytes_sent + 7]
                cf_header = bytes([(FRAME_TYPE_CF << 4) | (seq_num & 0x0F)])
                cf_data = (cf_header + chunk).ljust(8, bytes([GMLAN_PADDING_BYTE]))
                can_logger.info(f"TX | 0x{self.tx_id:03X} | {cf_data.hex(' ').upper()}")
                
                target = time.perf_counter() + stmin_s
                if not self.adapter.send_frame(self.tx_id, cf_data):
                    return False
                bytes_sent += len(chunk)
                seq_num = (seq_num + 1) & 0x0F
                
                if stmin_s > 0.0:
                    while time.perf_counter() < target:
                        pass
        finally:
            if winmm:
                try:
                    winmm.timeEndPeriod(1)
                except Exception:
                    pass

        return True

    def receive_payload(self, timeout_s: float = 2.0) -> Optional[bytes]:
        start_time = time.time()
        rx_buffer = bytearray()
        expected_length = 0
        expected_seq = 1

        while time.time() - start_time < timeout_s:
            rx_id, rx_data = self.adapter.read_frame(timeout_ms=100)
            if not rx_data:
                continue

            # Log all incoming frames on the CAN bus
            can_logger.info(f"RX | 0x{rx_id:03X} | {rx_data.hex(' ').upper()}")

            if rx_id != self.rx_id:
                continue

            frame_type = (rx_data[0] >> 4) & 0x0F

            if frame_type == FRAME_TYPE_SF:
                length = rx_data[0] & 0x0F
                return bytes(rx_data[1:1 + length])

            elif frame_type == FRAME_TYPE_FF:
                # First Frame: Total length is encoded in lower nibble of byte 0 and byte 1
                expected_length = ((rx_data[0] & 0x0F) << 8) | rx_data[1]
                # Payload starts at byte 2 (skip PCI bytes)
                rx_buffer.extend(rx_data[2:8])
                expected_seq = 1
                
                # Send Flow Control (CTS)
                fc_frame = bytes([0x30, 0x00, 0x00]).ljust(8, bytes([GMLAN_PADDING_BYTE]))
                can_logger.info(f"TX | 0x{self.tx_id:03X} | {fc_frame.hex(' ').upper()}")
                self.adapter.send_frame(self.tx_id, fc_frame)

            elif frame_type == FRAME_TYPE_CF:
                current_seq = rx_data[0] & 0x0F
                
                # Extract clean data bytes (skip the CF sequence byte at index 0)
                remaining = expected_length - len(rx_buffer)
                chunk_len = min(7, remaining)
                rx_buffer.extend(rx_data[1:1 + chunk_len])
                
                if len(rx_buffer) >= expected_length:
                    return bytes(rx_buffer)
                    
                expected_seq = (expected_seq + 1) & 0x0F

        return None if not rx_buffer else bytes(rx_buffer)


class GMLANClient:
    def __init__(self, adapter: BaseAdapter, ecu: BaseECU):
        self.ecu = ecu
        self.tp = ISOTPTransport(adapter, ecu.CAN_ID_TX, ecu.CAN_ID_RX)

    def send_functional_message(self, service_id: int, subfunction: Optional[int] = None) -> bool:
        """
        Sends GMLAN Functional Broadcast to CAN ID 0x101 with Subnet Header 0xFE.
        Format: FE [len] [service_id] [subfunction if present] padded with 0xAA.
        """
        payload = [0xFE]
        if subfunction is not None:
            payload.extend([0x02, service_id, subfunction])
        else:
            payload.extend([0x01, service_id])
            
        frame_data = bytes(payload).ljust(8, bytes([0xAA]))
        can_logger.info(f"TX | 0x101 | {frame_data.hex(' ').upper()}")
        return self.tp.adapter.send_frame(0x101, frame_data)

    def wakeup_bus(self):
        """Sends Functional TesterPresent ping to ensure CAN transceiver is awake."""
        app_logger.debug("Sending Wakeup Pulse (Functional TesterPresent)...")
        self.send_functional_message(0x3E)
        time.sleep(0.05)
        self.tp.receive_payload(timeout_s=0.2)

    def send_tester_present(self) -> bool:
        """Sends Functional TesterPresent (0x3E) on CAN ID 0x101 to keep session active."""
        if not self.send_functional_message(0x3E):
            return False
        self.tp.receive_payload(timeout_s=0.2)
        return True

    def enter_programming_mode(self) -> bool:
        self.wakeup_bus()
        if not self.send_functional_message(0x10, 0x02):
            app_logger.error("[GMLAN] Failed to send Functional Programming Session request.")
            return False
        resp = self.tp.receive_payload(timeout_s=2.0)
        if resp is not None and (resp[0] == 0x50 or (resp[0] == 0x7F and len(resp) >= 3 and resp[1] == 0x10 and resp[2] in (0x11, 0x12, 0x22))):
            app_logger.info("[GMLAN] Programming Session Active.")
            return True
        app_logger.error(f"[GMLAN] Programming Session rejected. Response: {resp.hex() if resp else 'None'}")
        return False

    def request_seed(self) -> Optional[int]:
        payload = bytes([0x27, self.ecu.SECURITY_LEVEL])
        for retry in range(5):
            if not self.tp.send_payload(payload):
                return None
            resp = self.tp.receive_payload(timeout_s=3.0)
            if resp and len(resp) >= 4 and resp[0] == 0x67:
                return (resp[2] << 8) | resp[3]
            if resp and len(resp) >= 3 and resp[0] == 0x7F and resp[2] == 0x37:
                app_logger.info("[GMLAN] Security delay active (NRC 0x37). Waiting 10s...")
                time.sleep(10.0)
                continue
            time.sleep(0.5)
        return None

    def send_key(self, key: int) -> bool:
        key_level = self.ecu.SECURITY_LEVEL + 1
        payload = bytes([0x27, key_level, (key >> 8) & 0xFF, key & 0xFF])
        if not self.tp.send_payload(payload):
            return False
        resp = self.tp.receive_payload()
        return resp is not None and resp[0] == 0x67

    def authenticate(self) -> bool:
        seed = self.request_seed()
        if seed is None:
            app_logger.error("[GMLAN] Security Seed Request Failed.")
            return False

        if seed == 0x0000:
            app_logger.info("[GMLAN] ECU already unlocked (seed is 0x0000).")
            return True

        key = self.ecu.calculate_key(seed)
        app_logger.info(f"[GMLAN] Seed: 0x{seed:04X} -> Calculated Key: 0x{key:04X}")

        if self.send_key(key):
            app_logger.info("[GMLAN] Security Access Granted!")
            return True
        else:
            app_logger.error("[GMLAN] Security Access Denied.")
            return False

    def request_upload(self, memory_address: int, size: int) -> Optional[bytes]:
        """
        Request the ECU to upload a flash region.

        The default ISO‑TP timeout of 5 seconds may be insufficient for larger
        memory blocks or slower bus conditions, leading to intermittent failures.
        We increase the timeout to 15 seconds to improve stability.
        """
        addr_bytes = memory_address.to_bytes(4, 'big')
        size_bytes = size.to_bytes(4, 'big')
        payload = bytes([0x34, 0x00]) + addr_bytes + size_bytes
        
        if not self.tp.send_payload(payload):
            return None
        
        resp = self.tp.receive_payload(timeout_s=30.0)
        if resp and resp[0] == 0x74:
            return resp
        return None

    def transfer_data(self, block_sequence_counter: int) -> Optional[bytes]:
        payload = bytes([0x36, block_sequence_counter & 0xFF])
        if not self.tp.send_payload(payload):
            return None
        # Increased timeout to tolerate slower ECU responses
        return self.tp.receive_payload(timeout_s=10.0)

    def request_transfer_exit(self) -> bool:
        payload = bytes([0x37])
        if not self.tp.send_payload(payload):
            return False
        resp = self.tp.receive_payload(timeout_s=2.0)
        return resp is not None and resp[0] == 0x77

    def read_memory_by_address(self, address: int, size: int, timeout_s: float = 5.0) -> Optional[bytes]:
        addr_len_identifier = getattr(self.ecu, 'ADDR_LEN_IDENTIFIER', 0x00)
        # 3-byte address format (big‑endian)
        addr_bytes = address.to_bytes(4, 'big')[1:]  
        size_bytes = size.to_bytes(2, 'big')        
        payload = bytes([0x23, addr_len_identifier]) + addr_bytes + size_bytes
        
        if not self.tp.send_payload(payload):
            raise TimeoutError("Failed to send ReadMemoryByAddress request")
            
        resp = self.tp.receive_payload(timeout_s=timeout_s)
        
        if resp is None:
            raise TimeoutError(f"ECU did not respond to ReadMemoryByAddress at 0x{address:06X}")
            
        # Positive response for 0x23: 0x63 (1 byte) + 1 byte format + 3 bytes echoed address = 5 bytes header.
        if resp[0] == 0x63 and len(resp) >= 5:
            return resp[5:5 + size]
            
        if resp[0] == 0x7F:
            app_logger.debug(f"[NRC] ReadMemoryByAddress at 0x{address:06X} returned negative response: {resp.hex()}")
            
        return None

    def disable_normal_communication(self) -> bool:
        """Sends Functional $28 request to disable normal communication across all CAN nodes."""
        if not self.send_functional_message(0x28):
            return False
        resp = self.tp.receive_payload(timeout_s=2.0)
        return resp is not None and resp[0] == 0x68

    def report_programmed_state(self) -> bool:
        """Sends Functional $A2 request to check programming state."""
        if not self.send_functional_message(0xA2):
            return False
        resp = self.tp.receive_payload(timeout_s=2.0)
        return resp is not None and resp[0] == 0xE2

    def request_programming_mode_a501(self) -> bool:
        """Sends Functional $A5 01 to request programming session."""
        if not self.send_functional_message(0xA5, 0x01):
            return False
        resp = self.tp.receive_payload(timeout_s=2.0)
        return resp is not None and resp[0] == 0xE5

    def enable_programming_mode_a503(self) -> bool:
        """Sends Functional $A5 03 to enable programming mode. Expected to have no response."""
        return self.send_functional_message(0xA5, 0x03)

    def request_download(self, size: int) -> bool:
        """
        Sends $34 00 [3-byte size] to initiate download event, triggering internal flash erase.
        Monitors negative response 7F 34 78 (Response Pending) while the ECU erases.
        """
        size_bytes = size.to_bytes(3, 'big')
        payload = bytes([0x34, 0x00]) + size_bytes
        
        if not self.tp.send_payload(payload):
            return False
            
        start_time = time.time()
        timeout_s = 40.0
        
        while time.time() - start_time < timeout_s:
            resp = self.tp.receive_payload(timeout_s=1.0)
            if resp is None:
                continue
                
            if resp[0] == 0x74:
                app_logger.info("[GMLAN] RequestDownload accepted. Erase completed successfully.")
                return True
                
            if resp[0] == 0x7F and len(resp) >= 3 and resp[1] == 0x34:
                nrc = resp[2]
                if nrc == 0x78:
                    app_logger.info("ECU returned Response Pending (0x78) for RequestDownload...")
                    start_time = time.time()
                    continue
                else:
                    app_logger.error(f"[GMLAN] RequestDownload rejected with NRC: 0x{nrc:02X}")
                    return False
                    
        app_logger.error("[GMLAN] RequestDownload timed out waiting for erase completion.")
        return False

    def write_memory_block(self, address: int, data: bytes) -> bool:
        """
        Sends multi-frame TransferData request $36 00 [3-byte address] + [data].
        GMLAN service 0x36 requires subfunction 0x00 when passing 3-byte memory address.
        Block sequence counter is always 0x00 in GMLAN (address provides sequencing).
        """
        addr_bytes = address.to_bytes(4, 'big')[1:]  # 3-byte address
        payload = bytes([0x36, 0x00]) + addr_bytes + data
        
        if not self.tp.send_payload(payload):
            app_logger.error(f"[GMLAN] Failed to send TransferData block at 0x{address:06X}")
            return False
            
        start_time = time.time()
        timeout_s = 15.0
        
        while time.time() - start_time < timeout_s:
            resp = self.tp.receive_payload(timeout_s=1.0)
            if resp is None:
                continue
                
            if resp[0] == 0x76:
                return True
                
            if resp[0] == 0x7F and len(resp) >= 3 and resp[1] == 0x36:
                nrc = resp[2]
                if nrc == 0x78:
                    app_logger.debug(f"[GMLAN] ECU returned Response Pending (0x78) for TransferData at 0x{address:06X}. Waiting...")
                    start_time = time.time()
                    continue
                else:
                    app_logger.error(f"[GMLAN] TransferData rejected at 0x{address:06X} with NRC: 0x{nrc:02X}")
                    return False
                    
        app_logger.error(f"[GMLAN] TransferData at 0x{address:06X} timed out.")
        return False

    def return_to_normal_mode(self) -> bool:
        """Sends Functional $20 to CAN ID 0x101 to reset the ECU and return to normal mode."""
        return self.send_functional_message(0x20)

    def read_data_by_identifier(self, pid: int, timeout_s: float = 3.0) -> Optional[bytes]:
        """Sends $1A [pid] to read ECU diagnostic identifier data."""
        payload = bytes([0x1A, pid])
        if not self.tp.send_payload(payload):
            return None
            
        start_time = time.time()
        while time.time() - start_time < timeout_s:
            resp = self.tp.receive_payload(timeout_s=1.0)
            if resp is None:
                continue
                
            # If positive response: 0x5A + pid + data
            if resp[0] == 0x5A and len(resp) >= 2 and resp[1] == pid:
                return resp[2:]
                
            # If negative response
            if resp[0] == 0x7F and len(resp) >= 3 and resp[1] == 0x1A:
                nrc = resp[2]
                if nrc == 0x78:
                    # ECU is busy — just keep waiting, do NOT send TesterPresent
                    # (send_tester_present consumes the next RX frame which is our actual response)
                    continue
                else:
                    app_logger.debug(f"[GMLAN] PID 0x{pid:02X} rejected with NRC: 0x{nrc:02X}")
                    return None
        return None

    def get_vehicle_vin(self) -> str:
        data = self.read_data_by_identifier(0x90, timeout_s=3.0)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_ecu_hardware(self) -> str:
        data = self.read_data_by_identifier(0x71)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_software_version(self) -> str:
        data = self.read_data_by_identifier(0x08)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_calibration_set(self) -> str:
        data = self.read_data_by_identifier(0x74)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_codefile_version(self) -> str:
        data = self.read_data_by_identifier(0x73)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_ecu_description(self) -> str:
        data = self.read_data_by_identifier(0x72)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_ecu_sw_version_number(self) -> str:
        data = self.read_data_by_identifier(0x95)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_build_date(self) -> str:
        data = self.read_data_by_identifier(0x0A)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_serial_number(self) -> str:
        data = self.read_data_by_identifier(0xB4)
        if not data:
            return "Unknown"
        # 0xB4 can be 4-byte binary or 16-byte ASCII depending on ECU
        if len(data) >= 16:
            s = data[:16].decode('ascii', errors='ignore').strip('\x00')
            return s
        # Short response: format as hex
        return data.hex(' ').upper()

    def get_supplier_id(self) -> str:
        data = self.read_data_by_identifier(0x92)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_hardware_type(self) -> str:
        data = self.read_data_by_identifier(0x97)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_tester_serial(self) -> str:
        data = self.read_data_by_identifier(0x98)
        return data.decode('ascii', errors='ignore').strip() if data else "Unknown"

    def get_part_number_from_pid(self, pid: int) -> str:
        data = self.read_data_by_identifier(pid)
        if not data:
            return "Unknown"
        
        # EDC16C39 uses 16-byte ASCII for C-series PIDs (0xC1-0xC4)
        if len(data) >= 16 and hasattr(self.ecu, 'FORMAT_C_SERIES_AS_ASCII'):
            s = data[:16].decode('ascii', errors='ignore').strip('\x00')
            return f"{s[:8]}-{s[8:]}" if len(s) >= 16 else s
        
        # Default: 4-byte binary for other ECUs
        if data and len(data) >= 3:
            val = int.from_bytes(data, 'big')
            return str(val) if val != 0 else "Unknown"
        return "Unknown"

    def get_main_os(self) -> str:
        return self.get_part_number_from_pid(0xC1)

    def get_engine_calib(self) -> str:
        return self.get_part_number_from_pid(0xC2)

    def get_system_calib(self) -> str:
        return self.get_part_number_from_pid(0xC3)

    def get_speedo_calib(self) -> str:
        return self.get_part_number_from_pid(0xC4)

    def get_slave_os(self) -> str:
        return self.get_part_number_from_pid(0xC5)

    def get_diagnostic_address(self) -> str:
        data = self.read_data_by_identifier(0xB0)
        return f"0x{data[0]:02X}" if data else "Unknown"

    def get_programming_date_me96(self) -> str:
        data = self.read_data_by_identifier(0x99)
        if data and len(data) >= 4:
            # 4-byte BCD: YYYY-MM-DD (each nibble is a decimal digit)
            try:
                y = f"{data[0]>>4:X}{data[0]&0x0F:X}{data[1]>>4:X}{data[1]&0x0F:X}"
                m = f"{data[2]>>4:X}{data[2]&0x0F:X}"
                d = f"{data[3]>>4:X}{data[3]&0x0F:X}"
                return f"{y}-{m}-{d}"
            except Exception:
                val = int.from_bytes(data[:4], 'big')
                return f"{val:X}"
        return "Unknown"

    def get_top_speed(self) -> str:
        data = self.read_data_by_identifier(0x02)
        if data and len(data) >= 2:
            val = (data[0] << 8) | data[1]
            return f"{val / 10:.1f} km/h"
        return "Unknown"

    def get_radum(self) -> str:
        data = self.read_data_by_identifier(0x24)
        return str(data[0]) if data else "Unknown"

    def get_pmc_w(self) -> str:
        data = self.read_data_by_identifier(0x2E)
        if data and len(data) >= 2:
            val = (data[0] << 8) | data[1]
            return f"{val / 10:.1f}"
        return "Unknown"

    def get_saab_partnumber(self) -> str:
        data = self.read_data_by_identifier(0x7C)
        if data and len(data) >= 4:
            return str(int.from_bytes(data[:4], 'big'))
        return "Unknown"

    def get_end_model_partnumber(self) -> str:
        data = self.read_data_by_identifier(0xCB)
        if data and len(data) >= 4:
            return str(int.from_bytes(data[:4], 'big'))
        return "Unknown"

    def get_base_model_partnumber(self) -> str:
        data = self.read_data_by_identifier(0xCC)
        if data and len(data) >= 4:
            return str(int.from_bytes(data[:4], 'big'))
        return "Unknown"

    def get_diagnostic_data_identifier(self) -> str:
        data = self.read_data_by_identifier(0x9A)
        if data and len(data) >= 2:
            return f"0x{data[0]:02X} 0x{data[1]:02X}"
        return "Unknown"

    def get_manufacturers_enable_counter(self) -> str:
        data = self.read_data_by_identifier(0xA0)
        return str(data[0]) if data else "Unknown"

    def get_bosch_enable_counter(self) -> str:
        data = self.read_data_by_identifier(0x70)
        return f"0x{data[0]:X}" if data else "Unknown"