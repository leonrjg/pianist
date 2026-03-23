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

    # Frame / panel tones
    frame_dark: str
    frame_medium: str
    frame_light: str

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
    # Optional image path (relative to src/) used as the paper fill; '' = solid sheet_bg color
    sheet_bg_image: str
    # Opacity for the sheet background image (0.0 – 1.0)
    sheet_bg_image_opacity: float
    # Optional SVG path (relative to src/) drawn over the paper at low opacity; '' = none
    background_svg: str
    # Opacity for the background SVG (0.0 – 1.0)
    background_svg_opacity: float

    # --- Fallboard / control panel painting ---
    # Gradient stops as ((pos, color_str), ...) e.g. ((0.0, 'rgb(...)'), (0.6, 'rgb(...)'), (1.0, 'rgb(...)'))
    # Empty tuple = use legacy frame_medium → frame_dark two-stop gradient
    fallboard_gradient: tuple
    # Same format; used for the toggleable drawer (left frame panel)
    # Empty tuple = use fallboard_gradient if set, otherwise legacy draw_frame_texture
    frame_gradient: tuple
    # Optional SVG overlay on fallboard and control panel; '' = none
    frame_svg: str
    # Opacity for the frame SVG (0.0 – 1.0)
    frame_svg_opacity: float
    # Optional image overlay drawn over all keys as a region; '' = none
    keys_overlay: str
    # Opacity for the keys overlay (0.0 – 1.0)
    keys_overlay_opacity: float
    # Optional image overlay spanning fallboard + keys + control panel as one continuous image; '' = none
    piano_overlay: str
    # Opacity for the unified piano overlay (0.0 – 1.0)
    piano_overlay_opacity: float

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
    # Danger / destructive action button
    danger_bg: str
    danger_hover: str

    # --- Piano keys (painter-level colors) ---
    # Elapsed-time text on black keys
    black_key_text_color: str
    # Habit name label on white keys
    key_label_color: str

    # --- Toolbar icons ---
    # Tint color applied to SVG icons; '' = use native icon color (black)
    icon_tint: str = ""
