<img width="1792" height="576" alt="logo" src="https://github.com/user-attachments/assets/715ad4ff-7568-462d-ae48-822c7a3ca6b9" />


<br /><br />
<p align="center">Activity and habit tracking application with basic activity monitoring.</p>

## Use case
<img width="1368" height="600" alt="image" src="https://github.com/user-attachments/assets/542810bf-be8d-4fd6-8389-a358679ce627" />


## Features

- **Multiple Schedule Types**: Daily, weekly, monthly, hourly, and exponential scheduling (spaced repetition-like)
- **Real-time Monitoring**: Monitor habits through OS window activity and I/O events
- **Analytics**: Streaks, completion rates
- **CLI**: Command-line interface
- **Session Management**: Interactive habit sessions with automatic pause/resume functionality based on monitoring

## CLI Commands
```bash
cd src

# Add or edit a habit
./pianist save "name" --schedule hourly|daily|weekly|monthly|exponential_3 [--duration minutes] [--timeout seconds] [--track io|window] [--track-args “keywords=app_name”]
./pianist delete name

# Exercise a habit - blocking until Ctrl+C is pressed
./pianist play "name"

# Exercise a habit - non-blocking
./pianist hit "name"

# Show list of habits and their data, longest streak overall, etc.
./pianist stats

# Show longest streak of the habit, completion rate, etc
./pianist stats "name"
```

## Installation

### Requirements

- Python 3.9 or later
- SQLite3 (included with Python)

### Setup

1. Clone or download the project
2. Navigate to the project directory
3. Install dependencies:
   ```bash
   pip install -r src/requirements.txt
   ```

### Optional: Load Test Data

To load predefined habits with 4 weeks of sample data for testing:

```bash
# From the root directory
sqlite3 src/habits.db < test_data.sql
```

This will create 7 sample habits:
- **Daily**: piano, emails
- **Weekly**: goal_review, meditation
- **Monthly**: budgeting
- **Hourly**: posture_check
- **Exponential (base 3)**: chess

## Usage

Navigate to the `src` directory for all commands:

```bash
cd src
```

#### Create a New Habit

```bash
# Create a simple daily habit
python cli.py save "reading" --schedule daily

# Create a habit with 45 min of allocated time and mouse/keyboard tracking
python cli.py save "code review" --schedule daily --duration 45 --track io

# Create a weekly habit tracking a browser tab, set minimum session length to 2h, and define a tolerance for inactivity of 30s
python cli.py save "chess" --schedule weekly --duration 120 --timeout 30 --track window --track-args "keywords=Chess.com"
```

#### Schedule Types

- `hourly`
- `daily`
- `weekly`
- `monthly`
- `exponential_3` - Exponentially increasing intervals in a spaced repetition fashion (base 3)

#### Start a Habit Session

```bash
# Non-interactive session
python cli.py hit piano

# Interactive session (Press Ctrl+C to end)
python cli.py play piano

# The session will:
# - Track your activity in real-time (if you configured any trackers)
# - Pause automatically during inactivity (if you configured any trackers)
# - Resume when activity is detected (if you configured any trackers)
# - Show elapsed time
```

#### View Habit Information and Stats

```bash
# View summary of all habits
python cli.py stats

# View detailed statistics for specific habit
python cli.py stats "piano"
```

Information displayed includes:
- Current and longest streaks
- Completion rates
- Total time spent
- Session history
- Next scheduled session

#### Delete a Habit

```bash
python cli.py delete "habit_name"
```

#### Trackers

Trackers automatically pause the session during inactivity periods, and resume once activity is detected.

**I/O Tracking** (`--track io`):
- Monitors keyboard and mouse activity

**Window Tracking** (`--track window`):
- Monitors active window titles
- Configure with `--track-args "keywords=App Name or Browser Tab Name"`

## (For Developers) Testing

Run the test suite from the project root:

```bash
# Run all tests
python -m pytest

# Run with coverage
coverage run -m pytest tests && coverage report
```

## Troubleshooting

### Common Issues

**No habits showing**:
```bash
python cli.py stats  # Check if any habits exist
sqlite3 habits.db < ../test_data.sql  # Load sample data
# Check that habits.db is located in the "src" folder
```

**Tracking not working**:
- I/O and Window trackers will not work unless they are given permissions; you will be prompted by your OS on the first use.
- WindowTracker: Verify that keywords match actual window titles (TODO: a command to do this will be provided in the future)
- Check the inactivity threshold setting

