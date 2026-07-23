"""
Application Layer - Session Manager.

Encapsulates programming-session entry, security access, keep-alive, and
session teardown.  Extracted from the former ``ECUFlasher`` god-class.
"""

from typing import Optional
from protocols.base_protocol import ProtocolClient
from domain.cancellation import CancellationToken
from domain.clock import Clock, SystemClock
from domain.errors import SessionError, SecurityAccessError, NotConnectedError
from logger import app_logger


class SessionManager:
    """Manages ECU diagnostic session lifecycle."""

    KEEPALIVE_INTERVAL_S = 2.0

    def __init__(
        self,
        protocol: ProtocolClient,
        cancellation_token: Optional[CancellationToken] = None,
        clock: Optional[Clock] = None,
    ):
        self._protocol = protocol
        self._cancel = cancellation_token or CancellationToken()
        self._clock = clock or SystemClock()
        self._last_tp_time: float = 0.0

    @property
    def protocol(self) -> ProtocolClient:
        return self._protocol

    def enter_read_session(self) -> bool:
        """Execute the ECU-family read-session preparation sequence."""
        app_logger.info("Waking up ECU for read...")
        prepare = getattr(self._protocol, "prepare_read_session", None)
        prepared = (
            bool(prepare())
            if callable(prepare)
            else bool(self._protocol.enter_programming_mode() and self._protocol.authenticate())
        )
        if not prepared:
            app_logger.error("Read-session preparation denied.")
            return False
        app_logger.info("Read session ready.")
        self._last_tp_time = self._clock.monotonic()
        return True

    def enter_write_session(self) -> bool:
        """Authenticate, enter programming mode, and send initial tester present."""
        app_logger.info("Executing mandatory ECU-family programming-session plan...")
        if not self._protocol.prepare_programming_session():
            app_logger.error("Programming-session plan failed.")
            return False
        self._last_tp_time = self._clock.monotonic()
        app_logger.info("Write session ready.")
        return True

    def keep_alive(self) -> None:
        """Send TesterPresent if the keep-alive interval has elapsed."""
        now = self._clock.monotonic()
        if now - self._last_tp_time >= self.KEEPALIVE_INTERVAL_S:
            self._protocol.send_tester_present()
            self._last_tp_time = now

    def return_to_normal(self) -> bool:
        """Reset the ECU to normal mode. Best-effort, logs errors."""
        try:
            return self._protocol.return_to_normal_mode()
        except (OSError, RuntimeError) as e:
            app_logger.debug(f"return_to_normal cleanup: {e}")
            return False
