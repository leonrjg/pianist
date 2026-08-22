from datetime import datetime
from types import SimpleNamespace

from core.habit.habit import Habit
from core.reminder.service import ReminderService


def test_habit_fixed_reminder_uses_today_when_time_is_still_ahead():
    habit = Habit(
        name="Piano",
        schedule="daily",
        started_at=datetime(2026, 5, 1, 0, 0),
        created_at=datetime(2026, 5, 1, 0, 0),
        updated_at=datetime(2026, 5, 1, 0, 0),
    )
    reminder = SimpleNamespace(
        id="fixed-habit",
        reminder_type="fixed",
        habit=habit,
        manual_task=None,
        fixed_time_minute=9 * 60,
        next_fire_at=None,
    )

    assert ReminderService.get_next_fixed_fire_time(
        reminder,
        datetime(2026, 5, 2, 8, 0),
    ) == datetime(2026, 5, 2, 9, 0)


def test_habit_fixed_reminder_advances_after_time_passes():
    habit = Habit(
        name="Piano",
        schedule="daily",
        started_at=datetime(2026, 5, 1, 0, 0),
        created_at=datetime(2026, 5, 1, 0, 0),
        updated_at=datetime(2026, 5, 1, 0, 0),
    )
    reminder = SimpleNamespace(
        id="fixed-habit",
        reminder_type="fixed",
        habit=habit,
        manual_task=None,
        fixed_time_minute=9 * 60,
        next_fire_at=None,
    )

    assert ReminderService.get_next_fixed_fire_time(
        reminder,
        datetime(2026, 5, 2, 10, 0),
    ) == datetime(2026, 5, 3, 9, 0)


def test_monthly_habit_fixed_reminder_advances_past_same_day_schedule_result():
    habit = Habit(
        name="Piano",
        schedule="monthly",
        started_at=datetime(2026, 1, 1, 0, 0),
        created_at=datetime(2026, 1, 1, 0, 0),
        updated_at=datetime(2026, 1, 1, 0, 0),
    )
    reminder = SimpleNamespace(
        id="fixed-monthly-habit",
        reminder_type="fixed",
        habit=habit,
        manual_task=None,
        fixed_time_minute=9 * 60,
        next_fire_at=None,
    )

    assert ReminderService.get_next_fixed_fire_time(
        reminder,
        datetime(2026, 5, 2, 10, 0),
    ) == datetime(2026, 5, 31, 9, 0)


def test_manual_task_fixed_reminder_is_one_off():
    manual_task = SimpleNamespace(
        title="Call tuner",
        scheduled_at=datetime(2026, 5, 2, 15, 30),
        completed_at=None,
        deleted_at=None,
    )
    reminder = SimpleNamespace(
        id="fixed-task",
        reminder_type="fixed",
        habit=None,
        manual_task=manual_task,
        fixed_time_minute=15 * 60 + 30,
        next_fire_at=None,
    )

    assert ReminderService.get_next_fixed_fire_time(
        reminder,
        datetime(2026, 5, 2, 12, 0),
    ) == datetime(2026, 5, 2, 15, 30)
    assert ReminderService.get_next_fixed_fire_time(
        reminder,
        datetime(2026, 5, 2, 16, 0),
    ) is None


def test_fixed_reminder_warns_when_outside_global_window(monkeypatch):
    settings = {
        'reminders.global_window_enabled': True,
        'reminders.global_window_start_minute': 9 * 60,
        'reminders.global_window_end_minute': 17 * 60,
    }
    monkeypatch.setattr(
        'core.reminder.service.SettingsService.get',
        lambda key, default=None: settings.get(key, default),
    )
    reminder = SimpleNamespace(
        reminder_type="fixed",
        fixed_time_minute=8 * 60,
        next_fire_at=None,
        active_start_minute=0,
        active_end_minute=1440,
    )

    assert ReminderService.is_reminder_outside_global_window(reminder)


def test_reminder_window_inside_global_does_not_warn(monkeypatch):
    settings = {
        'reminders.global_window_enabled': True,
        'reminders.global_window_start_minute': 9 * 60,
        'reminders.global_window_end_minute': 17 * 60,
    }
    monkeypatch.setattr(
        'core.reminder.service.SettingsService.get',
        lambda key, default=None: settings.get(key, default),
    )
    reminder = SimpleNamespace(
        reminder_type="stochastic",
        fixed_time_minute=None,
        next_fire_at=None,
        active_start_minute=10 * 60,
        active_end_minute=12 * 60,
    )

    assert not ReminderService.is_reminder_outside_global_window(reminder)


