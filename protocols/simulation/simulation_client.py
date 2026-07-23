"""Adapter-backed semantic client for complete hardware-free workflows."""

from typing import Dict, Optional

from adapters.base_adapter import BaseAdapter
from domain.cancellation import CancellationToken
from domain.errors import DiagnosticError, SecurityAccessError
from ecus.base_ecu import BaseECU
from protocols.base_protocol import DownloadParameters, ProtocolClient


class SimulationProtocolClient(ProtocolClient):
    """Exercise application state machines without impersonating one wire protocol."""

    def __init__(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> None:
        if not adapter.is_simulation:
            raise ValueError("SimulationProtocolClient requires an explicitly simulated adapter")
        super().__init__(adapter, ecu)
        self._cancel = cancellation_token or CancellationToken()

    def _call(self, name: str, *args):
        method = getattr(self.adapter, name, None)
        if method is None:
            raise DiagnosticError(f"Simulation adapter does not implement {name}")
        return method(*args)

    def enter_programming_mode(self) -> bool:
        self._cancel.check("simulation session entry")
        return bool(self._call("simulation_enter_session"))

    def authenticate(self) -> bool:
        level = self.ecu.SECURITY_LEVEL
        seed = int(self._call("simulation_request_seed", level, self.ecu.SECURITY_POLICY.seed_length))
        if hasattr(self.ecu, "candidate_keys"):
            # T7 accepts several key-derivation variants depending on the
            # physical ECU; the simulator only ever needs the first one.
            key = self.ecu.candidate_keys(seed)[0]
        else:
            key = self.ecu.calculate_key(seed)
        accepted = bool(self._call("simulation_submit_key", level + 1, key, key))
        if not accepted:
            raise SecurityAccessError("Simulated ECU rejected SecurityAccess key", level=level)
        return True

    def prepare_programming_session(self) -> bool:
        return self.enter_programming_mode() and self.authenticate() and self.send_tester_present()

    def read_memory_by_address(self, address: int, size: int, timeout_s: float = 5.0) -> Optional[bytes]:
        del timeout_s
        self._cancel.check("simulation read")
        return bytes(self._call("simulation_read_memory", address, size))

    def request_download(self, size: int) -> DownloadParameters:
        if not self._call("simulation_begin_download", size):
            raise DiagnosticError("Simulated ECU rejected RequestDownload")
        maximum = self.ecu.WRITE_BLOCK_SIZE + self.ecu.TRANSFER_REQUEST_OVERHEAD
        return DownloadParameters(max_request_bytes=maximum, raw_response=b"SIMULATED")

    def write_memory_block(self, address: int, data: bytes) -> bool:
        return bool(self._call("simulation_write_memory", address, bytes(data)))

    def finalize_transfer(self) -> bool:
        return bool(self._call("simulation_finalize_transfer"))

    def verify_flash_routine(self) -> bool:
        return bool(self._call("simulation_verify"))

    def return_to_normal_mode(self) -> bool:
        return bool(self._call("simulation_reset"))

    def send_tester_present(self) -> bool:
        return bool(self._call("simulation_tester_present"))

    def read_ecu_info(self) -> Dict[str, str]:
        return dict(self._call("simulation_ecu_info"))
