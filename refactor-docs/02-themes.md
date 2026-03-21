# Feature 02: Themes

## Goal

Decouple all styling from layout/logic code so the app can switch between named
visual themes at runtime. Implement two themes:

- **Vintage** — the existing sepia/brass aesthetic (no visible change for existing users).
- **Sakura** — a modern, clean theme with Japanese visual affinity (soft pinks, muted
  greys, cherry blossom accents).

---

## Current State

Styling is scattered across multiple files as hardcoded RGB strings:

| File | What's hardcoded |
|------|-----------------|
| `base_page.py` | All page-level stylesheets, `PAPER_COLOR`, `INK_PRIMARY`, etc. |
| `vintage_styles.py` | `VINTAGE_COLORS` dict, `VINTAGE_MENU_STYLE` |
| `constants.py` | `PianoColors.*` |
| `calendar_page.py` | Popup background, task frame colors, scrollbar colors |
| `index_page.py` | Day header color, urgency colors |
| `sync_page.py` | Device row colors (active green, offline brown) |
| `habit_card.py`, etc. | Per-widget inline stylesheets |

---

## New Structure: `src/gui/themes/`

```
src/gui/themes/
    __init__.py          # exports ThemeManager
    theme.py             # Theme dataclass
    vintage.py           # VINTAGE_THEME instance
    sakura.py            # SAKURA_THEME instance
    manager.py           # ThemeManager singleton
```

---

## `Theme` Dataclass

```python
@dataclass(frozen=True)
class Theme:
    name: str

    # Sheet / page background
    paper: str           # e.g. "rgb(255, 252, 245)"
    paper_alt: str
    paper_dark: str

    # Text
    ink_primary: str
    ink_secondary: str
    link: str
    link_hover: str

    # Borders / separators
    border: str
    separator: str

    # Accent
    accent: str
    accent_dark: str
    accent_light: str

    # Piano frame (wood tones)
    wood_dark: str
    wood_medium: str
    wood_light: str

    # Piano keys
    white_key: str
    black_key: str

    # Status indicators
    status_active: str   # e.g. online/green
    status_inactive: str

    # Section header font family
    header_font: str

    # Urgency colors (list of 4: overdue, soon, today, future)
    urgency_colors: tuple[str, str, str, str]

    # Full stylesheet snippet for QMenu (used in dropdowns / calendar popup)
    menu_stylesheet: str

    # Full stylesheet snippet for QScrollBar:vertical
    scrollbar_stylesheet: str
```

All fields are strings so stylesheets can interpolate them directly with no QColor
conversions needed in stylesheet-generating code.

---

## Vintage Theme

Identical values to the current hardcoded colors — no visual regression.

```python
VINTAGE_THEME = Theme(
    name="vintage",
    paper="rgb(255, 252, 245)",
    paper_alt="rgb(252, 248, 235)",
    paper_dark="rgb(245, 240, 225)",
    ink_primary="rgb(70, 50, 35)",
    ink_secondary="rgb(110, 90, 70)",
    link="rgb(120, 80, 50)",
    link_hover="rgb(160, 110, 70)",
    border="rgb(200, 185, 160)",
    separator="rgb(200, 185, 160)",
    accent="rgb(184, 134, 11)",
    accent_dark="rgb(160, 115, 10)",
    accent_light="rgb(218, 165, 32)",
    wood_dark="rgb(61, 40, 23)",
    wood_medium="rgb(92, 61, 46)",
    wood_light="rgb(122, 80, 64)",
    white_key="rgb(253, 252, 248)",
    black_key="rgb(20, 20, 18)",
    status_active="rgb(60, 140, 60)",
    status_inactive="rgb(140, 120, 95)",
    header_font="Luxurious Roman",
    urgency_colors=("rgb(160, 50, 50)", "rgb(184, 134, 11)", "rgb(140, 110, 80)", "rgb(200, 185, 160)"),
    menu_stylesheet="...",   # matches current VINTAGE_MENU_STYLE
    scrollbar_stylesheet="...",
)
```

---

## Sakura Theme

Modern, minimal Japanese aesthetic. Cherry blossom pinks on near-white backgrounds,
with slate-grey text and soft red-pink accents.

