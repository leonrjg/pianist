# Popup Screen Clamping

## Issue

Popup widgets positioned relative to a button or anchor point do not check screen
bounds before rendering. When the main window is near a screen edge, the popup
overflows and is partially clipped by the OS.

Affected widgets at time of writing:

- `AddTaskWidget` — positioned to the left of the "add task" button in the control panel
- `ThemedDatePicker` — positions its `TaskCalendarWidget` popup below the date button

Both were fixed by clamping `(x, y)` against `screen.availableGeometry()` before
calling `move()`. However, the fixes are ad hoc — each widget duplicates the same
clamping logic independently, and there is no structural mechanism to enforce or
suggest this for future popup widgets.

### Secondary ownership issue

`ThemedDatePicker` performs the positioning of `TaskCalendarWidget` inline inside
`_show_calendar()`, rather than delegating to the popup widget itself. This means
the popup does not own its screen-aware positioning — the caller does. If the same
calendar widget is reused elsewhere, it would need the same clamping logic duplicated
again.

---

## Proposal

### 1. Introduce `ScreenAwarePopup`

A base class using the Template Method pattern:

```python
class ScreenAwarePopup(QWidget):
    def show_at_position(self, pos: QPoint):
        self.adjustSize()
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = max(geo.left(), min(pos.x(), geo.right() - self.width()))
        y = max(geo.top(), min(pos.y(), geo.bottom() - self.height()))
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        self._after_shown()

    def _after_shown(self):
        """Override to run logic after the popup is shown (e.g. set focus)."""
        pass
```

Subclasses inherit screen-safe positioning by default. Clamping cannot be forgotten
because it is the only standard entry point.

### 2. Apply to `AddTaskWidget` and `TaskCalendarWidget`

Both inherit from `ScreenAwarePopup`. `AddTaskWidget._after_shown()` sets focus on
the title input. `TaskCalendarWidget` gains `show_at_position` for free.

### 3. Fix the ownership boundary in `ThemedDatePicker`

Once `TaskCalendarWidget` inherits `ScreenAwarePopup`, `ThemedDatePicker._show_calendar()`
replaces its inline positioning block with:

```python
self._calendar_popup.show_at_position(button_pos)
```

The popup owns its positioning. The caller supplies only the anchor point.
