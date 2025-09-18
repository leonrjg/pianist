from habit.habit import Habit
from habit.bucket import Bucket


def get_habit_with_longest_streak(habits: list[Habit]) -> Habit:
    """Return the habit with the longest streak from a list of habits."""
    return max(habits, key=lambda h: h.get_longest_streak())

def group_habits_by_schedule(habits: list[Habit]):
    """Group habits by their schedule."""
    from itertools import groupby
    return groupby(
        sorted(habits, key=lambda h: h.schedule),
        key=lambda h: h.schedule)

def get_time_spent(buckets: list[Bucket]) -> int:
    """Calculate the total time spent on a habit."""
    return sum(b.net_duration for b in buckets)

def get_task_vs_schedule_ratio(buckets: int, previous_tasks: int) -> float:
    """Calculate the ratio of completed tasks to scheduled tasks, accounting for edge cases."""
    if buckets == 0 and previous_tasks == 0:
        return 0.0
    if previous_tasks == 0:
        return 1.0
    return min(buckets / previous_tasks, 1.0)