from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str

    # Page / sheet background
    paper: str
    paper_alt: str
    paper_dark: str

    # Text
    ink_primary: str
    ink_secondary: str
    link: str
    link_hover: str

    # Borders
    border: str
    separator: str

    # Accent
    accent: str
    accent_dark: str
    accent_light: str

    # Piano frame tones
    wood_dark: str
    wood_medium: str
    wood_light: str

    # Piano keys
    white_key: str
    black_key: str

    # Status indicators
    status_active: str
    status_inactive: str

    # Typography
    header_font: str

    # Urgency: (overdue, soon, today, future)
    urgency_colors: tuple

    # Full stylesheet snippets (interpolated by consumers)
    menu_stylesheet: str
    scrollbar_stylesheet: str

    # --- Sheet / paper painting (MusicSheetWidget) ---
    # Dark wooden/frame container background
    sheet_frame: str
    # Paper center fill color
    sheet_bg: str
    # Drop shadow behind the paper sheet (rgba)
    sheet_shadow: str
    # Paper border color
    sheet_border: str
    # Left-edge binding shadow (rgba)
    sheet_binding: str
    # Folded dog-ear corner color
    dog_ear_color: str
    # Optional SVG path (relative to src/) drawn over the paper at low opacity; '' = none
    background_svg: str
    # Opacity for the background SVG (0.0 – 1.0)
    background_svg_opacity: float

    # --- Cards (HabitCard) ---
    card_bg: str
    card_bg_completed: str
    card_border: str
    card_hover_border: str

    # --- Form inputs ---
    input_bg: str
    input_focus_border: str
    input_selection: str

    # --- Buttons ---
    button_primary_bg: str
    button_primary_hover: str
    button_primary_text: str
    button_secondary_bg: str
    button_secondary_hover: str
    button_secondary_text: str

    # --- Piano keys (painter-level colors) ---
    # Elapsed-time text on black keys
    black_key_text_color: str
    # Habit name label on white keys
    key_label_color: str
