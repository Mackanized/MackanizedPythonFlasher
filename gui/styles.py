DARK_QSS = """
/* ── Global ──────────────────────────────────────────────────────── */
QWidget {
    background-color: #1a1a2e;
    color: #e0e0e0;
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", sans-serif;
    font-size: 15px;
}

QMainWindow {
    background-color: #1a1a2e;
}

/* ── Buttons ─────────────────────────────────────────────────────── */
QPushButton {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 10px;
    padding: 14px 24px;
    min-height: 44px;
    font-weight: 600;
    color: #e0e0e0;
}
QPushButton:hover {
    background-color: #0f3460;
    border-color: #1a5276;
}
QPushButton:pressed {
    background-color: #1a5276;
}
QPushButton:disabled {
    background-color: #111122;
    border-color: #222244;
    color: #555566;
}
QPushButton#primaryBtn {
    background-color: #0f3460;
    border-color: #3498db;
    color: #ffffff;
    font-size: 16px;
    min-height: 52px;
}
QPushButton#primaryBtn:hover {
    background-color: #1a5276;
    border-color: #5dade2;
}
QPushButton#primaryBtn:pressed {
    background-color: #2471a3;
}
QPushButton#dangerBtn {
    background-color: #2e1010;
    border-color: #8b2020;
    color: #ff6666;
}
QPushButton#dangerBtn:hover {
    background-color: #4b1818;
    border-color: #cc3333;
}

/* ── Card buttons (ECU selection) ────────────────────────────────── */
QPushButton#cardBtn {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 14px;
    padding: 20px;
    min-height: 72px;
    text-align: left;
    font-size: 16px;
}
QPushButton#cardBtn:hover {
    background-color: #1c2848;
    border-color: #3498db;
}
QPushButton#cardBtn:checked {
    background-color: #0f3460;
    border-color: #3498db;
    border-width: 3px;
}

/* ── Labels ──────────────────────────────────────────────────────── */
QLabel#titleLabel {
    font-size: 22px;
    font-weight: 700;
    color: #ffffff;
    padding: 8px 0;
}
QLabel#subtitleLabel {
    font-size: 13px;
    color: #8888aa;
    padding: 4px 0;
}
QLabel#statusLabel {
    font-size: 14px;
    color: #aaaacc;
}
QLabel#successLabel {
    color: #2ecc71;
    font-weight: 600;
}
QLabel#warningLabel {
    color: #f39c12;
    font-weight: 600;
}
QLabel#errorLabel {
    color: #e74c3c;
    font-weight: 600;
}

/* ── Progress bar ────────────────────────────────────────────────── */
QProgressBar {
    border: 2px solid #0f3460;
    border-radius: 8px;
    text-align: center;
    min-height: 32px;
    font-size: 14px;
    font-weight: 600;
    color: #ffffff;
    background-color: #111122;
}
QProgressBar::chunk {
    background-color: #3498db;
    border-radius: 6px;
}

/* ── Text areas (log / CAN trace) ────────────────────────────────── */
QPlainTextEdit {
    background-color: #0d1117;
    border: 1px solid #1e2a3a;
    border-radius: 6px;
    font-family: "Cascadia Code", "Consolas", "Courier New", monospace;
    font-size: 12px;
    color: #c0c0d0;
    padding: 4px;
}

/* ── Group boxes ─────────────────────────────────────────────────── */
QGroupBox {
    border: 2px solid #0f3460;
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #8888aa;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 6px;
}

/* ── Combo boxes ─────────────────────────────────────────────────── */
QComboBox {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    padding: 10px 16px;
    min-height: 40px;
    font-size: 15px;
}
QComboBox:hover {
    border-color: #3498db;
}
QComboBox::drop-down {
    border: none;
    width: 36px;
}
QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    selection-background-color: #0f3460;
    padding: 8px;
    min-height: 40px;
}

/* ── Scroll bars ─────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #111122;
    width: 12px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #0f3460;
    min-height: 30px;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover {
    background: #1a5276;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ── Line edits ──────────────────────────────────────────────────── */
QLineEdit {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    padding: 10px 16px;
    min-height: 40px;
    font-size: 15px;
    color: #e0e0e0;
}
QLineEdit:focus {
    border-color: #3498db;
}

/* ── Table ───────────────────────────────────────────────────────── */
QTableWidget {
    background-color: #16213e;
    border: 1px solid #1e2a3a;
    border-radius: 8px;
    gridline-color: #1e2a3a;
    font-size: 14px;
}
QTableWidget::item {
    padding: 8px 12px;
    min-height: 32px;
}
QTableWidget::item:selected {
    background-color: #0f3460;
}
QHeaderView::section {
    background-color: #111122;
    border: none;
    padding: 8px 12px;
    font-weight: 600;
    color: #8888aa;
}

/* ── Checkboxes ──────────────────────────────────────────────────── */
QCheckBox {
    spacing: 10px;
    font-size: 15px;
    min-height: 44px;
}
QCheckBox::indicator {
    width: 24px;
    height: 24px;
    border-radius: 6px;
    border: 2px solid #0f3460;
    background-color: #16213e;
}
QCheckBox::indicator:checked {
    background-color: #3498db;
    border-color: #3498db;
}
"""

def apply_dark_theme(app):
    app.setStyleSheet(DARK_QSS)