def test_habit_reminder_message_uses_habit_name():
    reminder = SimpleNamespace(habit=SimpleNamespace(name="Piano"))

    assert ReminderService.get_habit_message(reminder) == "It's time for Piano"


def test_habit_stochastic_reminder_schedules_random_time_on_due_day(monkeypatch):
    monkeypatch.setattr('core.reminder.service.random.choice', lambda minutes: 10 * 60)
    habit = Habit(
        name="Piano",
        schedule="daily",
        started_at=datetime(2026, 5, 1, 0, 0),
        created_at=datetime(2026, 5, 1, 0, 0),
        updated_at=datetime(2026, 5, 1, 0, 0),
    )
    reminder = SimpleNamespace(
        id="stochastic-habit",
        reminder_type="stochastic",
        habit=habit,
        active_start_minute=9 * 60,
        active_end_minute=17 * 60,
    )

    assert ReminderService.get_next_habit_stochastic_fire_time(
        reminder,
        datetime(2026, 5, 2, 8, 0),
    ) == datetime(2026, 5, 2, 10, 0)


def test_habit_stochastic_reminder_advances_when_random_time_has_passed(monkeypatch):
    monkeypatch.setattr('core.reminder.service.random.choice', lambda minutes: 7 * 60)
    habit = Habit(
        name="Piano",
        schedule="daily",
        started_at=datetime(2026, 5, 1, 0, 0),
        created_at=datetime(2026, 5, 1, 0, 0),
        updated_at=datetime(2026, 5, 1, 0, 0),
    )
    reminder = SimpleNamespace(
        id="stochastic-habit",
        reminder_type="stochastic",
        habit=habit,
        active_start_minute=6 * 60,
        active_end_minute=12 * 60,
    )

    assert ReminderService.get_next_habit_stochastic_fire_time(
        reminder,
        datetime(2026, 5, 2, 8, 0),
    ) == datetime(2026, 5, 3, 7, 0)


def test_is_snoozed_false_when_no_snooze():
    reminder = SimpleNamespace(snooze_until=None)

    assert not ReminderService.is_snoozed(reminder, datetime(2026, 5, 2, 8, 0))


def test_is_snoozed_true_while_snooze_floor_in_future():
    reminder = SimpleNamespace(snooze_until=datetime(2026, 5, 2, 9, 0))

    assert ReminderService.is_snoozed(reminder, datetime(2026, 5, 2, 8, 0))


def test_is_snoozed_false_once_snooze_floor_elapsed():
    reminder = SimpleNamespace(snooze_until=datetime(2026, 5, 2, 9, 0))

    # At exactly the floor the snooze has elapsed and the reminder may fire.
    assert not ReminderService.is_snoozed(reminder, datetime(2026, 5, 2, 9, 0))
    assert not ReminderService.is_snoozed(reminder, datetime(2026, 5, 2, 10, 0))


def test_completed_habit_stochastic_reminder_reschedules_without_firing(monkeypatch):
    habit = Habit(
        name="Piano",
        schedule="daily",
        started_at=datetime(2026, 5, 1, 0, 0),
        created_at=datetime(2026, 5, 1, 0, 0),
        updated_at=datetime(2026, 5, 1, 0, 0),
    )
    reminder = SimpleNamespace(
        id="stochastic-habit",
        reminder_type="stochastic",
        habit=habit,
        next_fire_at=datetime(2026, 5, 2, 15, 0),
    )
    rescheduled = {}

    monkeypatch.setattr(habit, 'is_task_completed', lambda task_dt: task_dt == datetime(2026, 5, 2, 0, 0))
    monkeypatch.setattr(
        ReminderService,
        'reschedule',
        lambda reminder_arg, base_time=None: rescheduled.update(reminder=reminder_arg, base_time=base_time),
    )

    assert not ReminderService.should_fire_habit_reminder(reminder)
    assert rescheduled == {
        'reminder': reminder,
        'base_time': datetime(2026, 5, 2, 15, 0, 1),
    }
