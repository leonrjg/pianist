"""
Reminder Row - Programme-style entry for a single reminder.

Renders one reminder as a ruled line, like an entry in a recital programme:
a left gutter holds the next-fire time, the body holds the name and a single
cadence-and-action descriptor, and quiet inline controls (fire now /
pause-resume) sit on the right. Clicking the body edits the reminder.

Shared by the Reminders page and the habit detail page's reminder section,
so it keeps the original constructor and the three signals those pages wire up.
"""

from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QSizePolicy
)
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt, pyqtSignal

from gui.themes import current_theme as _t
from gui.constants import make_font
from core.reminder.service import ReminderService
from .entry_card import ClickableCard


_ACTION_WORDS = {
    'open_link': 'open link',
    'random_line': 'random line',
    'show_text': 'show text',
    'anki_card': 'anki card',
}


class ReminderCard(ClickableCard):
    """A single ruled programme entry for a reminder."""

    toggle_enabled = pyqtSignal(object)  # Emits reminder
    edit_clicked = pyqtSignal(object)  # Emits reminder
    trigger_now = pyqtSignal(object)  # Emits reminder

    def __init__(self, reminder, parent=None):
        super().__init__(parent)
        self.reminder = reminder
        self._setup_ui()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        t = _t()
        self._dim = not self.reminder.is_enabled or self.reminder.next_fire_at is None

        self.setToolTip("Click to edit")
        self._apply_card_style(self._tick_color(t))

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 9, 8, 9)
        row.setSpacing(8)

        row.addWidget(self._build_gutter(t))
        row.addWidget(self._build_body(t), 1)
        row.addWidget(self._build_actions(t))

    def _build_gutter(self, t) -> QWidget:
        """Left time column: next-fire time over a relative-day caption."""
        r = self.reminder
        if r.is_enabled and r.next_fire_at is not None:
            time_text = r.next_fire_at.strftime("%H:%M")
            day_text = self._day_caption(r.next_fire_at)
        else:
            time_text = "—"
            day_text = "paused"

        gutter = QWidget()
        gutter.setFixedWidth(52)
        gutter.setStyleSheet("background: transparent;")
        box = QVBoxLayout(gutter)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)

        time_lbl = QLabel(time_text)
        time_font = make_font(t.header_font, 14)
        time_font.setBold(True)
        time_lbl.setFont(time_font)
        time_color = t.ink_secondary if self._dim else t.ink_primary
        time_lbl.setStyleSheet(f"color: {time_color}; background: transparent;")

        day_lbl = QLabel(day_text)
        day_lbl.setStyleSheet(f"color: {t.ink_secondary}; background: transparent; font-size: 9px;")

        box.addWidget(time_lbl)
        box.addWidget(day_lbl)
        return gutter

    def _build_body(self, t) -> QWidget:
        """Name plus a single cadence-and-action descriptor line."""
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        box = QVBoxLayout(body)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)

        name_lbl = QLabel(self.reminder.name)
        name_lbl.setWordWrap(True)
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        name_color = t.ink_secondary if self._dim else t.ink_primary
        name_font = make_font(t.header_font, 12)
        name_lbl.setFont(name_font)
        name_lbl.setStyleSheet(f"color: {name_color}; background: transparent;")
        box.addWidget(name_lbl)

        meta_lbl = QLabel(self._meta_text())
        meta_lbl.setWordWrap(True)
        meta_lbl.setStyleSheet(f"color: {t.ink_secondary}; background: transparent; font-size: 10px;")
        box.addWidget(meta_lbl)

        if ReminderService.is_reminder_outside_global_window(self.reminder):
            warn_lbl = QLabel("outside the global window")
            warn_lbl.setStyleSheet(
                f"color: {t.urgency_colors[0]}; background: transparent; "
                f"font-size: 9px; font-style: italic;"
            )
            box.addWidget(warn_lbl)

        return body

    def _build_actions(self, t) -> QWidget:
        """Right-hand stack of quiet text controls."""
        actions = QWidget()
        actions.setStyleSheet("background: transparent;")
        box = QVBoxLayout(actions)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)
        box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        fire_btn = self._flat_button("fire", t.accent_dark, "Fire this reminder now")
        fire_btn.clicked.connect(lambda: self.trigger_now.emit(self.reminder))
        box.addWidget(fire_btn, alignment=Qt.AlignmentFlag.AlignRight)

        toggle_text = "pause" if self.reminder.is_enabled else "resume"
        toggle_btn = self._flat_button(toggle_text, t.ink_secondary, f"{toggle_text.capitalize()} this reminder")
        toggle_btn.clicked.connect(lambda: self.toggle_enabled.emit(self.reminder))
        box.addWidget(toggle_btn, alignment=Qt.AlignmentFlag.AlignRight)

        return actions

    def _flat_button(self, text: str, color: str, tooltip: str) -> QPushButton:
        t = _t()
        btn = QPushButton(text)
        btn.setFlat(True)
        btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        btn.setToolTip(tooltip)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                padding: 1px 2px;
                color: {color};
                font-size: 10px;
            }}
            QPushButton:hover {{
                color: {t.link_hover};
                text-decoration: underline;
            }}
        """)
        return btn

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def _on_activate(self):
        """Clicking anywhere outside the inline buttons opens the editor."""
        self.edit_clicked.emit(self.reminder)

    # ------------------------------------------------------------------
    # Derived display values
    # ------------------------------------------------------------------

    def _tick_color(self, t) -> str:
        """Left-edge accent: urgency for active reminders, muted for paused."""
        r = self.reminder
        if not r.is_enabled or r.next_fire_at is None:
            return t.status_inactive
        hours_until = (r.next_fire_at - datetime.now()).total_seconds() / 3600
        overdue, soon, today, future = t.urgency_colors
        if hours_until < 0:
            return overdue
        if hours_until < 2:
            return soon
        if hours_until < 24:
            return today
        return future

    def _day_caption(self, dt: datetime) -> str:
        now = datetime.now()
        if dt < now:
            return "overdue"
        today = now.date()
        delta_days = (dt.date() - today).days
        if delta_days == 0:
            return "today"
        if delta_days == 1:
            return "tomorrow"
        if delta_days < 7:
            return dt.strftime("%a").lower()
        return dt.strftime("%b %d").lower()

    def _meta_text(self) -> str:
        """One-line 'cadence · [one-off] · action' descriptor."""
        r = self.reminder
        parts = []

        if r.reminder_type == 'stochastic':
            if getattr(r, 'habit_id', None):
                parts.append("loose")
            elif r.target_rate_per_week:
                parts.append(f"loose · {r.target_rate_per_week:g}×/wk")
            else:
                parts.append("loose")
        elif r.reminder_type == 'fixed':
            fixed_minute = getattr(r, "fixed_time_minute", None)
            if fixed_minute is not None:
                parts.append(f"fixed · {self._format_minutes(fixed_minute)}")
            else:
                parts.append("fixed")

        if getattr(r, 'manual_task', None) is not None:
            parts.append("one-off")

        if getattr(r, 'habit_id', None):
            parts.append("mark habit done")
        else:
            parts.append(_ACTION_WORDS.get(r.action_type, r.action_type))

        return " · ".join(parts)

    @staticmethod
    def _format_minutes(total_minutes: int) -> str:
        if total_minutes == 1440:
            return "24:00"
        hours = max(0, int(total_minutes)) // 60
        minutes = max(0, int(total_minutes)) % 60
        return f"{hours:02d}:{minutes:02d}"
