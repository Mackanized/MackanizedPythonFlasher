"""Stateful virtual CAN adapter and ECU simulator.

The simulator operates at the raw CAN boundary used by :class:`ISOTPTransport`.
It reassembles tester requests, emits ISO-TP flow-control and segmented ECU
responses, and maintains an in-memory flash image.  This makes read, write,
identification, security-access, and verification workflows testable without
special cases in the application or protocol layers.

It is a simulator, not evidence that any physical ECU implements these exact
responses.  Production UIs must label it accordingly.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from adapters.base_adapter import BaseAdapter


class MockAdapter(BaseAdapter):
    """Stateful GMLAN/ISO-TP ECU simulator with writable flash memory."""

    FUNCTIONAL_REQUEST_ID = 0x101

    def __init__(
        self,
        flash_size: int = 0x400000,
        tx_id: int = 0x7E0,
        rx_id: int = 0x7E8,
    ) -> None:
        super().__init__()
        self._connected = False
        self._baudrate = 500000
        self._tx_id = tx_id
        self._rx_id = rx_id
        self._rx_queue: Deque[Tuple[int, bytes]] = deque()

        self._request_expected = 0
        self._request_buffer = bytearray()
        self._request_seq = 1
        self._response_remainder = b""
        self._response_seq = 1

        self._programming_session = False
        self._security_unlocked = False
        self._download_active = False
        self._simulation_session = False
        self._simulation_seed: Optional[int] = None
        self._simulation_finalized = False
        self._simulation_dirty = False
        self._simulation_download_start = 0
        self._simulation_download_size = 0
        self._simulation_download_offset = 0
        self._simulation_block_counter = 1
        self._simulation_failures: Dict[str, int] = {}
        self._simulation_events: List[str] = []
        self._flash = self._make_initial_flash(flash_size)
        self._pids = self._default_pids()
        self._dtcs = [
            ("P0300", "Simulated random/multiple-cylinder misfire", "Active", "Medium"),
            ("P0100", "Simulated mass-air-flow circuit fault", "Pending", "Low"),
        ]

    @property
    def is_simulation(self) -> bool:
        return True

    def is_connected(self) -> bool:
        return self._connected

    @property
    def flash_size(self) -> int:
        return len(self._flash)

    @property
    def supply_voltage(self) -> float:
        return 13.8

    def configure_ecu(self, tx_id: int, rx_id: int, flash_size: int) -> None:
        """Configure addressing and ensure memory covers the selected ECU."""
        with self._bus_lock:
            self._tx_id = tx_id
            self._rx_id = rx_id
            if flash_size > len(self._flash):
                extension = self._make_initial_flash(flash_size - len(self._flash), len(self._flash))
                self._flash.extend(extension)
            self.flush_rx_buffer()

    def configure_for_ecu(self, tx_id: int, rx_id: int, flash_size: int) -> None:
        self.configure_ecu(tx_id, rx_id, flash_size)

    def connect(self, baudrate: int = 500000, channel: int = 0) -> bool:
        del channel
        with self._bus_lock:
            self._baudrate = baudrate
            self._set_nominal_bitrate(baudrate)
            self._connected = True
            self._reset_transport()
            return True

    def disconnect(self) -> None:
        with self._bus_lock:
            self._connected = False
            self._programming_session = False
            self._security_unlocked = False
            self._download_active = False
            self._reset_simulation_state()
            self._reset_transport()

    def flush_rx_buffer(self) -> None:
        with self._bus_lock:
            self._rx_queue.clear()

    def check_bus_status(self) -> bool:
        return self._connected

    def send_frame(self, can_id: int, data: bytes, is_extended: bool = False) -> bool:
        del is_extended
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not 1 <= len(data) <= 8:
                raise ValueError("MockAdapter accepts classic CAN frames of 1..8 bytes")
            self._record_tx(len(data))

            if can_id == self.FUNCTIONAL_REQUEST_ID:
                self._handle_functional_frame(data)
                return True

            if can_id != self._tx_id:
                return True

            frame_type = (data[0] >> 4) & 0x0F
            if frame_type == 0x0:
                payload_length = data[0] & 0x0F
                self._handle_request(bytes(data[1:1 + payload_length]))
            elif frame_type == 0x1:
                self._start_request(data)
            elif frame_type == 0x2:
                self._continue_request(data)
            elif frame_type == 0x3:
                self._release_response_frames(data)
            return True

    def read_frame(self, timeout_ms: int = 100) -> Tuple[int, bytes]:
        del timeout_ms
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if self._rx_queue:
                can_id, data = self._rx_queue.popleft()
                self._record_rx(len(data))
                return can_id, data
            return 0, b""

    def memory_snapshot(self, start: int = 0, length: Optional[int] = None) -> bytes:
        with self._bus_lock:
            end = len(self._flash) if length is None else start + length
            self._validate_range(start, end - start)
            return bytes(self._flash[start:end])

    def read_simulated_dtcs(self):
        self._require_connected()
        return list(self._dtcs)

    def clear_simulated_dtcs(self) -> None:
        self._require_connected()
        self._dtcs.clear()

    @property
    def simulation_events(self) -> Tuple[str, ...]:
        """Semantic operation trace used by hardware-free workflow tests."""
        with self._bus_lock:
            return tuple(self._simulation_events)

    def inject_simulation_failure(self, phase: str, count: int = 1) -> None:
        """Fail a named semantic phase a bounded number of times."""
        if not phase.strip() or count < 1:
            raise ValueError("Simulation failure requires a phase and positive count")
        with self._bus_lock:
            self._simulation_failures[phase] = count

    def simulation_enter_session(self) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            self._fail_simulation_phase("enter_session")
            self._simulation_session = True
            self._simulation_events.append("enter_session")
            return True

    def simulation_request_seed(self, level: int, seed_length: int = 2) -> int:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not self._simulation_session:
                raise RuntimeError("Mock ECU SecurityAccess requested outside a session")
            self._fail_simulation_phase("request_seed")
            if seed_length <= 0 or seed_length > 8:
                raise ValueError("Mock ECU seed length must be between one and eight bytes")
            seed_bytes = bytes((6, 5, 4, 3, 2, 1)) if seed_length == 6 else bytes.fromhex("5F94")
            if len(seed_bytes) != seed_length:
                seed_bytes = bytes(range(1, seed_length + 1))
            self._simulation_seed = int.from_bytes(seed_bytes, "big")
            self._simulation_events.append(f"request_seed:{level:02X}")
            return self._simulation_seed

    def simulation_submit_key(self, level: int, key: int, expected_key: int) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if self._simulation_seed is None:
                raise RuntimeError("Mock ECU key submitted before seed request")
            self._fail_simulation_phase("submit_key")
            accepted = 0 <= key <= 0xFFFFFFFFFFFFFFFF and key == expected_key
            self._security_unlocked = accepted
            self._simulation_events.append(f"submit_key:{level:02X}:{'ok' if accepted else 'rejected'}")
            return accepted

    def simulation_read_memory(self, address: int, size: int) -> bytes:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not self._simulation_session or not self._security_unlocked:
                raise RuntimeError("Mock ECU memory read requires an authenticated session")
            self._fail_simulation_phase("read")
            self._validate_range(address, size)
            self._simulation_events.append(f"read:{address:06X}:{size}")
            return bytes(self._flash[address:address + size])

    def simulation_begin_download(self, size: int) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not self._simulation_session or not self._security_unlocked:
                raise RuntimeError("Mock ECU download requires an authenticated session")
            if not 0 < size <= len(self._flash):
                raise ValueError("Mock ECU download size lies outside flash")
            self._fail_simulation_phase("erase")
            self._download_active = True
            self._simulation_finalized = False
            self._simulation_dirty = False
            self._simulation_events.append(f"erase:{size}")
            return True

    def simulation_write_memory(self, address: int, data: bytes) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not self._download_active:
                raise RuntimeError("Mock ECU TransferData sent before RequestDownload")
            self._fail_simulation_phase("transfer")
            self._validate_range(address, len(data))
            self._flash[address:address + len(data)] = data
            self._simulation_dirty = True
            self._simulation_events.append(f"transfer:{address:06X}:{len(data)}")
            return True

    def simulation_finalize_transfer(self) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not self._download_active or not self._simulation_dirty:
                return False
            self._fail_simulation_phase("finalize")
            self._download_active = False
            self._simulation_finalized = True
            self._simulation_events.append("finalize")
            return True

    def simulation_verify(self) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            self._fail_simulation_phase("verify")
            result = self._simulation_finalized and self._simulation_dirty
            self._simulation_events.append(f"verify:{'ok' if result else 'failed'}")
            return result

    def simulation_tester_present(self) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not self._simulation_session:
                return False
            self._fail_simulation_phase("tester_present")
            self._simulation_events.append("tester_present")
            return True

    def simulation_reset(self) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            self._fail_simulation_phase("reset")
            self._simulation_events.append("reset")
            self._simulation_session = False
            self._security_unlocked = False
            self._simulation_seed = None
            self._download_active = False
            return True

    def simulation_ecu_info(self) -> Dict[str, str]:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            self._fail_simulation_phase("identify")
            self._simulation_events.append("identify")
            return {
                "vin": self._pids[0x90].decode("ascii"),
                "serial": self._pids[0xB4].decode("ascii"),
                "hardware_type": self._pids[0x97].decode("ascii"),
                "supplier": self._pids[0x92].decode("ascii"),
                "main_os": str(int.from_bytes(self._pids[0xC1], "big")),
                "engine_calib": str(int.from_bytes(self._pids[0xC2], "big")),
            }

    def simulation_trionic_phase(self, generation: str, phase: str) -> bool:
        """Record one generation-specific semantic phase with failure injection."""
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            key = f"trionic_{phase.replace('-', '_')}"
            self._fail_simulation_phase(key)
            self._simulation_events.append(f"trionic:{generation}:{phase}")
            return True

    def simulation_trionic_erase_range(self, generation: str, start: int, size: int) -> bool:
        """Model the exact range erased by a Trionic family coordinator."""
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            self._validate_range(start, size)
            self._fail_simulation_phase("trionic_erase_range")
            self._flash[start:start + size] = b"\xFF" * size
            self._simulation_events.append(
                f"trionic:{generation}:erase:{start:06X}:{size}"
            )
            return True

    # EDC16C39 uses SecurityAccess before its 0x84 programming session and
    # downloads four address-specific destinations separated by an ECU reset.
    # These semantic primitives model that distinct contract without claiming
    # that the virtual responses are captured physical CAN traffic.

    def simulation_edc16_request_seed(self, level: int, seed_length: int) -> int:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            self._fail_simulation_phase("edc16_security")
            if level != 0x05 or seed_length != 6:
                raise ValueError("EDC16 mock accepts only the level-05 six-byte seed")
            seed = bytes.fromhex("060504030201")
            self._simulation_seed = int.from_bytes(seed, "big")
            self._simulation_events.append("request_seed:05")
            self._simulation_events.append("edc16:security:seed:05")
            return self._simulation_seed

    def simulation_edc16_submit_key(self, level: int, key: int, expected_key: int) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if self._simulation_seed is None:
                raise RuntimeError("EDC16 mock key submitted before seed request")
            self._fail_simulation_phase("edc16_key")
            accepted = level == 0x06 and key == expected_key
            self._security_unlocked = accepted
            self._simulation_events.append(f"edc16:security:key:06:{'ok' if accepted else 'rejected'}")
            return accepted

    def simulation_edc16_start_session(self) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not self._security_unlocked:
                raise RuntimeError("EDC16 mock programming session requires SecurityAccess first")
            self._fail_simulation_phase("edc16_session")
            self._simulation_session = True
            self._simulation_events.append("edc16:session:84")
            return True

    def simulation_edc16_erase(self, address: int, size: int) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not self._simulation_session or not self._security_unlocked:
                raise RuntimeError("EDC16 mock erase requires an authenticated 0x84 session")
            self._fail_simulation_phase("edc16_erase")
            self._validate_range(address, size)
            self._flash[address:address + size] = b"\xFF" * size
            self._simulation_events.append(f"edc16:erase:{address:08X}:{size}")
            return True

    def simulation_edc16_begin_download(self, address: int, size: int) -> int:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not self._simulation_session or not self._security_unlocked:
                raise RuntimeError("EDC16 mock download requires an authenticated 0x84 session")
            self._fail_simulation_phase("edc16_download")
            self._validate_range(address, size)
            self._download_active = True
            self._simulation_finalized = False
            self._simulation_dirty = False
            self._simulation_download_start = address
            self._simulation_download_size = size
            self._simulation_download_offset = 0
            self._simulation_block_counter = 1
            self._simulation_events.append(f"edc16:download:{address:08X}:{size}")
            return 0x1000

    def simulation_edc16_transfer(self, address: int, counter: int, data: bytes) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            if not self._download_active:
                raise RuntimeError("EDC16 mock TransferData sent before RequestDownload")
            expected_address = self._simulation_download_start + self._simulation_download_offset
            if address != expected_address:
                raise RuntimeError(
                    f"EDC16 mock expected address 0x{expected_address:08X}, got 0x{address:08X}"
                )
            if counter != self._simulation_block_counter:
                raise RuntimeError(
                    f"EDC16 mock expected block counter {self._simulation_block_counter}, got {counter}"
                )
            if self._simulation_download_offset + len(data) > self._simulation_download_size:
                raise RuntimeError("EDC16 mock TransferData exceeds negotiated destination")
            self._fail_simulation_phase("edc16_transfer")
            self._flash[address:address + len(data)] = data
            self._simulation_download_offset += len(data)
            self._simulation_block_counter = (counter + 1) & 0xFF
            self._simulation_dirty = True
            self._simulation_events.append(f"edc16:transfer:{address:08X}:{counter:02X}:{len(data)}")
            return True

    def simulation_edc16_finalize(self) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            complete = (
                self._download_active
                and self._simulation_dirty
                and self._simulation_download_offset == self._simulation_download_size
            )
            if not complete:
                return False
            self._fail_simulation_phase("edc16_finalize")
            self._download_active = False
            self._simulation_finalized = True
            self._simulation_events.append("edc16:finalize")
            return True

    def simulation_edc16_reset(self) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            self._fail_simulation_phase("edc16_reset")
            self._simulation_events.append("edc16:reset")
            self._simulation_session = False
            self._security_unlocked = False
            self._simulation_seed = None
            self._download_active = False
            return True

    def simulation_edc16_wait_reconnect(self) -> bool:
        with self._bus_lock:
            self._assert_channel_access()
            self._require_connected()
            self._fail_simulation_phase("edc16_reconnect")
            self._simulation_events.append("edc16:reconnect")
            return True

    def _reset_transport(self) -> None:
        self._rx_queue.clear()
        self._request_expected = 0
        self._request_buffer.clear()
        self._request_seq = 1
        self._response_remainder = b""
        self._response_seq = 1

    def _reset_simulation_state(self) -> None:
        self._simulation_session = False
        self._simulation_seed = None
        self._simulation_finalized = False
        self._simulation_dirty = False
        self._simulation_download_start = 0
        self._simulation_download_size = 0
        self._simulation_download_offset = 0
        self._simulation_block_counter = 1
        self._simulation_events.clear()

    def _fail_simulation_phase(self, phase: str) -> None:
        remaining = self._simulation_failures.get(phase, 0)
        if remaining <= 0:
            return
        if remaining == 1:
            del self._simulation_failures[phase]
        else:
            self._simulation_failures[phase] = remaining - 1
        self._simulation_events.append(f"failure:{phase}")
        raise RuntimeError(f"Injected mock ECU failure during {phase}")

    def _start_request(self, frame: bytes) -> None:
        if len(frame) < 2:
            return
        length = ((frame[0] & 0x0F) << 8) | frame[1]
        header_size = 2
        if length == 0 and len(frame) >= 6:
            length = int.from_bytes(frame[2:6], "big")
            header_size = 6
        self._request_expected = length
        self._request_buffer = bytearray(frame[header_size:])
        self._request_seq = 1
        self._rx_queue.append((self._rx_id, b"\x30\x00\x00".ljust(8, b"\x00")))

    def _continue_request(self, frame: bytes) -> None:
        if not self._request_expected:
            return
        sequence = frame[0] & 0x0F
        if sequence != self._request_seq:
            self._request_expected = 0
            self._request_buffer.clear()
            return
        remaining = self._request_expected - len(self._request_buffer)
        self._request_buffer.extend(frame[1:1 + min(7, remaining)])
        self._request_seq = (self._request_seq + 1) & 0x0F
        if len(self._request_buffer) >= self._request_expected:
            payload = bytes(self._request_buffer[:self._request_expected])
            self._request_expected = 0
            self._request_buffer.clear()
            self._handle_request(payload)

    def _queue_response(self, payload: bytes) -> None:
        if len(payload) <= 7:
            frame = bytes([len(payload)]) + payload
            self._rx_queue.append((self._rx_id, frame.ljust(8, b"\x00")))
            return

        length = len(payload)
        if length > 0xFFF:
            raise ValueError("Mock ECU response exceeds classic ISO-TP test limit")
        first = bytes([0x10 | ((length >> 8) & 0x0F), length & 0xFF]) + payload[:6]
        self._rx_queue.append((self._rx_id, first.ljust(8, b"\x00")))
        self._response_remainder = payload[6:]
        self._response_seq = 1

    def _release_response_frames(self, flow_control: bytes) -> None:
        if not self._response_remainder or (flow_control[0] & 0x0F) != 0:
            return
        block_size = flow_control[1] if len(flow_control) > 1 else 0
        sent_in_block = 0
        while self._response_remainder and (block_size == 0 or sent_in_block < block_size):
            chunk = self._response_remainder[:7]
            self._response_remainder = self._response_remainder[7:]
            frame = bytes([0x20 | self._response_seq]) + chunk
            self._rx_queue.append((self._rx_id, frame.ljust(8, b"\x00")))
            self._response_seq = (self._response_seq + 1) & 0x0F
            sent_in_block += 1

    def _handle_functional_frame(self, frame: bytes) -> None:
        if len(frame) < 3 or frame[0] != 0xFE:
            return
        payload_length = frame[1]
        payload = bytes(frame[2:2 + payload_length])
        if not payload:
            return
        service = payload[0]
        subfunction = payload[1] if len(payload) > 1 else 0

        if service == 0x10:
            self._programming_session = True
            self._queue_response(bytes([0x50, subfunction]))
        elif service == 0x3E:
            self._queue_response(b"\x7E")
        elif service == 0x28:
            self._queue_response(b"\x68")
        elif service == 0xA2:
            self._queue_response(b"\xE2")
        elif service == 0xA5 and subfunction == 0x01:
            self._queue_response(b"\xE5\x01")
        elif service == 0x20:
            self._programming_session = False
            self._security_unlocked = False
            self._download_active = False

    def _handle_request(self, payload: bytes) -> None:
        if not payload:
            return
        service = payload[0]

        if service == 0x27:
            self._handle_security_access(payload)
        elif service == 0x23:
            self._handle_read_memory(payload)
        elif service == 0x34:
            self._download_active = True
            self._queue_response(b"\x74\x10\x20")
        elif service == 0x36:
            self._handle_transfer_data(payload)
        elif service == 0x37:
            if not self._download_active:
                self._queue_response(b"\x7F\x37\x24")
            else:
                self._download_active = False
                self._queue_response(b"\x77")
        elif service == 0x1A:
            pid = payload[1] if len(payload) > 1 else 0
            value = self._pids.get(pid, bytes([pid, 0x00]))
            self._queue_response(bytes([0x5A, pid]) + value)
        elif service == 0x14:
            self._queue_response(b"\x54")
        elif service == 0x19:
            self._queue_response(b"\x59\x02\x00")
        else:
            self._queue_response(bytes([0x7F, service, 0x11]))

    def _handle_security_access(self, payload: bytes) -> None:
        level = payload[1] if len(payload) > 1 else 0
        if level & 1:
            self._queue_response(bytes([0x67, level, 0x12, 0x34]))
        else:
            self._security_unlocked = True
            self._queue_response(bytes([0x67, level]))

    def _handle_read_memory(self, payload: bytes) -> None:
        if len(payload) < 7:
            self._queue_response(b"\x7F\x23\x13")
            return
        address = int.from_bytes(payload[2:5], "big")
        size = int.from_bytes(payload[5:7], "big")
        try:
            self._validate_range(address, size)
        except ValueError:
            self._queue_response(b"\x7F\x23\x31")
            return
        header = bytes([0x63, payload[1]]) + payload[2:5]
        self._queue_response(header + bytes(self._flash[address:address + size]))

    def _handle_transfer_data(self, payload: bytes) -> None:
        if len(payload) < 5 or not self._download_active:
            self._queue_response(b"\x7F\x36\x24")
            return
        address = int.from_bytes(payload[2:5], "big")
        data = payload[5:]
        try:
            self._validate_range(address, len(data))
        except ValueError:
            self._queue_response(b"\x7F\x36\x31")
            return
        self._flash[address:address + len(data)] = data
        self._queue_response(bytes([0x76, payload[1]]) + payload[2:5])

    def _validate_range(self, address: int, size: int) -> None:
        if address < 0 or size < 0 or address + size > len(self._flash):
            raise ValueError(
                f"Mock ECU range 0x{address:X}+0x{size:X} exceeds 0x{len(self._flash):X}"
            )

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("MockAdapter: adapter is not connected")

    @staticmethod
    def _make_initial_flash(size: int, offset: int = 0) -> bytearray:
        pattern = bytes((((offset + i) * 37 + 11) & 0xFF) for i in range(256))
        repeats = (size + len(pattern) - 1) // len(pattern)
        return bytearray((pattern * repeats)[:size])

    @staticmethod
    def _default_pids() -> Dict[int, bytes]:
        return {
            0x90: b"YS3FD79Y666000001",
            0xB4: b"MOCKECU000000001",
            0x97: b"MOCK-HARDWARE",
            0x92: b"Mackanized flasher",
            0xB0: b"\x10",
            0x0A: b"20260722",
            0x99: b"\x20\x26\x07\x22",
            0xC1: (1037383491).to_bytes(4, "big"),
            0xC2: (55500001).to_bytes(4, "big"),
            0xC3: (55500002).to_bytes(4, "big"),
            0xC4: (55500003).to_bytes(4, "big"),
            0xC5: (55500004).to_bytes(4, "big"),
            0x7C: (55353231).to_bytes(4, "big"),
            0xCB: (12700001).to_bytes(4, "big"),
            0xCC: (12700002).to_bytes(4, "big"),
            0x74: b"MOCK-CAL-SET",
            0x73: b"MOCK-CODE-V1",
            0x9A: b"\x12\x34",
            0x98: b"PYFLASH-MOCK",
        }
