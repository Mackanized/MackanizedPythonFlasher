"""Pytest bootstrap for Qt-dependent tests."""

import os
import sys


# In non-GUI automation on macOS, Qt's Cocoa backend can abort the whole Python
# process during QApplication startup. Use the offscreen backend for tests unless
# the caller explicitly selected another platform.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


_qt_app = None


def pytest_configure(config):
    """Create one offscreen QApplication before any widget tests run."""
    global _qt_app
    from PySide6.QtWidgets import QApplication

    _qt_app = QApplication.instance() or QApplication(sys.argv)
