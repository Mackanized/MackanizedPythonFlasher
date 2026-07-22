import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.styles import apply_dark_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ECU Flasher")
    apply_dark_theme(app)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()