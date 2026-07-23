"""Semantic simulator for Bosch EDC16C39."""

from __future__ import annotations

from typing import Optional

from adapters.base_adapter import BaseAdapter
from domain.cancellation import CancellationToken
from domain.edc16c39 import Edc16Area
from domain.errors import SecurityAccessError
from ecus.base_ecu import BaseECU
from protocols.base_protocol import DownloadParameters
from protocols.kwp2000.edc16c39_programming import Edc16C39ProgrammingCoordinator
from protocols.simulation.simulation_client import SimulationProtocolClient


class Edc16C39SimulationClient(
    Edc16C39ProgrammingCoordinator,
    SimulationProtocolClient,
):
    """Full semantic mock with the EDC16 reset/re-auth phase boundary."""

    def __init__(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        cancellation_token: Optional[CancellationToken] = None,
    ) -> None:
        super().__init__(adapter, ecu, cancellation_token=cancellation_token)
        self._edc16_download_active = False
        self._edc16_block_counter = 1

    def authenticate(self) -> bool:
        policy = self.ecu.SECURITY_POLICY
        seed = int(self._call(
            "simulation_edc16_request_seed",
            policy.request_level,
            policy.seed_length,
        ))
        key = self.ecu.calculate_key(seed)
        accepted = bool(self._call(
            "simulation_edc16_submit_key",
            policy.request_level + 1,
            key,
            key,
        ))
        if not accepted:
            raise SecurityAccessError(
                "EDC16 virtual ECU rejected the level-05 key",
                level=policy.request_level,
            )
        return True

    def enter_programming_mode(self) -> bool:
        self._cancel.check("EDC16 simulation session entry")
        return bool(self._call("simulation_edc16_start_session"))

    def prepare_read_session(self) -> bool:
        return self.authenticate() and self.enter_programming_mode() and self.send_tester_present()

    def prepare_programming_session(self) -> bool:
        return self.prepare_read_session()

    def _edc16_erase_area(self, area: Edc16Area) -> bool:
        return bool(self._call("simulation_edc16_erase", area.start, area.size))

    def _edc16_request_download_area(self, area: Edc16Area) -> DownloadParameters:
        maximum = int(self._call("simulation_edc16_begin_download", area.start, area.size))
        self._edc16_download_active = True
        self._edc16_block_counter = 1
        return DownloadParameters(max_request_bytes=maximum, raw_response=b"EDC16-SIMULATED")

    def write_memory_block(self, address: int, data: bytes) -> bool:
        if not self._edc16_download_active:
            return super().write_memory_block(address, data)
        counter = self._edc16_block_counter
        accepted = bool(self._call(
            "simulation_edc16_transfer",
            address,
            counter,
            bytes(data),
        ))
        if accepted:
            self._edc16_block_counter = (counter + 1) & 0xFF
        return accepted

    def finalize_transfer(self) -> bool:
        if not self._edc16_download_active:
            return super().finalize_transfer()
        accepted = bool(self._call("simulation_edc16_finalize"))
        if accepted:
            self._edc16_download_active = False
        return accepted

    def return_to_normal_mode(self) -> bool:
        self._edc16_download_active = False
        return bool(self._call("simulation_edc16_reset"))

    def _edc16_wait_reconnect(self) -> bool:
        return bool(self._call("simulation_edc16_wait_reconnect"))
