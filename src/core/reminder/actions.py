"""
Action handlers for reminder executions.

Supports three action types: open_link, random_line, show_text.
"""

import webbrowser
import subprocess
import random
import sys
from pathlib import Path


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
