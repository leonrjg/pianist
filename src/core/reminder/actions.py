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

from PyQt6.QtCore import Qt

# Set up logger
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .reminder import Reminder


class ActionHandler:
    """Handles execution of reminder actions."""

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
    def show_notification_for_action(cls, reminder: 'Reminder', message: str, urgency: str = 'normal'):
        """
        Orchestrate notification flow based on action type.

        Handles different interaction patterns:
        - anki_card: Two-phase (show front → reveal back → rate)
        - SR reminders: Single-phase with feedback buttons
        - Others: Simple notification

        Args:
            reminder: Reminder being fired
            message: Message to display (from get_message)
            urgency: Urgency level
        """
        from core.notification.service import NotificationService
        from core.integrations.anki_service import AnkiService

        notification_service = NotificationService.get_instance()

        # Anki card: Two-phase interaction (single toast, updated in-place)
        if reminder.action_type == 'anki_card':
            from core.integrations.anki_service import AnkiConnectError

            card = AnkiService.get_cached_card(reminder.id)
            if not card:
                notification_service.show_toast(reminder.name, message, 5000, 'normal')
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

                        next_due = AnkiService.get_next_due_date(active_card.card_id)
                        from datetime import date as _date
                        if next_due and next_due > _date.today():
                            due_str = f"next review: {next_due.strftime('%b %-d')}"
                        elif next_due:
                            due_str = "next review: later today"
                        else:
                            due_str = ""

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
                            key_bindings={(Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier): undo},
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
                            key_bindings={},
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
                            key_bindings={},
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
                    key_bindings={
                        Qt.Key.Key_1: lambda: rate(1, "Again"),
                        Qt.Key.Key_2: lambda: rate(2, "Hard"),
                        Qt.Key.Key_3: lambda: rate(3, "Good"),
                        Qt.Key.Key_4: lambda: rate(4, "Easy"),
                    }
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
                    key_bindings={Qt.Key.Key_Space: lambda: show_answer(new_card)}
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
                key_bindings={Qt.Key.Key_Space: lambda: show_answer(card)}
            )

        # SR reminder: Single-phase with feedback
        elif reminder.reminder_type == 'sr':
            from core.reminder.service import ReminderService

            # Build buttons first (closure will capture toast after creation)
            toast = None  # Will be set below

            def feedback(quality: int, label: str):
                ReminderService.apply_feedback(reminder, quality)
                # Update to confirmation
                toast.update_content(
                    title=f"✓ {label}",
                    message="Feedback recorded",
                    buttons=[],
                    auto_close_after=1000
                )

            buttons = [
                {"label": "Again", "callback": lambda: feedback(0, "Again"), "color": "rgba(160, 50, 50, 200)"},
                {"label": "Hard", "callback": lambda: feedback(1, "Hard"), "color": "rgba(184, 134, 11, 200)"},
                {"label": "Good", "callback": lambda: feedback(2, "Good"), "color": "rgba(140, 170, 90, 200)"},
                {"label": "Easy", "callback": lambda: feedback(3, "Easy"), "color": "rgba(100, 180, 120, 200)"}
            ]

            # Create toast with buttons already set - no timers start
            toast = notification_service.show_toast(
                reminder.name,
                message,
                urgency=urgency,
                buttons=buttons
            )

        # Simple notification
        else:
            notification_service.show_reminder_notification(reminder.name, message, urgency)
