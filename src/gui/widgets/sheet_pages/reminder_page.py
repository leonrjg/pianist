"""
Reminder Page - The reminders "programme".

Reminders are laid out as a running order, sorted by when they next fire and
grouped under day headers (Overdue / Today / Tomorrow / weekday / date), with
silenced reminders collected in a dimmed "Paused" group at the foot of the
list. Global controls (mute, window, idle nudge, list visibility) are set
rarely, so they live in a collapsible "Preferences" disclosure below the list
instead of crowding the top.
"""

from datetime import datetime

from PyQt6.QtWidgets import (
    QVBoxLayout, QWidget, QLabel, QHBoxLayout, QCheckBox, QMessageBox,
    QSpinBox, QFrame, QPushButton, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt

from .base_page import SheetPage
from .reminder_card import ReminderCard
from ..themed_form_widgets import ThemedButton, ThemedLineEdit

from core.reminder.service import ReminderService as _ReminderService
from core.settings.service import SettingsService

from gui.constants import make_font
from gui.themes import current_theme as _t


class ReminderPage(SheetPage):
    """Page displaying the reminders programme."""

    def __init__(self, parent=None):
        # Persisted across refresh() rebuilds so the disclosure keeps its state.
        self._prefs_expanded = False
        super().__init__(parent)

    def get_page_title(self) -> str:
        return "Reminders"

    def get_page_type(self) -> str:
        return "reminders"

    def build_content(self):
        """Build the reminders programme."""
        layout = self.layout()

        header = self._create_section_header("Reminders")
        layout.addWidget(header)

        rm = self._get_reminder_manager()
        if rm and rm.is_muted:
            layout.addWidget(self._build_muted_banner(rm))

        layout.addWidget(self._build_add_row())
        layout.addSpacing(2)

        self._build_programme(layout)

        layout.addSpacing(12)
        self._build_preferences(layout)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Header pieces
    # ------------------------------------------------------------------

    def _build_add_row(self) -> QWidget:
        new_btn = ThemedButton("＋ New reminder", parent=self)
        new_btn.clicked.connect(lambda: self.navigate_to.emit('reminder_detail', None))

        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        row = QHBoxLayout(wrap)
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(0)
        row.addWidget(new_btn)
        row.addStretch()
        return wrap

    def _build_muted_banner(self, rm) -> QWidget:
        t = _t()
        banner = QFrame()
        banner.setStyleSheet(f"""
            QFrame {{
                background-color: {t.status_inactive};
                border-radius: 3px;
            }}
        """)
        row = QHBoxLayout(banner)
        row.setContentsMargins(10, 7, 8, 7)
        row.setSpacing(8)

        text = QLabel(self._muted_text(rm))
        text.setStyleSheet(f"color: {t.button_primary_text}; background: transparent; font-size: 11px; font-weight: bold;")
        row.addWidget(text)
        row.addStretch()

        unmute_btn = ThemedButton("Unmute", button_type="secondary", parent=self)
        unmute_btn.clicked.connect(self._unmute)
        row.addWidget(unmute_btn)
        return banner

    @staticmethod
    def _muted_text(rm) -> str:
        until = rm.muted_until
        if until is None or until == datetime.max:
            return "All reminders are muted indefinitely"
        return f"All reminders are muted until {until.strftime('%H:%M')}"

    # ------------------------------------------------------------------
    # Programme list
    # ------------------------------------------------------------------

    def _build_programme(self, layout):
        show_habit_linked = bool(SettingsService.get('reminders.show_habit_linked_on_page', False))
        show_one_off = bool(SettingsService.get('reminders.show_one_off_on_page', True))
        reminders = _ReminderService.get_for_reminders_page(show_habit_linked, show_one_off)

        if not reminders:
            layout.addWidget(self._build_empty_state(show_habit_linked))
            return

        active = [r for r in reminders if r.is_enabled and r.next_fire_at is not None]
        paused = [r for r in reminders if not (r.is_enabled and r.next_fire_at is not None)]
        active.sort(key=lambda r: r.next_fire_at)

        now = datetime.now()
        current_group = None
        for reminder in active:
            label = self._group_label(reminder.next_fire_at, now)
            if label != current_group:
                layout.addWidget(self._group_header(label))
                current_group = label
            layout.addWidget(self._make_row(reminder))
            layout.addSpacing(2)

        if paused:
            layout.addWidget(self._group_header("Paused"))
            for reminder in paused:
                row = self._make_row(reminder)
                effect = QGraphicsOpacityEffect()
                effect.setOpacity(0.55)
                row.setGraphicsEffect(effect)
                layout.addWidget(row)
                layout.addSpacing(2)

    def _make_row(self, reminder) -> ReminderCard:
        card = ReminderCard(reminder, self)
        card.toggle_enabled.connect(self._toggle_reminder)
        card.edit_clicked.connect(self._edit_reminder)
        card.trigger_now.connect(self._trigger_reminder)
        return card

    def _build_empty_state(self, show_habit_linked: bool) -> QLabel:
        message = "No reminders yet. Create one to get started."
        if not show_habit_linked and _ReminderService.get_for_reminders_page(True):
            message = "No standalone reminders. Habit-linked ones are hidden — see Preferences."
        label = QLabel(message)
        label.setWordWrap(True)
        label.setStyleSheet(f"color: {_t().ink_secondary}; font-style: italic; margin-top: 18px;")
        return label

    def _group_header(self, text: str) -> QLabel:
        t = _t()
        label = QLabel(f"♪ {text}")
        font = make_font(t.header_font, 12)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet(f"color: {t.ink_primary}; background: transparent; padding: 10px 0px 2px 0px;")
        return label

    @staticmethod
    def _group_label(next_fire_at: datetime, now: datetime) -> str:
        if next_fire_at < now:
            return "Overdue"
        delta_days = (next_fire_at.date() - now.date()).days
        if delta_days == 0:
            return "Today"
        if delta_days == 1:
            return "Tomorrow"
        if delta_days < 7:
            return next_fire_at.strftime("%A")
        return next_fire_at.strftime("%B %d")

    # ------------------------------------------------------------------
    # Preferences disclosure (demoted global controls)
    # ------------------------------------------------------------------

    def _build_preferences(self, layout):
        layout.addWidget(self._create_separator())

        caret = "▾" if self._prefs_expanded else "▸"
        toggle = QPushButton(f"{caret}  Preferences")
        toggle.setFlat(True)
        toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        t = _t()
        toggle.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                text-align: left;
                padding: 6px 0px;
                color: {t.ink_secondary};
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{ color: {t.ink_primary}; }}
        """)
        toggle.clicked.connect(self._toggle_preferences)
        layout.addWidget(toggle)

        if not self._prefs_expanded:
            return

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(4, 2, 0, 4)
        body_layout.setSpacing(8)

        self._build_mute_section(body_layout)
        body_layout.addWidget(self._create_separator())
        self._build_global_window_section(body_layout)
        self._build_idle_nudge_section(body_layout)
        body_layout.addWidget(self._create_separator())
        self._build_visibility_section(body_layout)

        layout.addWidget(body)

    def _toggle_preferences(self):
        self._prefs_expanded = not self._prefs_expanded
        self.refresh()

    # ------------------------------------------------------------------
    # Preference sub-sections
    # ------------------------------------------------------------------

    def _get_reminder_manager(self):
        """Get the reminder manager from the top-level window."""
        return getattr(self.window(), 'reminder_manager', None)

    def _build_mute_section(self, layout):
        """Build the mute reminders controls."""
        rm = self._get_reminder_manager()

        mute_label = QLabel("Mute all reminders")
        mute_label.setStyleSheet(f"color: {_t().ink_primary}; font-weight: bold; font-size: 12px;")
        layout.addWidget(mute_label)

        if rm and rm.is_muted:
            status = QLabel("Currently muted — see the banner above to unmute.")
            status.setStyleSheet(f"color: {_t().ink_secondary}; font-style: italic; font-size: 11px;")
            layout.addWidget(status)
            return

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        for label, hours in [("1 h", 1), ("4 h", 4), ("24 h", 24), ("Indefinitely", None)]:
            btn = ThemedButton(label, button_type="secondary", parent=self)
            btn.clicked.connect(lambda _, h=hours: self._mute(h))
            row_layout.addWidget(btn)

        row_layout.addStretch()
        layout.addWidget(row)

    def _build_global_window_section(self, layout):
        """Build global reminder window controls."""
        title = QLabel("Global reminder window")
        title.setStyleSheet(f"color: {_t().ink_primary}; font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        enabled = QCheckBox()
        enabled.setChecked(bool(SettingsService.get('reminders.global_window_enabled', False)))
        row_layout.addWidget(enabled)

        start_edit = ThemedLineEdit("HH:MM")
        start_edit.setText(self._format_minutes(SettingsService.get('reminders.global_window_start_minute', 0)))
        start_edit.setFixedWidth(58)
        row_layout.addWidget(start_edit)

        sep = QLabel("to")
        sep.setStyleSheet(f"color: {_t().ink_secondary}; background: transparent; font-size: 11px;")
        row_layout.addWidget(sep)

        end_edit = ThemedLineEdit("HH:MM")
        end_edit.setText(self._format_minutes(SettingsService.get('reminders.global_window_end_minute', 1440)))
        end_edit.setFixedWidth(58)
        row_layout.addWidget(end_edit)

        def save_window(refresh_page=True):
            try:
                start = self._parse_time(start_edit.text(), allow_24=False)
                end = self._parse_time(end_edit.text(), allow_24=True)
            except ValueError as e:
                QMessageBox.warning(self, "Validation Error", str(e))
                return
            SettingsService.set('reminders.global_window_start_minute', start)
            SettingsService.set('reminders.global_window_end_minute', end)
            self.content_updated.emit()
            if refresh_page:
                self.refresh()

        def on_enabled_changed(state):
            SettingsService.set('reminders.global_window_enabled', bool(state))
            save_window()

        enabled.stateChanged.connect(on_enabled_changed)
        start_edit.editingFinished.connect(lambda: save_window())
        end_edit.editingFinished.connect(lambda: save_window())
        row_layout.addStretch()
        layout.addWidget(row)

    def _build_idle_nudge_section(self, layout):
        """Build idle session nudge controls."""
        title = QLabel("Idle session nudge")
        title.setStyleSheet(f"color: {_t().ink_primary}; font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        current = int(SettingsService.get('session.idle_nudge_seconds', 0))
        current_minutes = current // 60 if current > 0 else 0

        enabled_cb = QCheckBox()
        enabled_cb.setChecked(current > 0)
        row_layout.addWidget(enabled_cb)

        spin = QSpinBox()
        spin.setRange(1, 120)
        spin.setValue(current_minutes if current_minutes > 0 else 5)
        spin.setSuffix(" min")
        spin.setFixedWidth(80)
        spin.setEnabled(current > 0)
        row_layout.addWidget(spin)

        hint = QLabel("after idle")
        hint.setStyleSheet(f"color: {_t().ink_secondary}; background: transparent; font-size: 11px;")
        row_layout.addWidget(hint)
        row_layout.addStretch()
        layout.addWidget(row)

        def _save():
            if enabled_cb.isChecked():
                SettingsService.set('session.idle_nudge_seconds', spin.value() * 60)
            else:
                SettingsService.set('session.idle_nudge_seconds', 0)

        enabled_cb.stateChanged.connect(lambda state: (spin.setEnabled(bool(state)), _save()))
        spin.valueChanged.connect(lambda _: _save())

    def _build_visibility_section(self, layout):
        """Build list visibility controls."""
        for key, default, label_text in [
            ('reminders.show_habit_linked_on_page', False, "Show habit-linked reminders"),
            ('reminders.show_one_off_on_page', True, "Show one-off reminders"),
        ]:
            row = QWidget()
            row.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            checkbox = QCheckBox()
            checkbox.setChecked(bool(SettingsService.get(key, default)))
            row_layout.addWidget(checkbox)

            label = QLabel(label_text)
            label.setStyleSheet(f"color: {_t().ink_primary}; background: transparent; font-size: 12px;")
            row_layout.addWidget(label)

            def on_changed(state, k=key):
                SettingsService.set(k, bool(state))
                self.refresh()

            checkbox.stateChanged.connect(on_changed)
            row_layout.addStretch()
            layout.addWidget(row)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _mute(self, hours):
        rm = self._get_reminder_manager()
        if rm:
            rm.mute(hours)
        self.refresh()

    def _unmute(self):
        rm = self._get_reminder_manager()
        if rm:
            rm.unmute()
        self.refresh()

    def _toggle_reminder(self, reminder):
        """Toggle reminder enabled state."""
        from core.reminder.service import ReminderService
        ReminderService.toggle_enabled(reminder)
        self.navigate_to.emit('reminders', None)

    def _edit_reminder(self, reminder):
        """Navigate to edit page."""
        self.navigate_to.emit('reminder_detail', reminder.id)

    def _trigger_reminder(self, reminder):
        """Manually trigger a reminder now."""
        from core.reminder.service import ReminderService

        fresh_reminder = ReminderService.get_by_id(reminder.id)
        ReminderService.fire_reminder(fresh_reminder, record_fire=False)
        self.content_updated.emit()

    # ------------------------------------------------------------------
    # Time helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_minutes(total_minutes: int) -> str:
        total_minutes = int(total_minutes)
        if total_minutes == 1440:
            return "24:00"
        hours = max(0, total_minutes) // 60
        minutes = max(0, total_minutes) % 60
        return f"{hours:02d}:{minutes:02d}"

    @staticmethod
    def _parse_time(value: str, allow_24: bool) -> int:
        text = value.strip()
        parts = text.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
        except ValueError:
            raise ValueError("Time must be in HH:MM format")
        if hours == 24 and minutes == 0 and allow_24:
            return 1440
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            raise ValueError("Time must be between 00:00 and 23:59")
        if hours == 24:
            raise ValueError("Start time cannot be 24:00")
        return hours * 60 + minutes
