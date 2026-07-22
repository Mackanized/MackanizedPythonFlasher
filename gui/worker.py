import logging
from typing import Optional

from PySide6.QtCore import QThread, Signal

from adapters.base_adapter import BaseAdapter
from adapters.kvaser import KvaserAdapter
from adapters.j2534 import J2534Adapter
from ecus.base_ecu import BaseECU
from flasher import ECUFlasher


class _GuiLogHandler(logging.Handler):
    """Captures log records and forwards them to the GUI via signal."""
    def __init__(self, signal):
        super().__init__()
        self._signal = signal

    def emit(self, record):
        try:
            msg = self.format(record)
            self._signal.emit(msg)
        except Exception:
            pass


class FlasherWorker(QThread):
    """Runs ECUFlasher operations in a background thread."""

    progress = Signal(float, str)
    log_message = Signal(str)
    can_message = Signal(str, str, str)  # direction, can_id, data_hex
    finished_ok = Signal(str)       # result message
    finished_error = Signal(str)    # error message
    ecu_info_ready = Signal(dict)   # ECU info dict

    def __init__(self, adapter: BaseAdapter, ecu: BaseECU, parent=None):
        super().__init__(parent)
        self.adapter = adapter
        self.ecu = ecu
        self._operation: str = ""        # "read", "write", "info"
        self._region: str = ""
        self._filename: str = ""
        self._flasher: Optional[ECUFlasher] = None
        self._can_handler: Optional[logging.Handler] = None
        self._app_handler: Optional[logging.Handler] = None

    # ── Operation setters ────────────────────────────────────────────

    def set_read(self, region: str, output_dir: str = "."):
        self._operation = "read"
        self._region = region
        self._filename = output_dir

    def set_write(self, region: str, filename: str):
        self._operation = "write"
        self._region = region
        self._filename = filename

    def set_info(self):
        self._operation = "info"

    # ── Thread entry point ───────────────────────────────────────────

    def run(self):
        self._install_log_handlers()

        try:
            self._flasher = ECUFlasher(
                self.adapter,
                self.ecu,
                progress_callback=lambda pct, msg: (
                    self.progress.emit(pct, msg)
                ),
            )

            if not self._flasher.connect():
                self.finished_error.emit("Failed to connect adapter.")
                return

            if self._operation == "info":
                info = self._flasher.read_ecu_info()
                self.ecu_info_ready.emit(info)
                self.finished_ok.emit("ECU info read complete.")
                return

            if self._operation == "read":
                filename = self._flasher.read_to_file(self._region, self._filename)
                self.finished_ok.emit(f"Saved to: {filename}")
                return

            if self._operation == "write":
                if self._flasher.write_from_file(self._region, self._filename):
                    self.finished_ok.emit("Flash complete. ECU reset.")
                else:
                    self.finished_error.emit("Write failed. Check flasher.log.")
                return

        except Exception as e:
            self.finished_error.emit(str(e))
        finally:
            if self._flasher:
                self._flasher.disconnect()
            self._remove_log_handlers()

    # ── Log handler plumbing ─────────────────────────────────────────

    def _install_log_handlers(self):
        from logger import app_logger, can_logger

        self._app_handler = _GuiLogHandler(self.log_message)
        self._app_handler.setLevel(logging.DEBUG)
        self._app_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(message)s", datefmt="%H:%M:%S")
        )
        app_logger.addHandler(self._app_handler)

    def _remove_log_handlers(self):
        from logger import app_logger
        if self._app_handler:
            app_logger.removeHandler(self._app_handler)
            self._app_handler = None