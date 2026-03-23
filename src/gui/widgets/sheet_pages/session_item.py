"""
Session Item - Display individual session with delete option.
"""
from time import strftime

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt

from core.util.time import get_friendly_elapsed, get_friendly_datetime, HOUR
from .productivity_progress_bar import ProductivityProgressBar


from gui.themes import current_theme as _t


class SessionItem(QFrame):
    """Individual session display with delete button"""

    def __init__(self, log, on_delete=None, parent=None):
        """
        Args:
            log: Log object representing the session
            on_delete: Callback for delete action, receives the log as parameter
            parent: Parent widget
        """
        super().__init__(parent)
        self.log = log
        self.on_delete = on_delete

        self._setup_ui()

    def _setup_ui(self):
        """Set up the session item UI"""
        t = _t()
        self.setStyleSheet(f"""
            SessionItem {{
                background-color: {t.paper_dark};
                border: 1px solid {t.border};
                border-radius: 2px;
                padding: 4px;
                margin: 2px 0px;
            }}
        """)

        # Main vertical layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(4, 3, 4, 3)
        main_layout.setSpacing(3)
        self.setLayout(main_layout)

        # Top row: duration, time, source, delete button
        top_layout = QHBoxLayout()
        top_layout.setSpacing(6)

        # Duration
        if self.log.end:
            # Include offset in duration calculation
            offset = getattr(self.log, 'offset', 0)  # Safe access for backward compatibility
            duration_seconds = (self.log.end - self.log.start).total_seconds() - self.log.idle_time + offset
            duration_str = get_friendly_elapsed(duration_seconds)
            duration_badge = QLabel(f"⏱ {duration_str}")
            duration_badge.setStyleSheet(f"""
                background-color: {t.button_primary_bg};
                color: {t.button_primary_text};
                font-size: 9px;
                padding: 2px 6px;
                border-radius: 3px;
            """)
            top_layout.addWidget(duration_badge)

            # Add offset note if manually adjusted
            if offset != 0:
                offset_sign = "+" if offset > 0 else ""
                offset_str = get_friendly_elapsed(abs(offset))
                offset_note = QLabel(f"Manual time adjustment: {offset_sign}{offset_str}")
                offset_note.setStyleSheet("color: rgb(100, 80, 65); font-size: 8px; font-style: italic; background: transparent;")
                top_layout.addWidget(offset_note)

        # Session time
        end_str = self.log.end.strftime('%H:%M') if self.log.end else '...'
        start_time = f"{self.log.start.strftime('%H:%M')} ~ {end_str}"
        time_label = QLabel(start_time)
        time_label.setStyleSheet(f"color: {t.ink_primary}; font-size: 10px; background: transparent;")
        top_layout.addWidget(time_label)

        if self.log.started_by:
            source = self.log.started_by
            source_label = QLabel(f"(started by {source})")
            source_label.setStyleSheet("color: rgb(140, 120, 100); font-size: 9px; font-style: italic; background: transparent;")
            top_layout.addWidget(source_label)

        top_layout.addStretch()

        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(18, 18)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(140, 40, 40, 120);
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(180, 60, 60, 150);
            }
        """)
        delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        if self.on_delete:
            delete_btn.clicked.connect(lambda: self.on_delete(self.log))
        else:
            delete_btn.setEnabled(False)
        
        top_layout.addWidget(delete_btn)
        main_layout.addLayout(top_layout)

        # Productivity rate progress bar
        if self.log.end:
            total_time = (self.log.end - self.log.start).total_seconds()
            if total_time > 0:
                offset = getattr(self.log, 'offset', 0)  # Safe access for backward compatibility
                active_time = total_time - self.log.idle_time + offset
                productivity_rate = active_time / total_time
                progress_bar = ProductivityProgressBar(productivity_rate, parent=self)
                main_layout.addWidget(progress_bar)
