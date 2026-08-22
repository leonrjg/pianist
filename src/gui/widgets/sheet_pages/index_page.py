"""
Index Page - Main directory showing list of habits and navigation options.
"""

from PyQt6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt
from datetime import datetime, timedelta

from core.util.time import get_friendly_datetime
from gui.constants import font_pt, make_font
from .base_page import SheetPage
from .habit_card import HabitCard

from core.task import get_upcoming_tasks, get_past_tasks, Task
from core.task.service import TaskService


class IndexPage(SheetPage):
    """Index page showing upcoming tasks"""

    def __init__(self, parent=None):
        self._offset = 0  # 0 = today+future, -1 = yesterday, -2 = two days ago, etc.
        self._task_container = None
        super().__init__(parent)

    def get_page_title(self) -> str:
        return "Next Tasks"

    def get_page_type(self) -> str:
        return "index"

    def _viewed_date(self):
        return (datetime.now() + timedelta(days=self._offset)).date()

    def build_content(self):
        layout = self.layout()

        title = self._create_section_header("Tasks")
        layout.addWidget(title)

        self._task_container = QWidget()
        self._task_container.setStyleSheet("background: transparent;")
        task_layout = QVBoxLayout()
        task_layout.setContentsMargins(0, 0, 0, 0)
        task_layout.setSpacing(6)
        self._task_container.setLayout(task_layout)
        layout.addWidget(self._task_container)
        layout.addStretch()

        self._rebuild_tasks()

    def _rebuild_tasks(self):
        _service = getattr(self.window(), 'service', None)
        # Exclude hourly habits: they recur many times per day and would flood the
        # task list with near-duplicate cards. Standalone manual tasks are pulled in
        # separately by the task queries and are unaffected.
        habits = sorted(
            (h for h in _service.get_all_habits() if h.schedule != 'hourly'),
            key=lambda h: h.name,
        ) if _service else []

        task_layout = self._task_container.layout()
        while task_layout.count():
            item = task_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        task_layout.addWidget(self._create_nav_row())

        if self._offset == 0:
            self._build_upcoming_tasks_section(task_layout, habits)
        else:
            self._build_past_day_section(task_layout, habits)

        task_layout.addStretch()

    def _create_nav_row(self):
        from gui.themes.manager import ThemeManager
        t = ThemeManager.get_instance().current

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        row = QHBoxLayout()
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(6)
        container.setLayout(row)

        btn_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {t.ink_secondary};
                font-size: {font_pt(10)}pt;
                padding: 0px 2px;
            }}
            QPushButton:hover:enabled {{
                color: {t.ink_primary};
            }}
            QPushButton:disabled {{
                color: {t.border};
            }}
        """

        prev_btn = QPushButton("<<")
        prev_btn.setStyleSheet(btn_style)
        prev_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        prev_btn.setFixedWidth(24)
        prev_btn.clicked.connect(self._go_prev)

        next_btn = QPushButton(">>")
        next_btn.setStyleSheet(btn_style)
        next_btn.setEnabled(self._offset < 0)
        next_btn.setFixedWidth(24)
        if self._offset < 0:
            next_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        next_btn.clicked.connect(self._go_next)

        now = datetime.now()
        viewed = self._viewed_date()
        yesterday = (now - timedelta(days=1)).date()
        if self._offset == 0:
            date_text = get_friendly_datetime(now)
        elif viewed == yesterday:
            date_text = get_friendly_datetime(now - timedelta(days=1))
        else:
            date_text = get_friendly_datetime(viewed)

        date_label = QLabel(f"♪ {date_text}")
        font = make_font(date_label.font().family(), 12)
        font.setBold(True)
        date_label.setFont(font)
        date_label.setStyleSheet(f"color: {t.ink_primary}; background: transparent; padding: 4px 0px;")

        row.addWidget(prev_btn)
        row.addWidget(date_label)
        row.addStretch()
        row.addWidget(next_btn)

        return container

    def refresh(self):
        if self._task_container is not None:
            self._task_container.setUpdatesEnabled(False)
            self._rebuild_tasks()
            self._task_container.setUpdatesEnabled(True)
            self._task_container.update()
        else:
            super().refresh()

    def _go_prev(self):
        self._offset -= 1
        self.refresh()

    def _go_next(self):
        if self._offset < 0:
            self._offset += 1
            self.refresh()

    def _build_upcoming_tasks_section(self, layout, habits):
        try:
            timespan = 30 * 24 * 60 * 60
            upcoming_tasks = get_upcoming_tasks(
                habits=habits,
                timespan=timespan,
                include_manual=True,
                include_completed=True
            )

            if upcoming_tasks:
                grouped_tasks = self._group_tasks_by_day(upcoming_tasks)
                today = datetime.now().date()

                for day_label, tasks in grouped_tasks:
                    # Skip the "today" day header — the nav row already covers it
                    if tasks and tasks[0].scheduled_at.date() != today:
                        header = self._create_day_header(day_label)
                        layout.addWidget(header)

                    for task in tasks:
                        accent_color = self._get_urgency_color(task.scheduled_at)
                        card = HabitCard(
                            task=task,
                            subtitle=get_friendly_datetime(task.scheduled_at),
                            accent_color=accent_color,
                            on_click=self._navigate_to_habit if task.habit else None,
                            on_complete=self._on_task_completion_toggled,
                            parent=self
                        )
                        layout.addWidget(card)

                    layout.addSpacing(8)
            else:
                tasks_label = self._create_text_label("No upcoming tasks in the next 30 days.", secondary=True)
                layout.addWidget(tasks_label)

        except Exception as e:
            error_label = self._create_text_label(f"Error loading tasks: {e}", secondary=True)
            layout.addWidget(error_label)

    def _build_past_day_section(self, layout, habits):
        try:
            viewed = self._viewed_date()
            now = datetime.now()
            days_back = (now.date() - viewed).days
            lookback_seconds = (days_back + 1) * 24 * 60 * 60

            past_tasks = get_past_tasks(
                habits=habits,
                lookback_seconds=lookback_seconds,
                include_manual=True,
                include_completed=True
            )

            day_tasks = [t for t in past_tasks if t.scheduled_at.date() == viewed]

            if day_tasks:
                from gui.themes.manager import ThemeManager
                t = ThemeManager.get_instance().current

                for task in day_tasks:
                    card = HabitCard(
                        task=task,
                        subtitle=get_friendly_datetime(task.scheduled_at),
                        accent_color=t.border,
                        on_click=self._navigate_to_habit if task.habit else None,
                        on_complete=self._on_task_completion_toggled,
                        parent=self
                    )
                    effect = QGraphicsOpacityEffect()
                    effect.setOpacity(0.7)
                    card.setGraphicsEffect(effect)
                    layout.addWidget(card)
            else:
                tasks_label = self._create_text_label("No tasks for this day.", secondary=True)
                layout.addWidget(tasks_label)

        except Exception as e:
            error_label = self._create_text_label(f"Error loading tasks: {e}", secondary=True)
            layout.addWidget(error_label)

    def _group_tasks_by_day(self, tasks):
        now = datetime.now()
        today = now.date()
        tomorrow = (now + timedelta(days=1)).date()

        grouped = {}
        for task in tasks[:100]:
            task_date = task.scheduled_at.date()

            if task_date == today:
                label = get_friendly_datetime(datetime.now())
            elif task_date == tomorrow:
                label = get_friendly_datetime(datetime.now() + timedelta(days=1))
            else:
                label = get_friendly_datetime(task_date)

            if label not in grouped:
                grouped[label] = []
            grouped[label].append(task)

        return list(grouped.items())

    def _create_day_header(self, text):
        from gui.themes.manager import ThemeManager
        t = ThemeManager.get_instance().current
        label = QLabel(f"♪ {text}")
        font = make_font(label.font().family(), 12)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet(f"""
            color: {t.ink_primary};
            padding: 6px 0px 4px 0px;
            background: transparent;
        """)
        return label

    def _get_urgency_color(self, task_dt):
        from gui.themes.manager import ThemeManager
        colors = ThemeManager.get_instance().current.urgency_colors
        now = datetime.now()
        hours_until = (task_dt - now).total_seconds() / 3600

        if hours_until < 0:
            return colors[0]   # Overdue
        elif hours_until < 2:
            return colors[1]   # Soon
        elif hours_until < 24:
            return colors[2]   # Today
        else:
            return colors[3]   # Future

    def _navigate_to_habit(self, habit):
        self.navigate_to.emit('habit_detail', habit.id)

    def _on_task_completion_toggled(self, habit, task_datetime, new_state):
        try:
            normalized_dt = task_datetime.replace(microsecond=0)

            if habit is not None:
                _service = getattr(self.window(), 'service', None)
                if _service:
                    _service.toggle_task_completion(habit, normalized_dt)
            else:
                TaskService.toggle_standalone_task_completion(normalized_dt, new_state)

            self.content_updated.emit()

        except Exception as e:
            print(f"Error toggling task completion: {e}")
