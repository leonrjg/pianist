from .theme import Theme

_MENU = """
    QMenu {
        background-color: rgb(16, 30, 14);
        border: 2px solid rgb(65, 140, 55);
        border-radius: 4px;
        padding: 4px;
    }
    QMenu::item {
        background-color: transparent;
        color: rgb(200, 225, 190);
        padding: 6px 20px;
        font-size: 11px;
    }
    QMenu::item:selected {
        background-color: rgba(65, 140, 55, 200);
        color: rgb(230, 250, 220);
        border-radius: 3px;
    }
    QMenu::item:hover {
        background-color: rgba(65, 140, 55, 80);
        border-radius: 3px;
    }
"""

_SCROLLBAR = """
    QScrollBar:vertical {
        background: rgb(10, 20, 8);
        width: 8px;
        margin: 30px 2px 20px 2px;
        border: none;
        border-radius: 2px;
    }
    QScrollBar::handle:vertical {
        background: rgb(55, 120, 45);
        min-height: 20px;
        border-radius: 2px;
        border: 1px solid rgb(45, 100, 38);
    }
    QScrollBar::handle:vertical:hover {
        background: rgb(90, 170, 75);
        border: 1px solid rgb(90, 170, 75);
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        background: transparent;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: rgb(14, 28, 12);
    }
"""

MIDORI_THEME = Theme(
    name="midori",
    # Page / sheet background — deep forest dark
    paper="rgb(16, 26, 16)",
    paper_alt="rgb(22, 34, 22)",
    paper_dark="rgb(12, 20, 12)",
    # Text — pale green-white on dark
    ink_primary="rgb(220, 235, 210)",
    ink_secondary="rgb(150, 175, 140)",
    link="rgb(100, 190, 90)",
    link_hover="rgb(150, 220, 120)",
    # Borders — mossy green
    border="rgb(45, 80, 40)",
    separator="rgb(40, 70, 35)",
    # Accent — bright emerald
    accent="rgb(90, 180, 75)",
    accent_dark="rgb(60, 130, 50)",
    accent_light="rgb(130, 210, 100)",
    # Frame / panel tones
    frame_dark="rgb(8, 18, 8)",
    frame_medium="rgb(18, 38, 15)",
    frame_light="rgb(32, 60, 28)",
    # Piano keys
    white_key="rgb(240, 250, 235)",
    black_key="rgb(16, 32, 14)",
    # Status
    status_active="rgb(80, 200, 80)",
    status_inactive="rgb(55, 100, 50)",
    # Typography
    header_font="Luxurious Roman",
    # Urgency: (overdue, soon, today, future)
    urgency_colors=(
        "rgb(210, 60, 70)",
        "rgb(200, 155, 40)",
        "rgb(90, 180, 75)",
        "rgb(60, 120, 50)",
    ),
    menu_stylesheet=_MENU,
    scrollbar_stylesheet=_SCROLLBAR,
    # Sheet painting
    sheet_frame="rgb(8, 18, 8)",
    sheet_bg="rgb(15, 28, 13)",
    sheet_shadow="rgba(0, 40, 0, 120)",
    sheet_border="rgb(45, 80, 40)",
    sheet_binding="rgba(30, 80, 25, 60)",
    dog_ear_color="rgb(30, 55, 28)",
    sheet_bg_image="gui/themes/midori/forest.jpg",
    sheet_bg_image_opacity=0.4,
    background_svg="",
    background_svg_opacity=0.0,
    # Cards
    card_bg="rgba(20, 38, 18, 200)",
    card_bg_completed="rgba(20, 38, 18, 100)",
    card_border="rgb(45, 80, 40)",
    card_hover_border="rgb(90, 180, 75)",
    # Inputs
    input_bg="rgba(20, 38, 18, 220)",
    input_focus_border="rgb(90, 180, 75)",
    input_selection="rgba(90, 180, 75, 120)",
    # Buttons
    button_primary_bg="rgba(65, 140, 55, 185)",
    button_primary_hover="rgba(85, 170, 70, 210)",
    button_primary_text="rgb(220, 240, 210)",
    button_secondary_bg="rgba(20, 40, 18, 200)",
    button_secondary_hover="rgba(30, 55, 25, 220)",
    button_secondary_text="rgb(220, 235, 210)",
    danger_bg="rgba(160, 45, 45, 150)",
    danger_hover="rgba(185, 55, 55, 180)",
    # Piano key colors
    black_key_text_color="rgb(130, 200, 110)",
    key_label_color="rgb(30, 60, 25)",
    # Toolbar icons — light green so they're visible on dark backgrounds
    icon_tint="rgb(140, 195, 120)",
    # Fallboard / control panel — deep forest gradient
    fallboard_gradient=(
        (0.0, "rgb(8, 20, 8)"),
        (0.5, "rgb(20, 48, 18)"),
        (1.0, "rgb(12, 30, 10)"),
    ),
    # Drawer — dark backing so the forest.jpg overlay reads cleanly
    frame_gradient=(
        (0.0, "rgb(5, 15, 5)"),
        (1.0, "rgb(10, 25, 8)"),
    ),
    # Scattered leaves on fallboard + control panel (drawer is covered by MusicSheetWidget)
    frame_svg="gui/themes/midori/bg.png",
    frame_svg_opacity=0.35,
    keys_overlay="",
    keys_overlay_opacity=0.0,
    piano_overlay="",
    piano_overlay_opacity=0.0,
)
