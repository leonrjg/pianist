from .theme import Theme

_MENU = """
    QMenu {
        background-color: rgb(255, 252, 245);
        border: 2px solid rgb(184, 134, 11);
        border-radius: 3px;
        padding: 4px;
    }
    QMenu::item {
        background-color: transparent;
        color: rgb(70, 50, 35);
        padding: 6px 20px;
        font-size: 11px;
    }
    QMenu::item:selected {
        background-color: rgba(184, 134, 11, 180);
        color: rgb(255, 252, 245);
        border-radius: 2px;
    }
    QMenu::item:hover {
        background-color: rgba(184, 134, 11, 120);
        border-radius: 2px;
    }
"""

_SCROLLBAR = """
    QScrollBar:vertical {
        background: rgb(61, 40, 23);
        width: 8px;
        margin: 30px 2px 20px 2px;
        border: none;
        border-radius: 2px;
    }
    QScrollBar::handle:vertical {
        background: rgb(184, 134, 11);
        min-height: 20px;
        border-radius: 2px;
        border: 1px solid rgb(184, 134, 11);
    }
    QScrollBar::handle:vertical:hover {
        background: rgb(218, 165, 32);
        border: 1px solid rgb(218, 165, 32);
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        background: transparent;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: rgb(92, 61, 46);
    }
"""

VINTAGE_THEME = Theme(
    name='wood',
    paper='rgb(255, 252, 245)',
    paper_alt='rgb(252, 248, 235)',
    paper_dark='rgb(245, 240, 225)',
    ink_primary='rgb(70, 50, 35)',
    ink_secondary='rgb(110, 90, 70)',
    link='rgb(120, 80, 50)',
    link_hover='rgb(160, 110, 70)',
    border='rgb(200, 185, 160)',
    separator='rgb(200, 185, 160)',
    accent='rgb(184, 134, 11)',
    accent_dark='rgb(160, 115, 10)',
    accent_light='rgb(218, 165, 32)',
    frame_dark='rgb(61, 40, 23)',
    frame_medium='rgb(92, 61, 46)',
    frame_light='rgb(122, 80, 64)',
    white_key='rgb(253, 252, 248)',
    black_key='rgb(48, 48, 44)',
    status_active='rgb(60, 140, 60)',
    status_inactive='rgb(140, 120, 95)',
    header_font='Luxurious Roman',
    urgency_colors=(
        'rgb(160, 50, 50)',
        'rgb(184, 134, 11)',
        'rgb(140, 110, 80)',
        'rgb(200, 185, 160)',
    ),
    menu_stylesheet=_MENU,
    scrollbar_stylesheet=_SCROLLBAR,
    # Sheet painting
    sheet_frame='rgb(44, 24, 16)',
    sheet_bg='rgb(252, 248, 235)',
    sheet_shadow='rgba(160, 140, 110, 100)',
    sheet_border='rgb(200, 185, 160)',
    sheet_binding='rgba(120, 100, 75, 60)',
    dog_ear_color='rgb(220, 210, 185)',
    sheet_bg_image='',
    sheet_bg_image_opacity=1.0,
    background_svg='',
    background_svg_opacity=0.0,
    # Cards
    card_bg='rgba(255, 252, 245, 180)',
    card_bg_completed='rgba(255, 252, 245, 100)',
    card_border='rgb(200, 185, 160)',
    card_hover_border='rgb(184, 134, 11)',
    # Inputs
    input_bg='rgba(255, 252, 245, 200)',
    input_focus_border='rgb(184, 134, 11)',
    input_selection='rgba(184, 134, 11, 120)',
    # Buttons
    button_primary_bg='rgba(184, 134, 11, 180)',
    button_primary_hover='rgba(200, 150, 30, 200)',
    button_primary_text='rgb(255, 252, 245)',
    button_secondary_bg='rgba(255, 252, 245, 200)',
    button_secondary_hover='rgba(255, 255, 250, 220)',
    button_secondary_text='rgb(70, 50, 35)',
    danger_bg='rgba(180, 50, 50, 150)',
    danger_hover='rgba(200, 60, 60, 180)',
    # Piano key colors
    black_key_text_color='rgb(180, 180, 180)',
    key_label_color='rgb(74, 74, 74)',
    # Fallboard / control panel
    fallboard_gradient=(),
    frame_gradient=(),
    frame_svg='',
    frame_svg_opacity=0.0,
    keys_overlay='',
    keys_overlay_opacity=0.0,
    piano_overlay='',
    piano_overlay_opacity=0.0,
)
