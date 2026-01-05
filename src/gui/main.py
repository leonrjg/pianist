"""
Main entry point for the Piano GUI application (Refactored version)

This uses the new clean architecture with separated concerns.
"""
import os
import sys
import multiprocessing
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase, QFont

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
    # Required for multiprocessing on some platforms
    multiprocessing.set_start_method('spawn', force=True)

    app = QApplication(sys.argv)
    app.setApplicationName("Pianist")
    
    # Load custom fonts and set default application font
    load_application_fonts()
    default_font = QFont("Rounded Mplus 1c", 12)
    app.setFont(default_font)

    # Create and show the window
    window = PianoFloatingWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
