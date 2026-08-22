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

from PyQt6.QtWidgets import QApplication, QMessageBox, QProxyStyle, QStyle
from gui.constants import make_font
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFontDatabase, QFont, QIcon

from core.db import initialize_database
from .services import HabitService
from .widgets import PianoFloatingWindow


class InstantTooltipStyle(QProxyStyle):
    """Removes Qt's default ~700ms tooltip wake-up delay so tooltips appear instantly.

    Qt gates the first tooltip on SH_ToolTip_WakeUpDelay (default 700ms) and only
    skips it for subsequent tooltips shown within SH_ToolTip_FallAsleepDelay. Zeroing
    both makes every tooltip immediate regardless of recent hover history.
    """

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return 150
        if hint == QStyle.StyleHint.SH_ToolTip_FallAsleepDelay:
            return 0
        return super().styleHint(hint, option, widget, returnData)


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

    # On macOS, raise_() on a top-level window activates the whole process by
    # default, stealing focus from other apps (e.g. when notification toasts
    # restack). Windows that genuinely want activation call activateWindow().
    # Only the cocoa plugin reads this variable; on other platforms it is
    # ignored, so no platform guard is needed.
    os.environ.setdefault("QT_MAC_SET_RAISE_PROCESS", "0")

    app = QApplication(sys.argv)
    app.setApplicationName("Pianist")
    app.setWindowIcon(QIcon(str(Path(__file__).parent / "icons" / "piano.png")))
    app.setStyle(InstantTooltipStyle(app.style()))
    
    # Load custom fonts and set default application font
    load_application_fonts()
    app.setFont(make_font("Oxygen", 12, QFont.Weight.Thin))

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

    # Guarantee session teardown on every quit path. Cmd+Q, app.quit(), or a
    # dock "Quit" may bypass the window's closeEvent, so persist active sessions
    # here too. _shutdown() is idempotent, so the overlap with closeEvent is safe.
    app.aboutToQuit.connect(window._shutdown)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
