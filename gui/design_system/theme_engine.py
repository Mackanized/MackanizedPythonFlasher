"""
Presentation Layer - Mackanized flasher V1 Theme Engine & QSS Generator

Generates calm, elegant desktop QSS for Mackanized flasher V1:
- Dark Slate Canvas (#181A20, #20232B, #292C36)
- 6px / 8px Control Radii & Soft Dividers (#2D323E)
- Precision Blue Accent Buttons & Pill Badges
- Quiet Thin Scrollbars & Task Navigation Rail
"""

from gui.design_system.tokens import ColorTokens, TypographyTokens


class ThemeEngine:
    """Generates Mackanized flasher V1 QSS Stylesheet."""

    @staticmethod
    def get_stylesheet(theme_name: str = "dark", density: str = "compact") -> str:
        colors = ColorTokens()
        typo = TypographyTokens()

        if theme_name == "workshop":
            colors = ColorTokens(
                canvas_base="#000000",
                surface_card="#0D0E12",
                surface_control="#1A1C24",
                surface_hover="#282C38",
                border_subtle="#3D4354",
                border_default="#525A70",
                text_primary="#FFFFFF",
                accent_primary="#3B82F6"
            )

        qss = f"""
        /* ── Canvas & Core Reset ─────────────────────────────────── */
        QWidget {{
            background-color: {colors.surface_card};
            color: {colors.text_primary};
            font-family: {typo.font_family_main};
            font-size: 12px;
            selection-background-color: {colors.accent_primary};
            selection-color: {colors.text_on_accent};
        }}

        QMainWindow {{
            background-color: {colors.canvas_base};
        }}

        QSplitter::handle {{
            background-color: transparent;
            margin: 0px;
        }}

        QSplitter::handle:hover {{
            background-color: {colors.accent_primary};
        }}

        /* ── Dock Windows ─────────────────────────────────────────── */
        QDockWidget {{
            font-weight: 600;
            font-size: 11px;
            border: none;
        }}

        QDockWidget::title {{
            background-color: {colors.canvas_base};
            color: {colors.text_secondary};
            padding: 6px 10px;
            border: none;
        }}

        /* ── Buttons & Action Triggers ───────────────────────────── */
        QPushButton, QToolButton {{
            background-color: {colors.surface_control};
            color: {colors.text_primary};
            border: none;
            border-radius: 6px;
            padding: 4px 12px;
            font-weight: 500;
            font-size: 11px;
            min-height: 24px;
        }}

        QPushButton:hover, QToolButton:hover {{
            background-color: {colors.surface_hover};
            border: none;
        }}

        QPushButton:pressed, QToolButton:pressed {{
            background-color: {colors.surface_pressed};
            border: none;
        }}

        QPushButton:focus, QToolButton:focus {{
            border: none;
            outline: none;
        }}

        QPushButton#primaryBtn {{
            background-color: {colors.accent_primary};
            color: {colors.text_on_accent};
            border: none;
            font-weight: 600;
        }}

        QPushButton#primaryBtn:hover {{
            background-color: {colors.accent_hover};
            border: none;
        }}

        QPushButton#warningBtn {{
            background-color: {colors.warning_soft};
            color: {colors.warning_text};
            border: none;
            font-weight: 600;
        }}

        QPushButton#warningBtn:hover {{
            background-color: {colors.warning_border};
            color: #FFFFFF;
            border: none;
        }}

        QPushButton#dangerBtn {{
            background-color: {colors.danger_soft};
            color: {colors.danger_text};
            border: none;
            font-weight: 600;
        }}

        /* ── Form Inputs ─────────────────────────────────────────── */
        QLineEdit, QComboBox, QSpinBox {{
            background-color: {colors.canvas_base};
            color: {colors.text_primary};
            border: none;
            border-radius: 6px;
            padding: 4px 10px;
            min-height: 24px;
            font-size: 11px;
        }}

        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
            border: none;
        }}

        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}

        /* ── Tables & Data Grids ─────────────────────────────────── */
        QTableView, QTreeView, QListView, QTableWidget {{
            background-color: {colors.canvas_base};
            alternate-background-color: {colors.surface_card};
            gridline-color: transparent;
            border: none;
            border-radius: 6px;
            font-size: 11px;
        }}

        QHeaderView::section {{
            background-color: {colors.surface_card};
            color: {colors.text_secondary};
            padding: 5px 10px;
            border: none;
            font-weight: 600;
            font-size: 11px;
        }}

        QTableView::item {{
            padding: 3px 6px;
            border: none;
        }}

        QTableView::item:hover {{
            background-color: {colors.surface_hover};
        }}

        QTableView::item:selected {{
            background-color: {colors.surface_selected};
            color: {colors.text_primary};
        }}

        /* ── Quiet Scrollbars ────────────────────────────────────── */
        QScrollBar:vertical, QScrollBar:horizontal {{
            background-color: transparent;
            width: 6px;
            height: 6px;
            margin: 0px;
        }}

        QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
            background-color: {colors.border_strong};
            min-height: 20px;
            border-radius: 3px;
        }}

        QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {{
            background-color: {colors.accent_primary};
        }}

        QScrollBar::add-line, QScrollBar::sub-line {{
            width: 0px;
            height: 0px;
        }}

        /* ── Task Navigation Rail Tabs ────────────────────────────── */
        QTabBar::tab {{
            background-color: {colors.canvas_base};
            color: {colors.text_secondary};
            padding: 6px 16px;
            border: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 3px;
            font-size: 12px;
            font-weight: 500;
        }}

        QTabBar::tab:selected {{
            background-color: {colors.surface_card};
            color: {colors.text_primary};
            border-top: 2px solid {colors.accent_primary};
            font-weight: 600;
        }}

        QTabBar::tab:hover:!selected {{
            background-color: {colors.surface_hover};
        }}

        /* ── Status Bar ──────────────────────────────────────────── */
        QStatusBar {{
            background-color: {colors.canvas_base};
            color: {colors.text_secondary};
            border: none;
        }}

        /* ── Progress Bar ────────────────────────────────────────── */
        QProgressBar {{
            background-color: {colors.canvas_base};
            border: 1px solid {colors.border_subtle};
            border-radius: 6px;
            text-align: center;
            color: {colors.text_primary};
            font-weight: 600;
            font-size: 11px;
        }}

        QProgressBar::chunk {{
            background-color: {colors.accent_primary};
            border-radius: 5px;
        }}
        """
        return qss
