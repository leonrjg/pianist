"""
Session Process Manager - Handles session tracking in separate processes.

Extracted from the main GUI file to separate concerns.
"""

import os
import multiprocessing
from PyQt6.QtCore import QThread, pyqtSignal

from ..constants import Session as SessionConstants


def session_worker_process(habit_id, habit_name, command_queue, result_queue):
    """Worker process function that runs Session completely isolated"""
    try:
        # Import inside process to avoid Qt conflicts
        import time
        from core.session import Session
        from core.habit.habit import Habit

        # Reconstruct habit object in this process
        habit = Habit.get_by_id(habit_id)
        session = Session(habit)
        session.start()

        print(f"Session started for {habit_name} in process {os.getpid()}")

        # Main loop: handle commands and send updates
        while True:
            try:
                # Check for commands (non-blocking)
                if not command_queue.empty():
                    command = command_queue.get_nowait()
                    if command == 'stop':
                        break
                    elif command == 'get_elapsed':
                        elapsed = session.get_elapsed_time()
                        result_queue.put(('elapsed', habit_id, elapsed))

                # Send periodic elapsed time updates
                elapsed = session.get_elapsed_time()
                result_queue.put(('elapsed', habit_id, elapsed))

                time.sleep(1)  # Update every second

            except Exception as e:
                result_queue.put(('error', habit_id, str(e)))
                break

        # Clean shutdown
        session.end(ended_by="process_stop")
        result_queue.put(('ended', habit_id))
        print(f"Session ended for {habit_name}")

    except Exception as e:
        try:
            result_queue.put(('error', habit_id, str(e)))
        except Exception:
            pass  # Queue might be closed


class SessionProcessManager(QThread):
    """Manages communication with session processes"""

    elapsed_updated = pyqtSignal(int, int)  # habit_id, elapsed_seconds
    session_ended = pyqtSignal(int)  # habit_id
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self):
        super().__init__()
        self.processes = {}  # habit_id -> (process, command_queue, result_queue)
        self.running = True

    def start_session(self, habit):
        """Start a session in a separate process"""
        try:
            # Create communication queues
            command_queue = multiprocessing.Queue()
            result_queue = multiprocessing.Queue()

            # Start worker process
            process = multiprocessing.Process(
                target=session_worker_process,
                args=(habit.id, habit.name, command_queue, result_queue)
            )
            process.start()

            # Store process info
            self.processes[habit.id] = (process, command_queue, result_queue)
            print(f"Started session process for {habit.name}")

        except Exception as e:
            self.error_occurred.emit(f"Failed to start session process: {str(e)}")

    def stop_session(self, habit_id):
        """Stop a session process - non-blocking"""
        if habit_id in self.processes:
            process, command_queue, result_queue = self.processes[habit_id]
            try:
                # Send stop command
                command_queue.put('stop')
                print(f"Sent stop command to session process for habit {habit_id}")

                # Don't wait for process - let the monitoring loop handle cleanup
                # The run() method will detect when process ends and clean up

            except Exception as e:
                self.error_occurred.emit(f"Error stopping session: {str(e)}")

    def has_active_session(self, habit_id):
        """Check if a habit has an active session"""
        return habit_id in self.processes

    def is_session_active(self):
        """Check if any session is active"""
        return len(self.processes) > 0

    def run(self):
        """Monitor all session processes for updates"""
        while self.running:
            # Check all result queues for updates
            for habit_id, (process, command_queue, result_queue) in list(self.processes.items()):
                try:
                    # Check if process is still alive
                    if not process.is_alive():
                        self.session_ended.emit(habit_id)
                        del self.processes[habit_id]
                        print(f"Session process for habit {habit_id} has ended")
                        continue

                    # Check for results (non-blocking)
                    while not result_queue.empty():
                        try:
                            message = result_queue.get_nowait()
                            msg_type, msg_habit_id, data = message

                            if msg_type == 'elapsed':
                                self.elapsed_updated.emit(msg_habit_id, data)
                            elif msg_type == 'ended':
                                self.session_ended.emit(msg_habit_id)
                                if msg_habit_id in self.processes:
                                    del self.processes[msg_habit_id]
                            elif msg_type == 'error':
                                self.error_occurred.emit(data)

                        except:
                            break  # No more messages

                except Exception as e:
                    self.error_occurred.emit(f"Process monitoring error: {str(e)}")

            # Small delay to prevent busy waiting
            self.msleep(SessionConstants.PROCESS_MONITOR_INTERVAL)

    def cleanup(self):
        """Clean up all processes"""
        self.running = False

        # Send stop commands to all processes
        for habit_id, (process, command_queue, result_queue) in list(self.processes.items()):
            try:
                command_queue.put('stop')
            except:
                pass

        # Give processes a moment to stop gracefully
        self.msleep(500)

        self.processes.clear()
