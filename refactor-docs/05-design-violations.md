# Design Violations and Refactoring Plan

Critical violations of DRY, Separation of Concerns, and package hygiene that
complicate maintenance, extensibility, and correctness.

---

## 1. Theme accessor duplicated across 27+ files

Every widget file defines its own module-level helper to reach the current theme:

```python
def _t():
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current
```

This identical function appears in 27 files. Any change to the access pattern
(thread safety, injection, testing) requires editing every copy independently.

### Fix

Export a single `current_theme()` from `gui.themes` and import it everywhere:

```python
# gui/themes/__init__.py
from .manager import ThemeManager

def current_theme():
    return ThemeManager.get_instance().current
```

All 27 files replace their local `_t()` / `_theme()` with:

```python
from gui.themes import current_theme as _t
```

One owner, one definition. If the access pattern later changes (e.g. inject
a theme into a context object), the change happens in one place.

---

## 2. `_qcolor()` / `_parse_rgb()` parser duplicated with diverging behavior

Three independent implementations exist:

| Location                      | Handles `rgba()`? | Default alpha | Override alpha? |
|-------------------------------|-------------------|---------------|-----------------|
| `music_sheet_widget.py:26`    | Yes               | 255           | Yes             |
| `calendar_page.py:25`         | No                | 255           | No              |
| `constants.py:9` `_parse_rgb` | No                | 255 (opaque)  | No              |

Any `rgba(...)` string passed to the calendar variant silently produces a wrong
color. Adding new theme tokens that use `rgba()` will surface this as
theme-dependent visual bugs.

### Fix

Consolidate into a single utility in the theme package:

```python
# gui/themes/color.py
from PyQt6.QtGui import QColor

def parse_color(s: str, alpha: int | None = None) -> QColor:
    """Parse 'rgb(r,g,b)' or 'rgba(r,g,b,a)' into QColor."""
    s = s.strip()
    if s.startswith('rgba('):
        parts = s[5:-1].split(',')
        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
        a = int(float(parts[3])) if len(parts) > 3 else 255
    elif s.startswith('rgb('):
        parts = s[4:-1].split(',')
        r, g, b, a = int(parts[0]), int(parts[1]), int(parts[2]), 255
    else:
        return QColor(s)
    if alpha is not None:
        a = alpha
    return QColor(r, g, b, a)
```

Delete the three local copies. All callers import `from gui.themes.color import
parse_color`.

---

## 3. `sys.path.insert` hacks in 13 GUI modules

Files like `habit_detail_page.py`, `calendar_page.py`, `settings_page.py`, etc.
manipulate `sys.path` at import time:

```python
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.db import db
```

This exists because the app is run with `src/` as the working directory rather
than being installed as a proper package. Every file encodes its exact
filesystem depth; moving a file breaks its imports at runtime, not at lint time.

### Fix

Make the project a proper installable package. The layout becomes:

```
pianist/
  pyproject.toml
  src/
    pianist/            # top-level package (renamed from bare src/)
      __init__.py
      __main__.py       # python -m pianist
      core/
        ...
      gui/
        ...
      cli/
        ...
```

`pyproject.toml` declares the package root:

```toml
[project]
name = "pianist"
version = "0.1.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
where = ["src"]

[project.scripts]
pianist = "pianist.gui.main:main"
pianist-cli = "pianist.cli.cli:main"
```

`__main__.py`:

```python
from pianist.gui.main import main
main()
```

After this:
- All imports are absolute from `pianist.*` (e.g., `from pianist.core.db import db`).
- Every `sys.path.insert` line is deleted.
- The app is run with `python -m pianist` or `pianist` (entry point) from any
  directory, not just `src/`.
- `pip install -e .` makes the package importable in development.

---

## 4. Widgets hardcode colors despite the theme system

`WoodDropdown` (`wood_dropdown.py:26-42`) hardcodes `rgb(120, 80, 50)` and
`rgb(160, 110, 70)` in its stylesheet. These are the wood theme's link colors.
Under sakura, this widget renders with mismatched colors.

`WoodButton`'s "danger" variant (`wood_form_widgets.py:236-252`) hardcodes
`rgba(180, 50, 50, ...)` with no corresponding token in `Theme`. New themes
inherit this one hardcoded red.

### Fix

1. Add `danger` and `danger_hover` fields to the `Theme` dataclass.
2. Replace every hardcoded color in `WoodDropdown` and `WoodButton.danger`
   with theme token reads.
