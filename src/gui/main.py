"""
Main entry point for the Piano GUI application (Refactored version)

This uses the new clean architecture with separated concerns.
"""

import sys
import multiprocessing
from PyQt6.QtWidgets import QApplication

from .widgets import PianoFloatingWindow


def main():
    """Main entry point"""
    # Required for multiprocessing on some platforms
    multiprocessing.set_start_method('spawn', force=True)

    app = QApplication(sys.argv)
    app.setApplicationName("Pianist")

    # Create and show the window
    window = PianoFloatingWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
