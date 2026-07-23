"""
Application Layer - Flasher Commands

Concrete application commands orchestrating hardware connection, ECU reading,
flash programming, backup, and UDS diagnostics validation.
"""

from typing import Tuple
from application.commands.base_command import ICommand
from application.state.app_state import ApplicationState
from adapters.base_adapter import BaseAdapter
from ecus.base_ecu import BaseECU


class ConnectAdapterCommand(ICommand):
    """Command to connect or disconnect a hardware adapter."""

    def __init__(self, state: ApplicationState, adapter: BaseAdapter, adapter_key: str):
        self._state = state
        self._adapter = adapter
        self._adapter_key = adapter_key

    @property
    def name(self) -> str:
        return f"Connect Adapter ({self._adapter_key})"

    def validate(self) -> Tuple[bool, str]:
        if self._adapter is None:
            return False, "Hardware adapter instance is null."
        v = self._state.voltage
        if v is not None and v < 11.0:
            return False, f"Battery voltage too low ({v}V < 11.0V)."
        return True, ""

    def execute(self) -> bool:
        valid, msg = self.validate()
        if not valid:
            self._state.log_error("Hardware", f"Connect failed: {msg}")
            return False

        try:
            res = self._adapter.connect()
            if res:
                self._state.set_adapter_state(self._adapter_key, True)
                self._state.log_info("Hardware", f"Adapter '{self._adapter_key}' connected successfully.")
                return True
            else:
                self._state.log_error("Hardware", f"Adapter '{self._adapter_key}' failed to initialize.")
                return False
        except (OSError, RuntimeError) as e:
            self._state.log_error("Hardware", f"Adapter connection exception: {str(e)}")
            return False


class ValidateFlashCommand(ICommand):
    """Legacy validation command.

    This command cannot authorize a write because it has no live identity,
    adapter, voltage-source freshness, backup evidence, or operator approval.
    Use ``ProgrammingPreflight`` to obtain an ``ApprovedProgrammingPlan``.
    """

    def __init__(self, state: ApplicationState, ecu: BaseECU, binary_data: bytes):
        self._state = state
        self._ecu = ecu
        self._binary_data = binary_data

    @property
    def name(self) -> str:
        return "Validate Calibration File"

    def validate(self) -> Tuple[bool, str]:
        return False, "Legacy validation cannot authorize programming; use ProgrammingPreflight."

    def execute(self) -> bool:
        valid, msg = self.validate()
        if not valid:
            self._state.log_error("Validation", f"Flash validation failed: {msg}")
            return False

        self._state.log_info("Validation", f"Binary calibration file validated ({len(self._binary_data)} bytes). Ready to flash.")
        return True
