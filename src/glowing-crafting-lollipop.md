# Reminder System Implementation Plan

## Overview
Add a reminder system with two types (Spaced Repetition and Stochastic), three action types, and desktop notifications. Follows existing codebase patterns.

---

## 1. Data Models

### Reminder (`/src/core/reminder/reminder.py`)
```python
class Reminder(BaseModel):
    id = AutoField()
    name = CharField()
    reminder_type = CharField()  # 'sr' or 'stochastic'
    habit = ForeignKeyField(Habit, null=True, on_delete='SET NULL')  # Optional link

    # Action
    action_type = CharField()  # 'open_link', 'random_line', 'show_text'
    action_payload = TextField()  # URL, file path, or text
    notification_method = CharField(default='desktop')  # 'desktop', 'none'

    # SR-specific
    ease_factor = FloatField(default=2.5)
    interval_days = IntegerField(default=1)

    # Stochastic-specific
    target_rate_per_week = FloatField(null=True)
    weight = FloatField(default=1.0)

    # Scheduling
    next_fire_at = DateTimeField(null=True, index=True)
    last_fired_at = DateTimeField(null=True)
    context_config = TextField(default='{}')  # JSON for context modifiers
    is_enabled = BooleanField(default=True)
    created_at = DateTimeField()
    updated_at = DateTimeField()
```

### ReminderLog (`/src/core/reminder/reminder_log.py`)
```python
class ReminderLog(BaseModel):
    id = AutoField()
    reminder = ForeignKeyField(Reminder, on_delete='CASCADE')
    fired_at = DateTimeField(index=True)
    action_executed = CharField()
    notification_sent = BooleanField(default=False)
    feedback_rating = IntegerField(null=True)  # Future: 0-3 for again/hard/good/easy
    context_modifier = FloatField(default=1.0)
    was_overdue = BooleanField(default=False)
```

---

## 2. Schedule Extensions

### SpacedRepetitionSchedule (`/src/core/schedule/spaced_repetition.py`)
- SM-2 algorithm implementation
- `calculate_next_interval(rating)` → returns (new_interval_days, new_ease_factor)
- Intervals grow: `interval = previous_interval × ease_factor`

### StochasticSchedule (`/src/core/schedule/stochastic.py`)
- Poisson distribution: `wait = exponential(rate_per_week / WEEK)`
- Enforces minimum gap between firings
- `get_next_task()` → random next fire time

---

## 3. Notification Service (`/src/core/notification/service.py`)

Generic service for future reuse:
```python
class NotificationService:
    @classmethod
    def get_instance(cls) -> 'NotificationService'
    def set_parent(self, widget: QWidget)
    def show_toast(self, title, message, duration=5000, preset=INFO)
    def show_reminder_notification(self, reminder_name, message, urgency='normal')
```
- Uses `pyqt-toast-notification` (already in requirements)
- Piano-themed styling

---

## 4. Action Handlers (`/src/core/reminder/actions.py`)

```python
class ActionHandler:
    @classmethod
    def execute(cls, reminder) -> str:  # Returns text for notification

    # Actions:
    _handle_open_link(payload)    # webbrowser.open() / subprocess for file://
    _handle_random_line(payload)  # Random line from text file
    _handle_show_text(payload)    # Return text as-is
```

---

## 5. Context Evaluator (`/src/core/reminder/context.py`)

Returns probability modifier [0.0 - 2.0]:
```python
class ContextEvaluator:
    def get_modifier(self, reminder) -> float:
        # idle_boost: ×1.5 after returning from idle (>5 min)
        # sustained_boost: ×1.3 after sustained activity (>30 min)
        # startup_reduce: ×0.3 during first 2 minutes
        # overdue_urgency (SR): +20% per overdue day, max ×2
```

---

## 6. Reminder Manager (`/src/core/reminder/manager.py`)

Background QThread (30-second check interval):
```python
class ReminderManager(QThread):
    reminder_fired = pyqtSignal(int, str)
    notification_requested = pyqtSignal(str, str, str)

    def run(self):
        self._check_overdue_on_startup()
        while self.running:
            self._check_and_fire_reminders()
            self.msleep(30_000)

    def _check_and_fire_reminders(self):
        # SR: Fire all due (guaranteed)
        # Stochastic: Weight-based competition, fire one

    def _fire_reminder(self, reminder, is_overdue=False):
        # Check anti-spam gap (15 min)
        # Apply context modifier
        # Execute action
        # Log to ReminderLog
        # Send notification
        # Reschedule
```

---

## 7. UI Components

### ReminderPage (`/src/gui/widgets/sheet_pages/reminder_page.py`)
- List view of all reminders
- "New Reminder" button
- ReminderCard for each reminder

### ReminderDetailPage (`/src/gui/widgets/sheet_pages/reminder_detail_page.py`)
- Form sections: Basic Info, Action, Schedule, Context, Notification
- Dynamic schedule fields based on type (SR vs Stochastic)
- Save/Delete buttons

### ReminderCard (`/src/gui/widgets/sheet_pages/reminder_card.py`)
- Card widget showing reminder summary
- Toggle enabled, edit button

---

## 8. File Structure

```
src/core/
    reminder/
        __init__.py
        reminder.py
        reminder_log.py
        manager.py
        actions.py
        context.py
    notification/
        __init__.py
        service.py
    schedule/
        spaced_repetition.py
        stochastic.py
    migrations/
        006_add_reminder_tables.py

src/gui/widgets/sheet_pages/
    reminder_page.py
    reminder_detail_page.py
    reminder_card.py
```

---

## 9. Integration Points

**db.py** - Add Reminder, ReminderLog to `create_tables()`

**piano_window.py** - Initialize ReminderManager:
```python
self.context_evaluator = ContextEvaluator()
self.reminder_manager = ReminderManager(self.context_evaluator)
self.reminder_manager.notification_requested.connect(self._on_notification)
self.reminder_manager.start()
```

**music_sheet_widget.py** - Add ReminderPage to navigation

---

## 10. Edge Cases

| Case | Handling |
|------|----------|
| Multiple SR due | Fire all (guaranteed) |
| Multiple Stochastic due | Weight-based competition, fire one |
| Anti-spam | 15 min minimum gap between notifications |
| App startup overdue | SR: fire with urgency; Stochastic: just reschedule |
| Timezone | Naive datetime (local time), same as existing models |

---

## 11. Implementation Phases

1. **Models & Migration** - Reminder, ReminderLog, migration 006
2. **Schedules** - SpacedRepetitionSchedule, StochasticSchedule
3. **Actions & Context** - ActionHandler, ContextEvaluator
4. **Notification** - NotificationService with pyqt-toast
5. **Manager** - ReminderManager background thread
6. **UI** - ReminderPage, ReminderDetailPage, ReminderCard, navigation
7. **Integration** - Wire up in PianoFloatingWindow, test end-to-end

---

## Verification

1. Create an SR reminder with "Show Text" action → verify notification appears on schedule
2. Create a Stochastic reminder (~5/day) → verify random firing over time
3. Test "Open Link" with `https://` and `file://` protocols
4. Test "Read Random Line" from a text file
5. Disable app, wait past scheduled time, restart → verify overdue handling
6. Create multiple Stochastic reminders → verify weight-based competition
