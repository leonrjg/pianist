"""
Action handlers for reminder executions.

Supports action types: open_link, random_line, show_text, anki_card.
"""

import os
import webbrowser
import subprocess
import random
import sys
import logging
from pathlib import Path
from typing import TYPE_CHECKING

# Set up logger
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .reminder import Reminder


class ActionHandler:
    """Handles execution of reminder actions."""

    # Snooze durations offered on habit reminder notifications: (label, minutes)
    SNOOZE_PRESETS = [("10m", 10), ("1h", 60), ("3h", 180), ("8h", 480), ("1d", 1440)]

    @classmethod
    def get_message(cls, reminder) -> str:
        """
        Get notification message for a reminder without executing action.

        Args:
            reminder: Reminder object with action_type and action_payload

        Returns:
            Text message for notification display
        """
        action_type = reminder.action_type
        payload = reminder.action_payload

        if getattr(reminder, 'habit_id', None):
            from core.reminder.service import ReminderService
            return ReminderService.get_habit_message(reminder)

        if action_type == 'open_link':
            return f"Opening: {payload}"
        elif action_type == 'random_line':
            return cls._handle_random_line(payload)
        elif action_type == 'show_text':
            return payload or ""
        elif action_type == 'anki_card':
            return cls._handle_anki_card(reminder, payload)
        else:
            return "Reminder triggered"

    @classmethod
    def execute(cls, reminder) -> None:
        """
        Execute the reminder's action.

        Args:
            reminder: Reminder object with action_type and action_payload
        """
        action_type = reminder.action_type
        payload = reminder.action_payload

        if getattr(reminder, 'habit_id', None):
            return

        if action_type == 'open_link':
            cls._execute_open_link(payload)
        elif action_type == 'random_line':
            pass  # Message already retrieved in get_message
        elif action_type == 'show_text':
            pass  # No action needed, just display

    @classmethod
    def _execute_open_link(cls, payload: str) -> None:
        """
        Open a URL or file path.

        Args:
            payload: URL (http://, https://) or file path (file://)
        """
        if payload.startswith('file://'):
            # Handle file:// protocol
            file_path = payload[7:]  # Remove 'file://'
            if sys.platform == 'darwin':
                subprocess.run(['open', file_path], check=True)
            elif sys.platform == 'win32':
                subprocess.run(['start', '', file_path], shell=True, check=True)
            else:  # Linux
                subprocess.run(['xdg-open', file_path], check=True)
        else:
            # Handle HTTP/HTTPS URLs
            webbrowser.open(payload)

    @classmethod
    def _handle_random_line(cls, payload: str) -> str:
        """
        Read a random line from a text file.

        Args:
            payload: Path to text file

        Returns:
            Random line from the file
        """
        try:
            file_path = Path(payload).expanduser()
            if not file_path.exists():
                return f"File not found: {payload}"

            with open(file_path, 'r', encoding='utf-8') as f:
                raw_lines = [line.strip() for line in f if line.strip()]

            processed_lines = [
                cls._postprocess_random_line(line, file_path).strip()
                for line in raw_lines
            ]
            lines = [line for line in processed_lines if line]

            if not lines:
                return "File is empty"

            return random.choice(lines)
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @classmethod
    def _postprocess_random_line(cls, line: str, file_path: Path) -> str:
        """Apply postprocessing for lines read from files."""
        processors = [cls._strip_markdown_list_prefix]
        for processor in processors:
            line = processor(line, file_path)
        return line

    @staticmethod
    def _strip_markdown_list_prefix(line: str, file_path: Path) -> str:
        """Strip '- ' list prefixes for markdown files."""
        if file_path.suffix.lower() == ".md" and line.startswith("- ") and not line.startswith("- ["):
            return line[2:].lstrip()
        return line

    @classmethod
    def _handle_show_text(cls, payload: str) -> str:
        """
        Return text payload as-is.

        Args:
            payload: Text to display

        Returns:
            The payload text
        """
        return payload

    @classmethod
    def _handle_anki_card(cls, reminder, deck_name: str) -> str:
        """
        Fetch Anki card and return front.

        Args:
            reminder: Reminder object (for caching)
            deck_name: Name of Anki deck

        Returns:
            Front of the card
        """
        from core.integrations.anki_service import AnkiService, AnkiConnectError

        try:
            card = AnkiService.get_card(deck_name, reminder.id)
            return card.front
        except AnkiConnectError as e:
            return f"Anki error: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    @classmethod
    def _make_snooze_button(cls, get_toast, reminder, on_back, subtitle):
        """Build a 'Snooze' button that swaps the toast to a preset-duration sub-view.

        Shared by habit and fixed reminder notifications so both offer the same
        snooze choices (see :attr:`SNOOZE_PRESETS`).

        Args:
            get_toast: Zero-arg callable returning the live toast (late-bound, as
                the toast is created after the buttons that reference it).
            reminder: Reminder to snooze.
            on_back: Callback restoring the toast's primary buttons.
            subtitle: Title shown on the preset view and in the confirmation.
        """
        def show_presets():
            from core.reminder.service import ReminderService

            def make_preset(label, minutes):
                def do_snooze():
                    try:
                        ReminderService.snooze(reminder, minutes)
                        get_toast().update_content(
                            title="Snoozed",
                            message=f"{subtitle} snoozed for {label}",
                            buttons=[],
                            auto_close_after=1500
                        )
                    except Exception as e:
                        logger.exception("Error snoozing reminder")
                        get_toast().update_content(
                            title="Error",
                            message=f"Failed to snooze: {str(e)}",
                            buttons=[],
                            auto_close_after=3000
                        )
                return {"label": label, "callback": do_snooze, "color": "rgba(90, 90, 110, 160)"}

            buttons = [make_preset(label, minutes) for label, minutes in cls.SNOOZE_PRESETS]
            buttons.append({"label": "Back", "callback": on_back, "color": "rgba(90, 90, 110, 160)"})
            get_toast().update_content(
                title=subtitle,
                message="Snooze for…",
                buttons=buttons,
            )

        return {"label": "Snooze", "callback": show_presets, "color": "rgba(90, 90, 110, 160)"}

    @classmethod
    def show_notification_for_action(cls, reminder: 'Reminder', message: str, urgency: str = 'normal'):
        """
        Orchestrate notification flow based on action type.

        Handles different interaction patterns:
        - anki_card: Two-phase (show front → reveal back → rate)
        - Others: Simple notification

        Args:
            reminder: Reminder being fired
            message: Message to display (from get_message)
            urgency: Urgency level
        """
        from core.notification.service import NotificationService
        from core.integrations.anki_service import AnkiService

        notification_service = NotificationService.get_instance()

        # Suppress a fresh notification while one for this reminder is still on screen.
        if notification_service.is_showing_task(reminder.id):
            logger.info("Reminder %s already has a visible notification — skipping", reminder.id)
            return

        if getattr(reminder, 'habit_id', None):
            from core.reminder.service import ReminderService

            task_dt = ReminderService.get_habit_task_datetime(reminder)
            toast = None

            def mark_done():
                try:
                    ReminderService.mark_habit_task_done(reminder, task_dt)
                    toast.update_content(
                        title="Done",
                        message=f"Marked {reminder.habit.name} as done",
                        buttons=[],
                        auto_close_after=1500
                    )
                except Exception as e:
                    logger.exception("Error marking habit reminder done")
                    toast.update_content(
                        title="Error",
                        message=f"Failed to mark done: {str(e)}",
                        buttons=[],
                        auto_close_after=3000
                    )

            def skip_occurrence():
                try:
                    ReminderService.skip_occurrence(reminder)
                    toast.update_content(
                        title="Skipped",
                        message=f"Reminder skipped until next occurrence",
                        buttons=[],
                        auto_close_after=1500
                    )
                except Exception as e:
                    logger.exception("Error skipping reminder occurrence")

            def show_primary():
                toast.update_content(
                    title=reminder.habit.name,
                    message=message,
                    buttons=primary_buttons(),
                )

            def primary_buttons():
                return [
                    cls._make_snooze_button(lambda: toast, reminder, show_primary, reminder.habit.name),
                    {
                        "label": "Skip",
                        "callback": skip_occurrence,
                        "color": "rgba(90, 90, 110, 160)",
                    },
                    {
                        "label": "Mark as done",
                        "callback": mark_done,
                        "color": "rgba(100, 180, 120, 200)",
                        "primary": True,
                    },
                ]

            toast = notification_service.show_toast(
                reminder.habit.name,
                message,
                urgency=urgency,
                buttons=primary_buttons(),
                dedup_key=reminder.id
            )
            return

        # Anki card: Two-phase interaction (single toast, updated in-place)
        if reminder.action_type == 'anki_card':
            from core.integrations.anki_service import AnkiConnectError

            card = AnkiService.get_cached_card(reminder.id)
            if not card:
                notification_service.show_toast(reminder.name, message, 5000, 'normal', dedup_key=reminder.id)
                return

            deck_name = reminder.action_payload
            toast = None  # Will be set after creation

            def show_answer(active_card):
                """Update toast to show back with rating buttons."""
                def rate(ease: int, label: str):
                    logger.info(f"[ANKI RATING] User clicked '{label}' (ease={ease}) for card {active_card.card_id}")
                    logger.info(f"[ANKI RATING] Card details: deck={active_card.deck_name}")
                    logger.info(f"[ANKI RATING] Reminder ID: {reminder.id}, Reminder name: {reminder.name}")

                    try:
                        logger.info(f"[ANKI RATING] Calling submit_rating...")
                        AnkiService.submit_rating(active_card.card_id, ease)
                        logger.info(f"[ANKI RATING] ✓ submit_rating completed successfully")

                        next_review = AnkiService.get_next_review_summary(active_card.card_id)
                        due_str = f"next review: {next_review.label}" if next_review else ""

                        AnkiService.clear_cache(reminder.id)
                        logger.info(f"[ANKI RATING] Cache cleared for reminder {reminder.id}")

                        def undo():
                            AnkiService.recache_card(reminder.id, active_card)
                            show_question(active_card)

                        toast.update_content(
                            title="✓ Sent to Anki",
                            message=f"Marked as {label}" + (f", {due_str}" if due_str else ""),
                            buttons=[{
                                "label": "Undo",
                                "callback": undo,
                                "color": "rgba(90, 90, 110, 160)",
                            }, {
                                "label": "Next card",
                                "callback": fetch_next_card,
                                "color": "rgba(100, 140, 180, 200)",
                                "primary": True,
                            }],
                            auto_close_after=5000
                        )
                        logger.info(f"[ANKI RATING] Toast updated to show success")

                    except AnkiConnectError as e:
                        logger.error(f"[ANKI RATING] ✗ AnkiConnectError occurred: {str(e)}")
                        logger.error(f"[ANKI RATING] Card ID: {active_card.card_id}, Ease: {ease}, Label: {label}")
                        toast.update_content(
                            title="Error",
                            message=f"Failed to submit rating: {str(e)}",
                            buttons=[],
                            auto_close_after=3000
                        )

                    except Exception as e:
                        logger.error(f"[ANKI RATING] ✗ Unexpected error: {type(e).__name__}: {str(e)}")
                        logger.error(f"[ANKI RATING] Card ID: {active_card.card_id}, Ease: {ease}")
                        import traceback
                        logger.error(f"[ANKI RATING] Traceback:\n{traceback.format_exc()}")
                        toast.update_content(
                            title="Error",
                            message=f"Unexpected error: {str(e)}",
                            buttons=[],
                            auto_close_after=3000
                        )

                rating_buttons = [
                    make_edit_button(active_card),
                    {"label": "Again", "callback": lambda: rate(1, "Again"), "color": "rgba(160, 50, 50, 200)"},
                    {"label": "Hard", "callback": lambda: rate(2, "Hard"), "color": "rgba(184, 134, 11, 200)"},
                    {"label": "Good", "callback": lambda: rate(3, "Good"), "color": "rgba(140, 170, 90, 200)"},
                    {"label": "Easy", "callback": lambda: rate(4, "Easy"), "color": "rgba(100, 180, 120, 200)"},
                ]

                toast.update_content(
                    title=f"{active_card.deck_name} - Answer",
                    message=active_card.back,
                    buttons=rating_buttons,
                )

            _edit_icon = os.path.join(os.path.dirname(__file__), '..', '..', 'gui', 'icons', 'edit.svg')

            def make_edit_button(active_card):
                def edit():
                    try:
                        AnkiService.open_in_editor(active_card.card_id)
                    except AnkiConnectError as e:
                        toast.update_content(title="Error", message=str(e), buttons=[], auto_close_after=2000)
                return {"label": "Edit", "callback": edit, "icon": _edit_icon}

            def make_question_buttons(active_card):
                """Build buttons for the question phase: Bury, Suspend, Show Answer."""
                def bury():
                    try:
                        AnkiService.bury_card(active_card.card_id)
                        AnkiService.clear_cache(reminder.id)
                        toast.update_content(
                            title="Buried",
                            message="Card buried until tomorrow",
                            buttons=[],
                            auto_close_after=2000
                        )
                    except AnkiConnectError as e:
                        toast.update_content(title="Error", message=str(e), buttons=[], auto_close_after=2000)

                def suspend():
                    try:
                        AnkiService.suspend_card(active_card.card_id)
                        AnkiService.clear_cache(reminder.id)
                        toast.update_content(
                            title="Suspended",
                            message="Card suspended",
                            buttons=[],
                            auto_close_after=2000
                        )
                    except AnkiConnectError as e:
                        toast.update_content(title="Error", message=str(e), buttons=[], auto_close_after=2000)

                return [
                    {"label": "Bury", "callback": bury, "color": "rgba(90, 90, 110, 160)"},
                    {"label": "Suspend", "callback": suspend, "color": "rgba(90, 90, 110, 160)"},
                    make_edit_button(active_card),
                    {"label": "Show Answer", "callback": lambda: show_answer(active_card), "color": "rgba(100, 140, 180, 200)", "primary": True},
                ]

            def show_question(new_card):
                """Update toast to show a card's front with action buttons."""
                toast.update_content(
                    title=f"{new_card.deck_name} - Question",
                    message=new_card.front,
                    buttons=make_question_buttons(new_card),
                )

            def fetch_next_card():
                """Fetch a new card from the same deck and display it."""
                try:
                    next_card = AnkiService.get_card(deck_name, reminder.id)
                    show_question(next_card)
                except AnkiConnectError as e:
                    toast.update_content(
                        title="No more cards",
                        message=str(e),
                        buttons=[],
                        auto_close_after=2000
                    )

            # Create toast showing first card's front
            toast = notification_service.show_toast(
                f"{card.deck_name} - Question",
                card.front,
                buttons=make_question_buttons(card),
                dedup_key=reminder.id
            )

        # Fixed reminders get the same preset snooze sub-view as habit reminders
        elif reminder.reminder_type == 'fixed':
            if urgency == 'high':
                duration = 15000
            elif urgency == 'low':
                duration = 5000
            else:
                duration = 12000

            toast = None

            def show_primary():
                toast.update_content(
                    title=reminder.name,
                    message=message,
                    buttons=primary_buttons(),
                )

            def primary_buttons():
                return [cls._make_snooze_button(lambda: toast, reminder, show_primary, reminder.name)]

            toast = notification_service.show_toast(
                reminder.name,
                message,
                duration,
                urgency,
                buttons=primary_buttons(),
                dedup_key=reminder.id
            )

        else:
            notification_service.show_reminder_notification(reminder.name, message, urgency, dedup_key=reminder.id)
