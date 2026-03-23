"""
Main entry point for the Piano GUI application (Refactored version)

This uses the new clean architecture with separated concerns.
"""
import os
import sys
import multiprocessing
from pathlib import Path

if sys.platform == 'win32':
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except OSError:
        pass  # Already set by the Python executable manifest; Qt will use whatever was set

from PyQt6.QtWidgets import QApplication, QMessageBox
from gui.constants import make_font
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFontDatabase, QFont

from core.db import initialize_database
from .services import HabitService
from .widgets import PianoFloatingWindow


def load_application_fonts() -> None:
    """Load custom fonts for the application and return the default font family"""
    fonts_dir = Path(__file__).parent / "fonts"
    font_files = os.listdir(fonts_dir)

    default_family = None
    for font_file in font_files:
        font_path = fonts_dir / font_file
        if font_path.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id != -1 and default_family is None:
                # Get the actual font family name from the first loaded font
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    print(f"Loaded font: {families[0]}")


def main():
    """Main entry point"""
    multiprocessing.set_start_method('spawn', force=True)

    app = QApplication(sys.argv)
    app.setApplicationName("Pianist")
    
    # Load custom fonts and set default application font
    load_application_fonts()
    app.setFont(make_font("Rounded Mplus 1c", 12))

    # Initialize database and data service before creating any UI
    try:
        initialize_database()
        service = HabitService()
        service.load()
    except Exception as e:
        QMessageBox.critical(None, "Startup Error", f"Failed to initialize application:\n{e}")
        raise e

    # Refresh the UI after each sync completes. QTimer.singleShot marshals
    # the call onto the main thread from delta_sync's background thread.
    from core.sync.service import SyncService
    SyncService.get_instance().client.on_sync_complete = lambda: QTimer.singleShot(0, service.refresh)

    # Create and show the window
    window = PianoFloatingWindow(service)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
