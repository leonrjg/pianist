from habit.habit import Habit
from habit.bucket import Bucket
from util.time import get_timespan


def get_habit_with_longest_streak(habits: list[Habit]) -> Habit:
    """
    Find the habit with the longest streak from a list of habits.

    This function returns the longest run streak of all defined habits by comparing
    the longest streak across all provided habits.

    Args:
        habits: List of Habit objects to analyze.

    Returns:
        The Habit object that has achieved the longest consecutive
        streak of completed tasks.

    Raises:
        ValueError: If the habits list is empty.
    """
    return max(habits, key=lambda h: h.get_longest_streak())

def group_habits_by_schedule(habits: list[Habit]):
    """
    Group habits by their schedule type for periodicity analysis.

    This function returns a list of all habits with the same periodicity by
    organizing habits into groups based on their scheduling type.

    Args:
        habits: List of Habit objects to group.

    Returns:
        Iterator of (schedule_type, habits_group) tuples where:
        - schedule_type: String like 'daily', 'weekly', etc.
        - habits_group: Iterator of Habit objects with that schedule
    """
    from itertools import groupby
    return groupby(
        sorted(habits, key=lambda h: h.schedule),
        key=lambda h: h.schedule)

def get_time_spent(buckets: list[Bucket]) -> int:
    """
    Calculate the total net time spent across all activity buckets.

    This function sums the net duration (active time minus idle time)
    from all activity buckets for comprehensive time analysis.

    Args:
        buckets: List of Bucket objects containing session data.

    Returns:
        Total net duration in seconds across all buckets.

    Example:
        >>> buckets = habit.get_activity_buckets()
        >>> total_seconds = get_time_spent(buckets)
        >>> hours = total_seconds / 3600
        >>> print(f"Total time spent: {hours:.1f} hours")
    """
    return sum(b.net_duration for b in buckets)

def get_completion_rate(buckets: int, previous_tasks: int) -> float:
    """
    Calculate completion rate as the ratio of completed to scheduled tasks.

    This function handles edge cases and ensures the rate never exceeds 1.0,
    even if more sessions were completed than originally scheduled.

    Args:
        buckets: Number of completed activity buckets (sessions).
        previous_tasks: Number of tasks that were scheduled.

    Returns:
        Completion rate as a float between 0.0 and 1.0, where:
        - 0.0 means no tasks were completed
        - 1.0 means all scheduled tasks were completed

    Note:
        Edge cases:
        - If both buckets and previous_tasks are 0: returns 0.0
        - If previous_tasks is 0 but buckets > 0: returns 1.0
        - If buckets > previous_tasks: returns 1.0 (caps at 100%)

    Example:
        >>> rate = get_completion_rate(8, 10)  # 8 out of 10 tasks
        >>> print(f"Completion rate: {rate * 100:.1f}%")  # 80.0%
    """
    if buckets == 0 and previous_tasks == 0:
        return 0.0
    if previous_tasks == 0:
        return 1.0
    return min(buckets / previous_tasks, 1.0)

def sort_habits_by_completion_rate(habits: list[Habit]) -> list[tuple[Habit, float]]:
    """
    Sort habits by their completion rate in descending order.

    This function calculates the completion rate for each habit by comparing
    their activity buckets against their scheduled tasks, then sorts them
    from highest to lowest completion rate.

    Args:
        habits: List of Habit objects to analyze and sort.

    Returns:
        List of (Habit, completion_rate) tuples sorted by completion rate
        in descending order (best performers first).

    Example:
        >>> sorted_habits = sort_habits_by_completion_rate(all_habits)
        >>> for habit, rate in sorted_habits:
        ...     print(f"{habit.name}: {rate * 100:.1f}%")
        morning_meditation: 95.5%
        piano_practice: 87.2%
        weekly_review: 75.0%
    """
    habit_rates = []
    for habit in habits:
        schedule = habit.get_schedule()
        previous_tasks = len(schedule.get_previous_tasks(get_timespan(schedule.start)))
        buckets = len(habit.get_activity_buckets())
        rate = get_completion_rate(buckets, previous_tasks)
        habit_rates.append((habit, rate))
    return sorted(habit_rates, key=lambda x: x[1], reverse=True)