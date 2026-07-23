import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.qt_startup import is_non_gui_automation, qt_startup_error
from gui.styles import apply_dark_theme


def main():
    if is_non_gui_automation():
        print(qt_startup_error(), file=sys.stderr)
        return 2

    app = QApplication(sys.argv)
    app.setApplicationName("ECU Flasher")
    apply_dark_theme(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
