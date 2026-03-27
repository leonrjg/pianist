from .theme import Theme

_MENU = """
    QMenu {
        background-color: rgb(248, 248, 250);
        border: 2px solid rgb(55, 75, 115);
        border-radius: 4px;
        padding: 4px;
    }
    QMenu::item {
        background-color: transparent;
        color: rgb(20, 25, 40);
        padding: 6px 20px;
        font-size: 11px;
    }
    QMenu::item:selected {
        background-color: rgba(55, 75, 115, 200);
        color: rgb(245, 245, 245);
        border-radius: 3px;
    }
    QMenu::item:hover {
        background-color: rgba(55, 75, 115, 80);
        border-radius: 3px;
    }
"""

_SCROLLBAR = """
    QScrollBar:vertical {
        background: rgb(18, 25, 48);
        width: 8px;
        margin: 30px 2px 20px 2px;
        border: none;
        border-radius: 2px;
    }
    QScrollBar::handle:vertical {
        background: rgb(55, 75, 115);
        min-height: 20px;
        border-radius: 2px;
        border: 1px solid rgb(35, 55, 90);
    }
    QScrollBar::handle:vertical:hover {
        background: rgb(90, 130, 175);
        border: 1px solid rgb(90, 130, 175);
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        background: transparent;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: rgb(28, 38, 65);
    }
    QScrollBar:horizontal {
        background: rgb(18, 25, 48);
        height: 8px;
        margin: 2px 2px 2px 2px;
        border: none;
        border-radius: 2px;
    }
    QScrollBar::handle:horizontal {
        background: rgb(55, 75, 115);
        min-width: 20px;
        border-radius: 2px;
        border: 1px solid rgb(35, 55, 90);
    }
    QScrollBar::handle:horizontal:hover {
        background: rgb(90, 130, 175);
        border: 1px solid rgb(90, 130, 175);
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
        background: transparent;
    }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: rgb(28, 38, 65);
    }
"""

SAKURA_THEME = Theme(
    name="sakura",
    # Page / sheet background — whitesmoke
    paper="rgb(245, 245, 245)",
    paper_alt="rgb(240, 240, 242)",
    paper_dark="rgb(228, 228, 232)",
    # Text — deep blue-black ink
    ink_primary="rgb(20, 25, 40)",
    ink_secondary="rgb(50, 65, 95)",
    link="rgb(55, 75, 115)",
    link_hover="rgb(90, 155, 185)",
    # Borders — blue-grey
    border="rgb(185, 200, 220)",
    separator="rgb(195, 208, 225)",
    # Accent — slate blue
    accent="rgb(55, 75, 115)",
    accent_dark="rgb(35, 55, 90)",
    accent_light="rgb(90, 155, 185)",
    # Frame / panel tones
    frame_dark="rgb(25, 35, 62)",
    frame_medium="rgb(40, 52, 82)",
    frame_light="rgb(58, 75, 108)",
    # Piano keys
    white_key="rgb(250, 250, 250)",
    black_key="rgb(48, 48, 44)",
    # Status
    status_active="rgb(60, 170, 100)",
    status_inactive="rgb(90, 110, 148)",
    header_font="Luxurious Roman",
    # Urgency: (overdue, soon, today, future)
    urgency_colors=(
        "rgb(200, 50, 80)",
        "rgb(55, 75, 115)",
        "rgb(70, 100, 140)",
        "rgb(160, 182, 210)",
    ),
    menu_stylesheet=_MENU,
    scrollbar_stylesheet=_SCROLLBAR,
    # Sheet painting
    sheet_frame="rgb(25, 40, 78)",
    sheet_bg="rgb(255, 255, 255)",
    sheet_shadow="rgba(55, 75, 115, 80)",
    sheet_border="rgb(185, 200, 220)",
    sheet_binding="rgba(55, 75, 115, 45)",
    dog_ear_color="rgb(232, 236, 245)",
    sheet_bg_image="gui/themes/sakura/mt_fuji_c.jpg",
    sheet_bg_image_opacity=0.35,
    background_svg="",
    background_svg_opacity=0.0,
    # Cards
    card_bg="rgba(245, 245, 245, 180)",
    card_bg_completed="rgba(245, 245, 245, 100)",
    card_border="rgb(185, 200, 220)",
    card_hover_border="rgb(55, 75, 115)",
    # Inputs
    input_bg="rgba(245, 245, 245, 210)",
    input_focus_border="rgb(55, 75, 115)",
    input_selection="rgba(55, 75, 115, 110)",
    # Buttons
    button_primary_bg="rgba(55, 75, 115, 185)",
    button_primary_hover="rgba(75, 100, 148, 210)",
    button_primary_text="rgb(245, 245, 245)",
    button_secondary_bg="rgba(245, 245, 245, 210)",
    button_secondary_hover="rgba(235, 238, 245, 230)",
    button_secondary_text="rgb(20, 25, 40)",
    danger_bg="rgba(180, 50, 50, 150)",
    danger_hover="rgba(200, 60, 60, 180)",
    # Piano key colors
    black_key_text_color="rgb(155, 185, 215)",
    key_label_color="rgb(20, 25, 40)",
    # Fallboard / control panel — Mt. Fuji gradient + cherry blossom overlay
    fallboard_gradient=(
        (0.0, "rgb(255, 255, 255)"),  # snow-white peak
        (0.22, "rgb(255, 255, 255)"),  # snow ends
        (0.62, "rgb(55, 75, 115)"),  # slate-blue mountain body
        (0.74, "rgb(55, 110, 105)"),  # light teal treeline
        (1.0, "rgb(90, 155, 185)"),  # lake blue at bottom
    ),
    # Frame (toggleable drawer) — same scene, slightly darker/deeper so the
    # fallboard reads as a lighter foreground strip against it
    frame_gradient=(
        (0.0, "rgb(230, 235, 245)"),  # off-white, less bright than snow
        (0.22, "rgb(210, 215, 230)"),  # cool grey transition
        (0.62, "rgb(38, 55, 90)"),  # deeper navy mountain
        (0.74, "rgb(38, 85, 82)"),  # darker teal
        (1.0, "rgb(65, 125, 160)"),  # deeper lake blue
    ),
    frame_svg="gui/themes/sakura/1553444947.png",
    frame_svg_opacity=0.2,
    keys_overlay="",
    keys_overlay_opacity=0.0,
    piano_overlay="",
    piano_overlay_opacity=0.4,
)
