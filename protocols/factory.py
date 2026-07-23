"""Protocol client construction selected from ECU metadata."""

from typing import Protocol

from adapters.base_adapter import BaseAdapter
from domain.cancellation import CancellationToken
from domain.protocol_metadata import ProtocolFamily
from ecus.base_ecu import BaseECU
from protocols.base_protocol import ProtocolClient


class ProtocolClientFactory(Protocol):
    def create(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        cancellation_token: CancellationToken,
    ) -> ProtocolClient: ...


class DefaultProtocolClientFactory:
    def create(
        self,
        adapter: BaseAdapter,
        ecu: BaseECU,
        cancellation_token: CancellationToken,
    ) -> ProtocolClient:
        metadata = ecu.protocol_metadata
        profile = getattr(ecu, "PROFILE", None)
        if profile is not None:
            from domain.trionic import TrionicGeneration
            if getattr(adapter, "is_simulation", False) and not getattr(adapter, "is_replay", False):
                from protocols.simulation.trionic_simulation_client import TrionicSimulationClient
                return TrionicSimulationClient(adapter, ecu, cancellation_token=cancellation_token)
            if profile.generation in {TrionicGeneration.T5_2, TrionicGeneration.T5_5}:
                from protocols.trionic.t5_client import Trionic5Client
                return Trionic5Client(adapter, ecu, cancellation_token=cancellation_token)
            if profile.generation is TrionicGeneration.T7:
                from protocols.trionic.t7_client import Trionic7Client
                return Trionic7Client(adapter, ecu, cancellation_token=cancellation_token)
            if profile.generation is TrionicGeneration.T8:
                from protocols.trionic.t8_client import Trionic8Client
                return Trionic8Client(adapter, ecu, cancellation_token=cancellation_token)
        if metadata.family is ProtocolFamily.GMLAN:
            from protocols.gmlan.gmlan_client import GMLANClient
            return GMLANClient(adapter, ecu, cancellation_token=cancellation_token)
        if getattr(adapter, "is_simulation", False):
            if metadata.family is ProtocolFamily.KWP2000_ISOTP:
                from protocols.simulation.edc16c39_simulation_client import Edc16C39SimulationClient
                return Edc16C39SimulationClient(adapter, ecu, cancellation_token=cancellation_token)
            from protocols.simulation.simulation_client import SimulationProtocolClient
            return SimulationProtocolClient(adapter, ecu, cancellation_token=cancellation_token)
        if metadata.family is ProtocolFamily.KWP2000_ISOTP:
            from protocols.kwp2000.edc16c39_client import Edc16C39Client
            return Edc16C39Client(adapter, ecu, cancellation_token=cancellation_token)
        from protocols.gmlan.gmlan_client import GMLANClient
        return GMLANClient(adapter, ecu, cancellation_token=cancellation_token)
