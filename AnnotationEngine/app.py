"""
PyVisionAnnotator — Entry point.

Launches the main application window.
"""
import sys

from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PyVisionAnnotator")
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

