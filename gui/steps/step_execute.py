from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .base_step import BaseStep
from ..can_trace_panel import CANTracePanel


class StepExecute(BaseStep):
    """Step 4: Execute operation with progress, log, and CAN trace."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        self._title = QLabel("Ready")
        self._title.setObjectName("titleLabel")
        layout.addWidget(self._title)

        self._status = QLabel("")
        self._status.setObjectName("statusLabel")
        layout.addWidget(self._status)

        layout.addSpacing(8)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        layout.addSpacing(8)

        self._log = QLabel("Log:")
        self._log.setObjectName("statusLabel")
        layout.addWidget(self._log)

        from PySide6.QtWidgets import QPlainTextEdit
        self._log_text = QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMaximumBlockCount(500)
        layout.addWidget(self._log_text)

        # CAN trace panel
        self._can_trace = CANTracePanel()
        layout.addWidget(self._can_trace)

        # ECU info table (for info operation)
        self._info_table = QTableWidget(0, 2)
        self._info_table.setHorizontalHeaderLabels(["Field", "Value"])
        self._info_table.setVisible(False)
        layout.addWidget(self._info_table)

        layout.addStretch()

        # Cancel button
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("dangerBtn")
        self._cancel_btn.setMinimumHeight(44)
        self._cancel_btn.clicked.connect(self._cancel)
        self._cancel_btn.setVisible(False)
        layout.addWidget(self._cancel_btn)

    def start_worker(self, worker, operation: str):
        self._worker = worker
        self._can_trace.install_logger()

        worker.progress.connect(self._on_progress)
        worker.log_message.connect(self._on_log)
        worker.finished_ok.connect(self._on_finished_ok)
        worker.finished_error.connect(self._on_finished_error)
        worker.ecu_info_ready.connect(self._on_ecu_info)

        self._title.setText(f"{'Reading' if operation == 'read' else 'Writing' if operation == 'write' else 'Reading ECU Info'}...")
        self._status.setText("Connecting...")
        self._progress.setValue(0)
        self._log_text.clear()
        self._can_trace.clear()
        self._info_table.setVisible(False)
        self._cancel_btn.setVisible(True)

        self.back_enabled.emit(False)
        self.next_enabled.emit(False)

        worker.start()

    def _on_progress(self, pct: float, msg: str):
        self._progress.setValue(int(pct))
        self._status.setText(msg)

    def _on_log(self, msg: str):
        self._log_text.appendPlainText(msg)

    def _on_finished_ok(self, msg: str):
        self._title.setText("Complete")
        self._status.setText(msg)
        self._progress.setValue(100)
        self._cancel_btn.setVisible(False)
        self.back_enabled.emit(True)
        self.next_enabled.emit(False)
        self._can_trace.remove_logger()
        self._worker = None

    def _on_finished_error(self, msg: str):
        self._title.setText("Error")
        self._status.setText(msg)
        self._cancel_btn.setVisible(False)
        self.back_enabled.emit(True)
        self.next_enabled.emit(False)
        self._can_trace.remove_logger()
        self._worker = None

    def _on_ecu_info(self, info: dict):
        self._info_table.setRowCount(len(info))
        self._info_table.setVisible(True)
        for i, (key, val) in enumerate(info.items()):
            self._info_table.setItem(i, 0, QTableWidgetItem(key))
            self._info_table.setItem(i, 1, QTableWidgetItem(str(val)))
        self._info_table.resizeColumnsToContents()

    def _cancel(self):
        if self._worker and self._worker.isRunning():
            self._worker.requestInterruption()
            self._status.setText("Cancelling...")

    def on_enter(self):
        self.next_enabled.emit(False)