3. Audit all widgets for remaining hardcoded `rgb(...)` literals that should
   come from the theme; a grep for `rgb(` inside `setStyleSheet` calls that
   do not interpolate a theme variable will catch them.

---

## 5. `wood_styles.py` is a dead compatibility shim with duplicated data

`wood_styles.py` retains a `VINTAGE_COLORS` dict whose values duplicate the
`wood.py` theme definition. The comment says it exists for backward
compatibility, but nothing imports `VINTAGE_COLORS` — grep confirms zero
consumers.

### Fix

Delete `wood_styles.py`. If anything breaks, the caller should read from
`ThemeManager` instead. Leaving the file invites future use of a stale copy.

---

## 6. `HabitService` mixes instance and classmethod APIs

The service has two query paths:

- **Instance methods** (`get_habit_by_id`, `get_visible_habits`) read from
  `self._habits`, the in-memory cache.
- **Classmethods** (`get_non_deleted_by_id`, `get_all_non_deleted`) query the
  ORM directly, bypassing the cache.

`habit_detail_page.py:69` calls `HabitService.get_non_deleted_by_id(id)` — a
classmethod that hits the DB while the rest of the UI reads from the instance
cache. If the cache has state that hasn't been flushed, or the DB has state
that hasn't been loaded, the detail page sees data inconsistent with the index.

### Fix

Remove the classmethods. All reads go through the instance, which is the single
source of truth for the GUI. Where a page needs to query something not in the
cache (e.g. archived habits), add an instance method that performs the query and
make the cache/bypass decision explicit in the method name (e.g.
`query_non_deleted_by_id` for a direct DB hit, if truly needed).

The instance is already dependency-injected into `PianoFloatingWindow`. Thread
it into pages via the existing `parent` chain or store it on `MusicSheetWidget`
so pages can access it as `self.service`.

---

## 7. Widget names still say "Wood" in a theme-agnostic system

All common form widgets carry the "Wood" prefix: `WoodDropdown`,
`WoodLineEdit`, `WoodSpinBox`, `WoodCheckBox`, `WoodButton`, `WoodDateEdit`,
`WoodDatePicker`. File names match: `wood_form_widgets.py`, `wood_dropdown.py`,
`wood_date_picker.py`.

These are theme-generic — they read from `ThemeManager` at runtime and work
with any theme. The naming misleads developers into thinking they're
wood-specific.

### Rename map

| Current                          | Renamed                  |
|----------------------------------|--------------------------|
| `WoodDropdown`                   | `ThemedDropdown`         |
| `WoodLineEdit`                   | `ThemedLineEdit`         |
| `WoodSpinBox`                    | `ThemedSpinBox`          |
| `WoodCheckBox`                   | `ThemedCheckBox`         |
| `WoodButton`                     | `ThemedButton`           |
| `WoodDateEdit`                   | `ThemedDateEdit`         |
| `WoodDatePicker`                 | `ThemedDatePicker`       |
| `FormSection`                    | `ThemedFormSection`      |
| `wood_form_widgets.py`           | `themed_form_widgets.py` |
| `wood_dropdown.py`               | `themed_dropdown.py`     |
| `wood_date_picker.py`            | `themed_date_picker.py`  |

These widgets are also currently nested under `sheet_pages/` despite being
general-purpose form components used outside sheet pages (e.g.,
`add_task_widget.py` imports `WoodDatePicker` from `gui/widgets/`). They belong
one level up in `gui/widgets/` alongside other shared widgets.

### Fix

1. Rename files and classes per the table above.
2. Move `themed_form_widgets.py` and `themed_dropdown.py` from
   `gui/widgets/sheet_pages/` to `gui/widgets/`.
3. `themed_date_picker.py` is already in `gui/widgets/` — just rename.
4. Update all imports. The `sheet_pages/__init__.py` re-exports can remain
   as aliases during transition if needed, then be removed.

---

## Suggested execution order

1. **Package structure** (#3) — unblocks clean imports for everything else.
2. **Theme accessor** (#1) + **color parser** (#2) — small, mechanical, no
   behavioral change.
3. **Delete `wood_styles.py`** (#5) — trivial.
4. **Rename widgets** (#7) — mechanical rename + move.
5. **Fix hardcoded colors** (#4) — requires adding theme tokens.
6. **HabitService API** (#6) — requires careful audit of all callers.
