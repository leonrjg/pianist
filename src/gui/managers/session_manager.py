"""
Session Manager - Manages session tracking in isolated subprocesses.

The worker process runs the Session (including native trackers like pynput/CGEventTap)
in isolation from the Qt event loop. It never writes to the database.

All SQLite writes happen in the monitor thread (this process) via the result queue,
eliminating the concurrent-write problem from the old design where the worker process
also wrote Log records.
"""

import multiprocessing
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal

from core.habit.log import Log
from ..constants import Session as SessionConstants


def session_worker_process(habit_id, habit_name, command_queue, result_queue):
    """
    Worker process: runs Session tracking in isolation from Qt.

    Never writes to the database. Sends session stats in the 'ended' message
    so the monitor thread can do the final Log write.
    """
    try:
        import time
        from core.session import Session
        from core.habit.habit import Habit

        habit = Habit.get(Habit.id == habit_id, Habit.deleted_at.is_null())
        session = Session(habit, persist=False)  # No DB writes in subprocess
        session.start()

        while True:
            try:
                if not command_queue.empty():
                    command = command_queue.get_nowait()
                    if command == 'stop':
                        break
                    elif isinstance(command, tuple) and command[0] == 'adjust_time':
                        session.adjust_time(command[1])
                        result_queue.put(('elapsed', habit_id, session.get_elapsed_time()))

                result_queue.put(('elapsed', habit_id, session.get_elapsed_time(), session.is_paused()))
                time.sleep(1)

            except Exception as e:
                result_queue.put(('error', habit_id, str(e)))
                break

        session.end(ended_by="stopped")
        result_queue.put(('ended', habit_id, {
            'idle_time': int(session.total_paused_time),
            'ended_by': session.transition_reason,
            'offset': session.time_adjustment_offset,
        }))

    except Exception as e:
        try:
            result_queue.put(('error', habit_id, str(e)))
            result_queue.put(('ended', habit_id, {}))
        except Exception:
            pass


class SessionManager(QThread):
    """
    Manages session subprocesses and handles all database persistence.

    The worker subprocess never writes to SQLite. This thread receives session
    events via a result queue and performs all Log writes itself, so there are
    no concurrent writers across processes.
    """

    elapsed_updated = pyqtSignal(object, int)  # habit_id, elapsed_seconds
    session_ended = pyqtSignal(object)          # habit_id
    error_occurred = pyqtSignal(str)            # error message

    def __init__(self):
        super().__init__()
        self._processes: dict = {}   # habit_id -> (process, command_queue, result_queue)
        self._logs: dict = {}        # habit_id -> Log
        self._paused_since: dict = {}  # habit_id -> datetime when inactivity started
        self.running = True

    # ------------------------------------------------------------------
    # Public API (called from main thread)
    # ------------------------------------------------------------------

    def start_session(self, habit) -> None:
        """Start a session subprocess and create the initial Log record."""
        try:
            log = Log.create(habit=habit, start=datetime.now())

            command_queue = multiprocessing.Queue()
            result_queue = multiprocessing.Queue()

            process = multiprocessing.Process(
                target=session_worker_process,
                args=(habit.id, habit.name, command_queue, result_queue)
            )
            process.start()

            self._processes[habit.id] = (process, command_queue, result_queue)
            self._logs[habit.id] = log

        except Exception as e:
            self.error_occurred.emit(f"Failed to start session: {e}")

    def stop_session(self, habit_id: int) -> None:
        """Send stop command to a running session subprocess."""
        if habit_id in self._processes:
            _, command_queue, _ = self._processes[habit_id]
            try:
                command_queue.put('stop')
            except Exception as e:
                self.error_occurred.emit(f"Error stopping session: {e}")

    def has_active_session(self, habit_id: int) -> bool:
        """Return True if a subprocess is running for this habit."""
        return habit_id in self._processes

    def is_session_active(self) -> bool:
        """Return True if any session subprocess is running."""
        return len(self._processes) > 0

    def adjust_session_time(self, habit_id: int, delta_seconds: int) -> None:
        """Forward a time adjustment command to a running session."""
        if habit_id in self._processes:
            _, command_queue, _ = self._processes[habit_id]
            try:
                command_queue.put(('adjust_time', delta_seconds))
            except Exception as e:
                self.error_occurred.emit(f"Error adjusting session time: {e}")

    def cleanup(self) -> None:
        """Stop all sessions and wait briefly for them to send final stats."""
        self.running = False

        for habit_id, (process, command_queue, _) in list(self._processes.items()):
            try:
                command_queue.put('stop')
            except Exception:
                pass

        self.msleep(500)
        self._processes.clear()

        # Finalize any logs that didn't get a clean 'ended' message
        for habit_id in list(self._logs.keys()):
            self._finalize_log(habit_id, {})

    # ------------------------------------------------------------------
    # Monitor loop (QThread)
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Poll subprocesses for messages and handle session lifecycle."""
        while self.running:
            from core.settings.service import SettingsService
            timeout_seconds = SettingsService.get('session.timeout_seconds', 0)

            for habit_id, (process, command_queue, result_queue) in list(self._processes.items()):
                try:
                    # Drain result queue
                    while not result_queue.empty():
                        try:
                            message = result_queue.get_nowait()
                            msg_type = message[0]
                            msg_habit_id = message[1]
                            data = message[2] if len(message) > 2 else None

                            if msg_type == 'elapsed':
                                elapsed, is_paused = data, message[3] if len(message) > 3 else False
                                self.elapsed_updated.emit(msg_habit_id, elapsed)
                                if is_paused:
                                    self._paused_since.setdefault(msg_habit_id, datetime.now())
                                else:
                                    self._paused_since.pop(msg_habit_id, None)
                            elif msg_type == 'ended':
                                self._finalize_log(msg_habit_id, data or {})
                                self._processes.pop(msg_habit_id, None)
                                self._paused_since.pop(msg_habit_id, None)
                                self.session_ended.emit(msg_habit_id)
                            elif msg_type == 'error':
                                self.error_occurred.emit(data or "Unknown session error")

                        except Exception:
                            break

                    # Detect unexpected process death
                    if not process.is_alive() and habit_id in self._processes:
                        self._finalize_log(habit_id, {})
                        self._processes.pop(habit_id, None)
                        self._paused_since.pop(habit_id, None)
                        self.session_ended.emit(habit_id)

                    # Auto-end session after configured inactivity timeout
                    if timeout_seconds > 0 and habit_id in self._paused_since:
                        inactive_duration = (datetime.now() - self._paused_since[habit_id]).total_seconds()
                        if inactive_duration >= timeout_seconds:
                            self._paused_since.pop(habit_id, None)
                            command_queue.put('stop')

                except Exception as e:
                    self.error_occurred.emit(f"Session monitor error: {e}")

            self.msleep(SessionConstants.PROCESS_MONITOR_INTERVAL)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _finalize_log(self, habit_id: int, stats: dict) -> None:
        """Write the final Log record. Called from the monitor thread."""
        log = self._logs.pop(habit_id, None)
        if log:
            log.end = datetime.now()
            log.idle_time = int(stats.get('idle_time', 0))
            log.ended_by = stats.get('ended_by')
            log.offset = int(stats.get('offset', 0))

            from core.settings.service import SettingsService
            min_duration = SettingsService.get('session.min_duration_seconds', 0)
            if min_duration > 0:
                active_seconds = (log.end - log.start).total_seconds() - log.idle_time + log.offset
                if active_seconds < min_duration:
                    log.delete_instance()
                    return

            log.save()
