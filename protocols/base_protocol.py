"""
Abstract Protocol Client Interface for ECU Diagnostic Operations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Protocol, Tuple, runtime_checkable
from adapters.base_adapter import BaseAdapter
from ecus.base_ecu import BaseECU


@dataclass(frozen=True)
class DownloadParameters:
    """Negotiated ECU transfer contract returned by RequestDownload."""

    max_request_bytes: int
    raw_response: bytes

    def max_data_bytes(self, request_overhead: int) -> int:
        available = self.max_request_bytes - request_overhead
        if available <= 0:
            raise ValueError("ECU-negotiated transfer size cannot fit the request header")
        return available


class ProtocolClient(ABC):
    """Abstract protocol interface defining ECU diagnostic & flashing operations."""

    def __init__(self, adapter: BaseAdapter, ecu: BaseECU):
        self.adapter = adapter
        self.ecu = ecu

    @abstractmethod
    def enter_programming_mode(self) -> bool:
        """Enter programming/diagnostic session."""
        pass

    @abstractmethod
    def authenticate(self) -> bool:
        """Perform security access authentication."""
        pass

    @abstractmethod
    def prepare_programming_session(self) -> bool:
        """Execute every mandatory ECU-family transition before erase."""
        pass

    def prepare_read_session(self) -> bool:
        """Execute the ECU-family read-session sequence.

        Most supported GMLAN controllers enter a diagnostic session before
        SecurityAccess.  Families whose trace-backed sequence differs (for
        example EDC16C39) override this method instead of forcing that
        ordering into the application layer.
        """
        return self.enter_programming_mode() and self.authenticate()

    @abstractmethod
    def read_memory_by_address(self, address: int, size: int, timeout_s: float = 5.0) -> Optional[bytes]:
        """Read memory chunk from ECU."""
        pass

    @abstractmethod
    def request_download(self, size: int) -> DownloadParameters:
        """Request flash programming download / initiate erase."""
        pass

    @abstractmethod
    def write_memory_block(self, address: int, data: bytes) -> bool:
        """Transfer a block of flash data to ECU."""
        pass

    @abstractmethod
    def finalize_transfer(self) -> bool:
        """Explicitly close the transfer before ECU-side verification."""
        pass

    @abstractmethod
    def verify_flash_routine(self) -> bool:
        """Execute ECU post-flash verification routine or check programmed state."""
        pass

    @abstractmethod
    def return_to_normal_mode(self) -> bool:
        """Reset ECU and restore normal communication mode."""
        pass

    @abstractmethod
    def send_tester_present(self) -> bool:
        """Send keep-alive TesterPresent ping."""
        pass

    @abstractmethod
    def read_ecu_info(self) -> Dict[str, str]:
        """Read ECU identification parameters."""
        pass


@runtime_checkable
class ManagedProgrammingClient(Protocol):
    """Optional ECU-family coordinator for non-flat programming workflows."""

    def manages_programming_region(self, region_name: str) -> bool:
        """Return whether the named region requires this family coordinator."""
        ...

    def execute_managed_programming(
        self,
        *,
        region_name: str,
        region_start: int,
        data: bytes,
        progress_callback: Callable[[float, str], None],
    ) -> bool:
        """Execute an ECU-specific, internally verified programming plan."""
        ...
