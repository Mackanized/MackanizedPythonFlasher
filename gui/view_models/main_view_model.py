"""
Presentation Layer - Main ViewModel

MVVM ViewModel orchestrating interactions between ApplicationState, FlasherService,
TelemetryEngine, and presentation components.
Exposes observable properties and executes commands.
"""

from PySide6.QtCore import QObject, Signal
from application.state.app_state import ApplicationState
from application.services.flasher_service import FlasherService
from infrastructure.telemetry import TelemetryEngine


class MainViewModel(QObject):
    """ViewModel coordinating application state and UI views."""

    def __init__(
        self,
        app_state: ApplicationState,
        flasher_service: FlasherService,
        telemetry: TelemetryEngine,
        parent=None
    ):
        super().__init__(parent)
        self.state = app_state
        self.flasher = flasher_service
        self.telemetry = telemetry

    def connect_hardware(self) -> None:
        if self.state.is_connected:
            self.flasher.disconnect_adapter()
        else:
            self.flasher.connect_adapter()

    def start_read(self, region: str = "full") -> None:
        self.flasher.start_read_operation(region_name=region)

    def start_write(
        self,
        file_path: str,
        region: str = "full",
        operator_confirmed: bool = False,
        backup_verified: bool = False,
    ) -> None:
        self.flasher.start_write_operation(
            file_path=file_path,
            region_name=region,
            operator_confirmed=operator_confirmed,
            backup_verified=backup_verified,
        )

    def start_info(self) -> None:
        self.flasher.start_info_operation()

    def emergency_stop(self) -> None:
        self.flasher.cancel_operation()
        self.state.log_error("Emergency", "EMERGENCY STOP TRIGGERED BY OPERATOR!")
