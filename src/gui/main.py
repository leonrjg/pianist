"""
Main entry point for the Piano GUI application (Refactored version)

This uses the new clean architecture with separated concerns.
"""
import os
import sys
import multiprocessing
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFontDatabase, QFont

from core.db import initialize_database
from .services import HabitService
from .widgets import PianoFloatingWindow


def load_application_fonts() -> dict[str, str]:
    """Load all custom fonts and return a mapping of filename stem -> family name."""
    fonts_dir = Path(__file__).parent / "fonts"
    loaded = {}
    for font_file in os.listdir(fonts_dir):
        font_path = fonts_dir / font_file
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                loaded[Path(font_file).stem] = families[0]
                print(f"Loaded font: {families[0]}")
    return loaded


def main():
    """Main entry point"""
    multiprocessing.set_start_method('spawn', force=True)

    app = QApplication(sys.argv)
    app.setApplicationName("Pianist")
    
    # Load custom fonts and set default application font
    fonts = load_application_fonts()
    default_font = QFont(fonts.get("MPLUSRounded1c-Regular", "M PLUS Rounded 1c"), 12)
    app.setFont(default_font)

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
