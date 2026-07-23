"""Qt startup helpers for desktop entry points."""

from __future__ import annotations

import os
import sys


def is_non_gui_automation() -> bool:
    """Return True when launching Qt's GUI backend is known to be unsafe."""
    if sys.platform != "darwin":
        return False
    if os.environ.get("PYTHONFLASHER_FORCE_GUI") == "1":
        return False
    if os.environ.get("QT_QPA_PLATFORM"):
        return False
    return os.environ.get("CODEX_CI") == "1" or os.environ.get("CI") == "1"


def qt_startup_error() -> str:
    return (
        "Qt GUI startup was skipped because this process is running under "
        "non-GUI automation on macOS. Launch the desktop app from a normal "
        "user session, set QT_QPA_PLATFORM=offscreen for tests, or set "
        "PYTHONFLASHER_FORCE_GUI=1 to override."
    )
