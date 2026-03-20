<img width="1792" height="576" alt="logo" src="https://github.com/user-attachments/assets/715ad4ff-7568-462d-ae48-822c7a3ca6b9" />

Pianist is a habit and activity tracking app with a piano-themed interface. It runs as a small floating window that stays on top of other windows.

## How it works

Your habits appear as piano keys. Click a key to log a session. A slide-out panel gives access to everything else.

<img width="1368" height="600" alt="image" src="https://github.com/user-attachments/assets/542810bf-be8d-4fd6-8389-a358679ce627" />

## Features

**Habit scheduling** — Each habit has a schedule: hourly, daily, weekly, monthly, or exponential (intervals that grow over time, like spaced repetition). The app tracks when each habit is due and shows upcoming tasks.

**Activity tracking** — Optionally attach a tracker to a habit so sessions pause automatically during inactivity and resume when you're active again. Trackers can monitor keyboard/mouse activity or watch for a specific window title (e.g. a particular app or browser tab).

**Reminders** — Reminders fire toast notifications on a schedule. They can open a link, show a piece of text, pick a random line from a file, or show an Anki flashcard. Scheduling can be spaced repetition (interval adjusts based on your rating) or randomized at a target frequency. Reminders can be limited to specific hours and to when a particular window is active.

**Anki integration** — Anki flashcards can be surfaced as reminders. Requires [Anki](https://apps.ankiweb.net) running with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on.

**Stats** — Streaks, completion rates, and a calendar view of your session history per habit.

**Mood tracking** — Log a daily mood score and see it alongside your productivity overview.

**Notes** — Each habit has a Markdown notes field.

**Manual tasks** — Add one-off tasks with an optional due date, with or without a linked habit.

## Installation

Requires Python 3.9 or later and PyQt6.

```bash
pip install PyQt6
pip install -r src/requirements.txt
```

Then run from the `src` directory:

```bash
python -m gui.main
```

## CLI

A command-line interface is available for scripting or agentic use. Run `python -m cli.cli --help` from the `src` directory for usage.
