from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from adapters.kvaser import KvaserAdapter
from adapters.j2534 import J2534Adapter
from gui.styles import apply_dark_theme
from gui.worker import FlasherWorker
from gui.steps.step_adapter import StepAdapter
from gui.steps.step_ecu import StepECU
from gui.steps.step_operation import StepOperation
from gui.steps.step_execute import StepExecute


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECU Flasher")
        self.setMinimumSize(720, 760)
        self.resize(720, 760)

        self._adapter = None
        self._ecu = None
        self._worker = None

        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Header
        header = QLabel("ECU Flasher")
        header.setObjectName("titleLabel")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Step indicator
        self._step_label = QLabel("Step 1 of 4")
        self._step_label.setObjectName("subtitleLabel")
        self._step_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._step_label)

        # Stacked steps
        self._stack = QStackedWidget()
        layout.addWidget(self._stack)

        self._step_adapter = StepAdapter()
        self._step_ecu = StepECU()
        self._step_operation = StepOperation()
        self._step_execute = StepExecute()

        for step in [self._step_adapter, self._step_ecu, self._step_operation, self._step_execute]:
            self._stack.addWidget(step)

        # Navigation buttons
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(12)

        self._back_btn = QPushButton("Back")
        self._back_btn.setMinimumHeight(48)
        self._back_btn.setMinimumWidth(120)
        self._back_btn.clicked.connect(self._go_back)
        self._back_btn.setVisible(False)
        nav_layout.addWidget(self._back_btn)

        nav_layout.addStretch()

        self._next_btn = QPushButton("Next")
        self._next_btn.setObjectName("primaryBtn")
        self._next_btn.setMinimumHeight(48)
        self._next_btn.setMinimumWidth(160)
        self._next_btn.clicked.connect(self._go_next)
        nav_layout.addWidget(self._next_btn)

        layout.addLayout(nav_layout)

        # Connect step signals
        self._step_adapter.next_enabled.connect(self._on_next_enabled)
        self._step_ecu.next_enabled.connect(self._on_next_enabled)
        self._step_operation.next_enabled.connect(self._on_next_enabled)
        self._step_execute.back_enabled.connect(self._on_back_enabled)
        self._step_execute.next_enabled.connect(self._on_next_enabled)

        self._current_step = 0
        self._update_step()

    # ── Navigation ───────────────────────────────────────────────────

    def _go_next(self):
        if self._current_step == 0:
            self._create_adapter()
            self._step_ecu.on_enter()
        elif self._current_step == 1:
            self._create_ecu()
            self._step_operation.set_ecu(self._ecu)
            self._step_operation.on_enter()
        elif self._current_step == 2:
            self._start_operation()
            return  # Execute step handles its own flow

        self._current_step += 1
        self._update_step()

    def _go_back(self):
        if self._current_step > 0:
            self._current_step -= 1
            self._update_step()

    def _update_step(self):
        self._stack.setCurrentIndex(self._current_step)
        total = 4
        self._step_label.setText(f"Step {self._current_step + 1} of {total}")

        self._back_btn.setVisible(self._current_step > 0)
        self._next_btn.setVisible(self._current_step < 3)
        self._next_btn.setEnabled(False)

        # Re-evaluate enabled state
        step = self._stack.currentWidget()
        if hasattr(step, "on_enter"):
            step.on_enter()

    def _on_next_enabled(self, enabled: bool):
        self._next_btn.setEnabled(enabled)

    def _on_back_enabled(self, enabled: bool):
        self._back_btn.setEnabled(enabled)

    # ── Object creation ──────────────────────────────────────────────

    def _create_adapter(self):
        key = self._step_adapter.get_adapter_key()
        if key == "kvaser":
            self._adapter = KvaserAdapter()
        else:
            dll_path = self._step_adapter.get_j2534_dll()
            self._adapter = J2534Adapter(dll_path=dll_path)

    def _create_ecu(self):
        ecu_class = self._step_ecu.get_ecu_class()
        if ecu_class:
            self._ecu = ecu_class()

    # ── Operation execution ──────────────────────────────────────────

    def _start_operation(self):
        operation = self._step_operation.get_operation()
        region = self._step_operation.get_region()
        filename = self._step_operation.get_filename()

        self._current_step = 3
        self._update_step()

        if operation == "info":
            self._worker = FlasherWorker(self._adapter, self._ecu)
            self._worker.set_info()
            self._step_execute.start_worker(self._worker, "info")
        elif operation == "read":
            self._worker = FlasherWorker(self._adapter, self._ecu)
            self._worker.set_read(region)
            self._step_execute.start_worker(self._worker, "read")
        elif operation == "write":
            self._worker = FlasherWorker(self._adapter, self._ecu)
            self._worker.set_write(region, filename)
            self._step_execute.start_worker(self._worker, "write")