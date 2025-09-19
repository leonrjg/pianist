import time
from datetime import datetime
from itertools import islice

import click
from peewee import DoesNotExist

import analytics
from db import db, initialize_database
from habit.habit import Habit
from habit.habit_tracker import HabitTracker
from session import Session, SessionStatus
from session import SessionStatus
from util.time import get_friendly_elapsed, get_friendly_datetime, get_timespan


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        return
    initialize_database()


@cli.command()
@click.argument('name')
@click.option('--schedule', required=True,
              type=click.Choice(['hourly', 'daily', 'weekly', 'monthly', 'exponential_3', 'yearly']),
              help='Schedule type for the habit')
@click.option('--duration', type=int, help='Allocated time per period in minutes')
@click.option('--timeout', type=int, help='Inactivity threshold for trackers in seconds')
@click.option('--track', 'trackers', multiple=True, default=[], type=click.Choice(['io', 'window']), help='Trackers (one or more)')
@click.option('--track-args', help='Tracker arguments in "key=value&key2=value2" format (query string)')
def save(name, schedule, duration, timeout, trackers, track_args):
    """Add or edit a habit with the specified parameters."""
    with db.atomic():
        habit = Habit.get_or_none(Habit.name == name) or Habit.create(name=name, schedule=schedule)

        if duration:
            habit.allocated_time = duration * 60 # Minutes to seconds
        if timeout:
            habit.inactivity_threshold = timeout

        habit.save()

        for tracker in trackers:
            HabitTracker.insert(habit=habit, tracker=tracker, config=HabitTracker.create_json_config(track_args),
                                 is_enabled=True).on_conflict_replace().execute()
    
    click.echo(f"Saved habit '{name}' with schedule '{schedule}'")

@cli.command()
@click.argument('name')
def delete(name):
    """Delete a habit by name."""
    try:
        habit = Habit.get(Habit.name == name)
        habit.delete_instance()
        click.echo(f"Successfully deleted habit '{name}'")
    except Exception as e:
        click.echo(f"Error deleting habit '{name}'")


@cli.command()
@click.argument('name')
def play(name):
    """Exercise a habit"""
    # Get habit from database
    try:
        habit = Habit.get(Habit.name == name)
    except DoesNotExist:
        click.echo(f"Habit '{name}' was not found")
        return

    session = Session(habit)
    session.start()

    click.echo(f"{click.style('♪♪♪', blink=True)} Playing {click.style(name.capitalize(), fg='green')} "
               f"{click.style('(Press Ctrl+C to stop)', fg='bright_black')}")
    
    last_state = SessionStatus.ACTIVE
    try:
        while session.is_active():
            current_state = session.get_status()
            
            # Display state changes
            if current_state != last_state:
                if session.is_paused():
                    click.secho(f"\n⏸ Pausing due to inactivity ({session.get_transition_reason()})", fg='bright_red')
                elif current_state == SessionStatus.ACTIVE and last_state == SessionStatus.PAUSED:
                    click.echo(click.style(f"\nResuming due to activity detection", fg='bright_green'))
                last_state = current_state

            message = '' if session.is_paused() else get_friendly_elapsed(session.get_elapsed_time())
            click.secho(f"\r{message}", bold=True, nl=False)
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if session.is_ended():
            click.secho(f"Ending session due to extended inactivity", fg='bright_black')

        # Signal all threads to stop and wait until they finish
        session.end()
        session.join()

        active_time = session.get_elapsed_time()
        total_time = int(time.time() - session.start_time)
        paused_time = total_time - active_time
        
        click.echo(f"\nSession lasted {get_friendly_elapsed(active_time)}")
        if paused_time > 0:
            click.echo(f"Paused time: {get_friendly_elapsed(paused_time)}")
            click.echo(f"Total time: {get_friendly_elapsed(total_time)}")


@cli.command()
@click.argument('name', required=False)
def stats(name):
    """Show statistics for a specific habit or all habits."""
    if name:
        try:
            habit = Habit.get(Habit.name == name)
            _display_habit_stats(habit)
        except DoesNotExist:
            click.echo(f"Habit '{name}' not found")
    else:
        habits = list(Habit.select())
        if not habits:
            click.echo("No habits found")
            return
        _display_all_habits_stats(habits)


def _display_habit_stats(habit):
    """Display detailed statistics for a single habit."""
    schedule = habit.get_schedule()
    scale = schedule.get_scale()

    click.echo(f"\n=== {habit.name.upper()} ===")
    click.echo(f"Schedule: {habit.schedule}")
    click.echo(f"Created: {get_friendly_datetime(habit.created_at)}")
    click.echo(f"Started: {get_friendly_datetime(habit.started_at)}")
    click.echo(f"Next session: {get_friendly_datetime(schedule.get_next_task(datetime.now()), scale)}")
    
    if habit.allocated_time:
        click.echo(f"Allocated time per period: {get_friendly_elapsed(habit.allocated_time)}")
    if habit.inactivity_threshold:
        click.echo(f"Tracking timeout: {get_friendly_elapsed(habit.inactivity_threshold)}")
    
    # Show trackers
    trackers = list(habit.trackers.where(HabitTracker.is_enabled == True))
    if trackers:
        click.echo(f"\nTrackers ({len(trackers)}):")
        for tracker in trackers:
            click.echo(f"  • {tracker.tracker}{tracker.get_config()}")
    else:
        click.echo("\nNo trackers configured")

    buckets = habit.get_activity_buckets()

    print(f"\nLatest activity:")

    if not buckets:
        click.echo("No sessions recorded yet")
        return

    for bucket in islice(buckets, 5):
        start = get_friendly_datetime(bucket.start, scale)
        end = get_friendly_datetime(bucket.end, scale)
        duration = get_friendly_elapsed(bucket.net_duration)
        click.echo(f"• {start if start == end else f'{start} to {end}'} | Net duration: {duration} | Sessions: {bucket.sessions}")

    print(f"\nMilestones:")
    print(f"• Current streak: {habit.get_streak()}")
    print(f"• Longest streak: {habit.get_longest_streak()}")
    print(f"• Total time spent: {get_friendly_elapsed(analytics.get_time_spent(buckets))}")

    total_buckets = len(buckets)
    previous_tasks = len(schedule.get_previous_tasks(get_timespan(schedule.start)))
    print(f"• Tasks done: {total_buckets}")
    print(f"• Tasks vs schedule (all time): {analytics.get_task_vs_schedule_ratio(total_buckets, previous_tasks) * 100:.2f}%")

def _display_all_habits_stats(habits):
    """Display summary statistics for all habits."""
    click.echo(f"\n=== Habits ({len(habits)}) ===")
    for habit in habits:
        click.echo(f'- {habit.name}\n'
                   f'   - Schedule: {habit.schedule.capitalize()}\n'
                   f'   - Started: {get_friendly_datetime(habit.started_at, habit.get_schedule().get_scale())}')

    click.echo(f"\n=== Habits by periodicity ===")
    for schedule, group in analytics.group_habits_by_schedule(habits):
        click.echo(f'- {schedule.capitalize()}: {','.join(h.name for h in group)}')
    
    click.echo(f"\n=== Milestones ===")
    longest_streak_habit = analytics.get_habit_with_longest_streak(habits)
    click.echo(f"Longest streak of all habits: {longest_streak_habit.get_longest_streak()} ({longest_streak_habit.name})")


if __name__ == '__main__':
    cli()