# TODO

## AutoSessionManager Habit Updates
**Issue**: AutoSessionManager needs to be notified when habits are added/updated/removed, currently piano_window manually updates it which is wrong architecture.

**Solution**: Implement a signal-based system where:
- Habit model (or a HabitRegistry) emits signals when habits change
- AutoSessionManager listens to these signals and updates its habit list automatically
- Remove manual `self.auto_session_manager.habits = all_habits` updates from piano_window

**Affected locations**:
- `piano_window.py`: on_habit_updated_from_sheet(), refresh_habits()