```python
SAKURA_THEME = Theme(
    name="sakura",
    paper="rgb(252, 248, 252)",          # near-white with pink tint
    paper_alt="rgb(248, 242, 248)",
    paper_dark="rgb(240, 232, 240)",
    ink_primary="rgb(45, 40, 55)",       # deep slate
    ink_secondary="rgb(100, 90, 110)",
    link="rgb(180, 80, 110)",            # sakura rose
    link_hover="rgb(210, 110, 140)",
    border="rgb(210, 190, 210)",         # muted lavender-pink
    separator="rgb(220, 200, 215)",
    accent="rgb(220, 100, 130)",         # cherry blossom
    accent_dark="rgb(180, 70, 100)",
    accent_light="rgb(245, 150, 175)",
    wood_dark="rgb(40, 35, 50)",         # dark slate (replaces dark wood)
    wood_medium="rgb(70, 60, 80)",
    wood_light="rgb(100, 90, 110)",
    white_key="rgb(252, 248, 252)",
    black_key="rgb(30, 25, 35)",
    status_active="rgb(80, 160, 100)",
    status_inactive="rgb(150, 130, 155)",
    header_font="Hiragino Mincho ProN",  # Japanese-style serif; fallback: serif
    urgency_colors=("rgb(190, 60, 80)", "rgb(220, 100, 130)", "rgb(150, 110, 150)", "rgb(210, 190, 210)"),
    menu_stylesheet="...",
    scrollbar_stylesheet="...",
)
```

The piano keys and frame tones shift from warm wood to cool slate, giving the
instrument a lacquered-black Japanese upright feel.

---

## `ThemeManager`

```python
class ThemeManager:
    _instance: 'ThemeManager | None' = None

    @classmethod
    def get_instance(cls) -> 'ThemeManager':
        ...

    @property
    def current(self) -> Theme:
        """Return the active Theme. Falls back to VINTAGE_THEME."""
        from core.settings.service import SettingsService
        name = SettingsService.get('theme.active', 'vintage')
        return _REGISTRY.get(name, VINTAGE_THEME)

    def apply(self, app: QApplication) -> None:
        """Re-trigger stylesheet propagation after a theme change."""
        ...
```

`_REGISTRY = {'vintage': VINTAGE_THEME, 'sakura': SAKURA_THEME}`

---

## Migration of Hardcoded Colors

### `base_page.py`

Replace all hardcoded strings in `_setup_style()` and helper methods with
`ThemeManager.get_instance().current.<field>`. The stylesheet string is built
dynamically each time `_setup_style()` is called (it is already called once at init).

```python
def _setup_style(self):
    t = ThemeManager.get_instance().current
    self.setStyleSheet(f"""
        QWidget {{ background-color: transparent; color: {t.ink_primary}; }}
        QLabel {{ ... color: {t.ink_primary}; }}
        ...
    """)
```

### `vintage_styles.py`

Rename to `theme_styles.py`. Export a `get_menu_stylesheet()` function that reads
from `ThemeManager` instead of returning the vintage-hardcoded string. Existing
imports update accordingly.

### `constants.py` — `PianoColors`

`PianoColors` is used by painters (`brass_painter.py`, `frame_painter.py`,
`key_painter.py`). These painters call `QColor(PianoColors.WOOD_DARK)` etc.

After this refactor, painters call `ThemeManager.get_instance().current` and use the
`wood_dark`, `accent`, etc. string fields (converting with `QColor(theme.wood_dark)`).
`PianoColors` is removed.

### Other widgets

Each widget that embeds hardcoded RGB strings in its stylesheet replaces them with
`ThemeManager.get_instance().current.<field>`. Widgets that rebuild their stylesheet
at init time do so once; widgets that need live theme-switch must call a `refresh()`
hook.

---

## Theme Switching at Runtime

1. User picks theme in Settings page.
2. `SettingsService.set('theme.active', name)` is called.
3. Settings page (or a dedicated signal) triggers `ThemeManager.apply(QApplication.instance())`.
4. Each `SheetPage.refresh()` rebuilds its stylesheet.
5. Piano painters trigger a repaint via `update()` on the piano window.

Because all open pages share the same `ThemeManager` instance, the update is global.

---

## No Schema Migration Needed

Theme selection is stored in `AppSetting` (Feature 01). No additional migration.

---

## Implementation Steps

1. Create `src/gui/themes/` package with `theme.py`, `vintage.py`, `sakura.py`, `manager.py`.
2. Migrate `base_page.py` stylesheet strings to use `ThemeManager`.
3. Migrate `vintage_styles.py` → `theme_styles.py` with dynamic helpers.
4. Migrate `constants.py` `PianoColors` → theme-driven; update all three painters.
5. Migrate remaining widgets with inline hardcoded colors (calendar_page, index_page, sync_page, habit_card, etc.).
6. Wire up theme change signal from `SettingsPage`.
7. Add theme selector dropdown to the rebuilt Settings page (Feature 01).
