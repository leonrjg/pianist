<img width="1792" height="576" alt="pianistborderv2" src="https://github.com/user-attachments/assets/d88cb723-8589-4edd-be4c-1e4d662704d5" />


<br /><br />
<p align="center">A habit tracking application with basic activity monitoring.</p>

## Features

- **Flexible Schedule Types**: Daily, weekly, monthly, hourly, and exponential scheduling (spaced repetition-like)
- **Real-time Monitoring**: Monitor habits through OS window activity and I/O events
- **Analytics**: Streak tracking, completion rates, and habit performance analysis
- **CLI**: Full command-line interface for habit management
- **Session Management**: Interactive habit sessions with pause/resume functionality based on monitoring

## Installation

### Requirements

- Python 3.7 or later
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
sqlite3 src/habits.db < test_data.sql
```

This will create 7 sample habits:
- **Daily habits**: piano_practice, morning_meditation
- **Weekly habits**: deep_work_session, language_study
- **Monthly habit**: financial_review
- **Hourly habit**: posture_check
- **Exponential (base 3) habit**: skill_challenge

## Usage

### Basic Commands

Navigate to the `src` directory for all commands:

```bash
cd src
```

#### Create a New Habit

```bash
# Create a simple daily habit
python cli.py save "daily_reading" --schedule daily

# Create a habit with allocated time and mouse/keyboard tracking
python cli.py save "workout" --schedule daily --duration 45 --track io

# Create a weekly habit with specific trackers
python cli.py save "coding" --schedule weekly --duration 120 --track window --track-args "keywords=project_name,VSCode,IntelliJ,Terminal"
```

#### Available Schedule Types

- `daily` - Every day
- `weekly` - Every 7 days
- `monthly` - Every month
- `hourly` - Every hour
- `exponential_3` - Exponentially increasing intervals (base 3)

#### Start a Habit Session

```bash
# Start an interactive session
python cli.py play "piano_practice"

# The session will:
# - Track your activity in real-time
# - Pause automatically during inactivity
# - Resume when activity is detected
# - Show elapsed time
# - Save session data to database
```

During a session:
- Press `Ctrl+C` to end manually
- Sessions pause automatically after the defined inactivity threshold
- Sessions end automatically after extended inactivity

#### View Habit Statistics

```bash
# View all habits summary
python cli.py stats

# View detailed statistics for specific habit
python cli.py stats piano_practice
```

Statistics include:
- Current and longest streaks
- Completion rates
- Total time spent
- Session history
- Next scheduled session
- Habit groupings by periodicity

#### Delete a Habit

```bash
python cli.py delete "habit_name"
```

### Advanced Usage

#### Habit Tracking Options

**I/O Tracking** (`--track io`):
- Monitors keyboard and mouse activity
- Pauses during inactivity periods
- Resumes when activity is detected

**Window Tracking** (`--track window`):
- Monitors active window titles
- Tracks time spent in relevant applications
- Configure with `--track-args "keywords=App1,App2"`

#### Example Tracking Configurations of Existing Habits

```bash
# Programming habit with IDE detection
python cli.py save "coding" --track window --track-args "keywords=VSCode,IntelliJ,Terminal,Sublime"

# Language learning with app detection
python cli.py save "spanish" --track window --track-args "keywords=Duolingo,Anki,Memrise"

# General focus time with I/O tracking
python cli.py save "deep_work" --track io
```

## Technical information

### Core Components

**Habit** (`src/habit/`):
- `Habit`: Core habit entity
- `Log`: Session records with timing data
- `Bucket`: Aggregated activity data

**Scheduling** (`src/schedule/`):
- `Schedule`: Base scheduling class
- `DailySchedule`: 24-hour intervals
- `WeeklySchedule`: 7-day intervals
- `MonthlySchedule`: Calendar month intervals
- `HourlySchedule`: 60-minute intervals
- `ExponentialSchedule`: Growing intervals

**Trackers** (`src/tracker/`):
- `Tracker`: Base tracker class
- `IOTracker`: Monitors keyboard/mouse activity
- `WindowTracker`: Monitors active window titles and program names

**Session Management** (`src/session.py`):
- Real-time activity tracking
- Pause/resume functionality
- Multi-threaded tracker coordination

### Database Schema

- **habit**: Core habit definitions with scheduling
- **log**: Session records with start/end times
- **habittracker**: Tracker configurations per habit

## Analytics Features

### Streak Tracking
 (accounting for allocated time requirements)
- Current Streak
- Longest Streak
- Completion Rate
- Time Spent
- Habits sorted by performance

## Testing

Run the test suite from the project root:

```bash
# Run all tests
python -m pytest

# Run specific test categories
python -m pytest tests/habit/
python -m pytest tests/schedule/
python -m pytest tests/test_analytics.py

# Run with coverage
python -m pytest --cov=. --cov-report=html
```

## Troubleshooting

### Common Issues

**No habits showing**:
```bash
python cli.py stats  # Check if any habits exist
sqlite3 habits.db < ../test_data.sql  # Load sample data
```

**Tracking not working**:
- Ensure tracker permissions for I/O monitoring
- Verify window keywords match actual application names
- Check inactivity threshold settings

