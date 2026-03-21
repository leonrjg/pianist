"""
Reminder Card - Vintage-styled card for displaying reminders.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Optional, Callable

from .vintage_form_widgets import VintageButton
from ..flow_layout import FlowLayout


def _t():
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current


class ReminderCard(QFrame):
    """Vintage-styled card for displaying a reminder"""

    toggle_enabled = pyqtSignal(object)  # Emits reminder
    edit_clicked = pyqtSignal(object)  # Emits reminder
    trigger_now = pyqtSignal(object)  # Emits reminder

    def __init__(self, reminder, parent=None):
        """
        Args:
            reminder: Reminder object to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.reminder = reminder
        self._setup_ui()

    def _setup_ui(self):
        """Setup the card UI"""
        t = _t()
        bg = t.card_bg_completed if not self.reminder.is_enabled else t.card_bg
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)

        self.setStyleSheet(f"""
            ReminderCard {{
                background-color: {bg};
                border-left: 4px solid {t.accent};
                border-top: 1px solid {t.card_border};
                border-right: 1px solid {t.card_border};
                border-bottom: 1px solid {t.card_border};
                border-radius: 3px;
                padding: 12px;
                margin: 4px 0px;
            }}
            ReminderCard:hover {{
                background-color: {t.card_bg};
                border-top: 1px solid {t.card_hover_border};
                border-right: 1px solid {t.card_hover_border};
                border-bottom: 1px solid {t.card_hover_border};
            }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        self.setLayout(layout)

        # Top row: name and type
        top_layout = QHBoxLayout()
        name_label = QLabel(self.reminder.name)
        name_label.setWordWrap(True)
        name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_layout.addWidget(name_label, 1)

        type_badge = self.reminder.reminder_type.upper()
        type_label = QLabel(type_badge)
        type_label.setStyleSheet(f"""
            background-color: {t.button_primary_bg};
            color: {t.button_primary_text};
            padding: 2px 8px;
            border-radius: 2px;
            font-size: 10px;
            font-weight: bold;
        """)
        top_layout.addWidget(type_label)
        top_layout.addStretch()

        layout.addLayout(top_layout)

        # Details
        details = self._get_details_text()
        details_label = QLabel(details)
        details_label.setWordWrap(True)
        details_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        details_label.setStyleSheet(f"color: {t.ink_secondary}; font-size: 11px;")
        layout.addWidget(details_label)

        # Action buttons
        btn_layout = FlowLayout(spacing=8)

        trigger_btn = VintageButton("Trigger Now", button_type="primary", parent=self)
        trigger_btn.clicked.connect(lambda: self.trigger_now.emit(self.reminder))
        btn_layout.addWidget(trigger_btn)

        toggle_btn = VintageButton(
            "Disable" if self.reminder.is_enabled else "Enable",
            button_type="secondary",
            parent=self
        )
        toggle_btn.clicked.connect(lambda: self.toggle_enabled.emit(self.reminder))
        btn_layout.addWidget(toggle_btn)

        edit_btn = VintageButton("Edit", button_type="secondary", parent=self)
        edit_btn.clicked.connect(lambda: self.edit_clicked.emit(self.reminder))
        btn_layout.addWidget(edit_btn)

        layout.addLayout(btn_layout)

    def _get_details_text(self) -> str:
        """Generate details text based on reminder type."""
        r = self.reminder
        lines = []

        # Schedule info
        if r.reminder_type == 'sr':
            lines.append(f"Interval: {r.interval_days} days (ease: {r.ease_factor:.2f})")
        elif r.reminder_type == 'stochastic':
            lines.append(f"Rate: {r.target_rate_per_week}/week (weight: {r.weight:.1f})")

        # Action info
        action_map = {
            'open_link': '🔗 Open Link',
            'random_line': '📄 Random Line',
            'show_text': '💬 Show Text'
        }
        lines.append(f"Action: {action_map.get(r.action_type, r.action_type)}")

        # Next fire
        if r.next_fire_at:
            lines.append(f"Next: {r.next_fire_at.strftime('%Y-%m-%d %H:%M')}")

        # Active window
        start_minute = getattr(r, "active_start_minute", 0)
        end_minute = getattr(r, "active_end_minute", 1440)
        if start_minute == end_minute:
            lines.append("Window: All day")
        else:
            lines.append(f"Window: {self._format_minutes(start_minute)}–{self._format_minutes(end_minute)}")

        return "\n".join(lines)

    @staticmethod
    def _format_minutes(total_minutes: int) -> str:
        if total_minutes == 1440:
            return "24:00"
        hours = max(0, int(total_minutes)) // 60
        minutes = max(0, int(total_minutes)) % 60
        return f"{hours:02d}:{minutes:02d}"
