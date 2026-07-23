"""
Infrastructure Layer - Application Settings Manager

Manages persistent application configuration, window geometry, splitter positions,
theme selection, density mode, and recent hardware configurations using QSettings.
"""

from typing import List, Optional
from PySide6.QtCore import QSettings


class SettingsManager:
    """Centralized manager for application settings and user preferences."""

    _ORG_NAME = "Mackanized flasher"
    _APP_NAME = "Mackanized flasher Suite"
    _THEMES = {"dark", "oled", "light"}
    _DENSITY_MODES = {"standard", "compact"}

    def __init__(self):
        self._settings = QSettings(self._ORG_NAME, self._APP_NAME)

    @property
    def theme(self) -> str:
        value = str(self._settings.value("ui/theme", "dark"))
        return value if value in self._THEMES else "dark"

    @theme.setter
    def theme(self, value: str) -> None:
        value = value if value in self._THEMES else "dark"
        self._settings.setValue("ui/theme", value)
        self._settings.sync()

    @property
    def density_mode(self) -> str:
        value = str(self._settings.value("ui/density_mode", "standard"))
        return value if value in self._DENSITY_MODES else "standard"

    @density_mode.setter
    def density_mode(self, value: str) -> None:
        value = value if value in self._DENSITY_MODES else "standard"
        self._settings.setValue("ui/density_mode", value)
        self._settings.sync()

    @property
    def default_adapter_key(self) -> str:
        return str(self._settings.value("hardware/default_adapter", "mock"))

    @default_adapter_key.setter
    def default_adapter_key(self, value: str) -> None:
        self._settings.setValue("hardware/default_adapter", value)
        self._settings.sync()

    @property
    def j2534_dll_path(self) -> str:
        return str(self._settings.value("hardware/j2534_dll", ""))

    @j2534_dll_path.setter
    def j2534_dll_path(self, value: str) -> None:
        self._settings.setValue("hardware/j2534_dll", value)
        self._settings.sync()

    @property
    def baudrate(self) -> int:
        return int(self._settings.value("hardware/baudrate", 500000))

    @baudrate.setter
    def baudrate(self, value: int) -> None:
        self._settings.setValue("hardware/baudrate", int(value))
        self._settings.sync()

    @property
    def disable_preflight(self) -> bool:
        val = self._settings.value("safety/disable_preflight", True)
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)

    @disable_preflight.setter
    def disable_preflight(self, value: bool) -> None:
        self._settings.setValue("safety/disable_preflight", bool(value))
        self._settings.sync()

    @property
    def recent_files(self) -> List[str]:
        val = self._settings.value("history/recent_files", [])
        if isinstance(val, str):
            return [val] if val else []
        return list(val) if isinstance(val, list) else []

    def add_recent_file(self, filepath: str) -> None:
        files = [f for f in self.recent_files if f != filepath]
        files.insert(0, filepath)
        files = files[:10]
        self._settings.setValue("history/recent_files", files)
        self._settings.sync()

    def get_window_geometry(self) -> Optional[bytes]:
        val = self._settings.value("window/geometry")
        return val if isinstance(val, bytes) else None

    def save_window_geometry(self, geometry: bytes) -> None:
        self._settings.setValue("window/geometry", geometry)

    def get_window_state(self) -> Optional[bytes]:
        val = self._settings.value("window/state")
        return val if isinstance(val, bytes) else None

    def save_window_state(self, state: bytes) -> None:
        self._settings.setValue("window/state", state)
