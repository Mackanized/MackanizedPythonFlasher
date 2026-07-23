"""
Domain Layer - Cancellation Token

Thread-safe cooperative cancellation primitive for flash operations.
"""

import threading
from contextlib import contextmanager
from typing import Optional


class CancellationToken:
    """Thread-safe cooperative cancellation flag.

    Workers call :meth:`cancel` from any thread (e.g. the GUI thread) and the
    long-running operation checks :meth:`is_cancelled` at safe points (e.g.
    between flash blocks).  This replaces bare ``bool`` flags which lack a
    memory barrier and are not idiomatic for cross-thread signalling.
    """

    __slots__ = ("_event", "_reason", "_lock", "_defer_count")

    def __init__(self) -> None:
        self._event = threading.Event()
        self._reason: Optional[str] = None
        self._lock = threading.RLock()
        self._defer_count = 0

    def cancel(self, reason: str = "User requested cancellation") -> None:
        with self._lock:
            self._reason = reason
            self._event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> Optional[str]:
        return self._reason

    @property
    def should_interrupt(self) -> bool:
        with self._lock:
            return self._event.is_set() and self._defer_count == 0

    def reset(self) -> None:
        with self._lock:
            self._event.clear()
            self._reason = None

    def check(self, action: str = "") -> bool:
        """Return True if cancelled, logging the action being aborted."""
        return self.should_interrupt

    @contextmanager
    def defer_interrupts(self):
        """Latch cancellation while an ECU is in an unsafe programming phase."""
        with self._lock:
            self._defer_count += 1
        try:
            yield
        finally:
            with self._lock:
                self._defer_count = max(0, self._defer_count - 1)
