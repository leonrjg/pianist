from .theme import Theme

_MENU = """
    QMenu {
        background-color: rgb(255, 245, 250);
        border: 2px solid rgb(210, 90, 130);
        border-radius: 4px;
        padding: 4px;
    }
    QMenu::item {
        background-color: transparent;
        color: rgb(35, 25, 45);
        padding: 6px 20px;
        font-size: 11px;
    }
    QMenu::item:selected {
        background-color: rgba(210, 90, 130, 200);
        color: rgb(255, 245, 250);
        border-radius: 3px;
    }
    QMenu::item:hover {
        background-color: rgba(210, 90, 130, 80);
        border-radius: 3px;
    }
"""

_SCROLLBAR = """
    QScrollBar:vertical {
        background: rgb(25, 18, 42);
        width: 8px;
        margin: 30px 2px 20px 2px;
        border: none;
        border-radius: 2px;
    }
    QScrollBar::handle:vertical {
        background: rgb(210, 90, 130);
        min-height: 20px;
        border-radius: 2px;
        border: 1px solid rgb(180, 70, 110);
    }
    QScrollBar::handle:vertical:hover {
        background: rgb(240, 130, 165);
        border: 1px solid rgb(240, 130, 165);
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        background: transparent;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: rgb(40, 30, 60);
    }
"""

SAKURA_THEME = Theme(
    name='sakura',
    # Page / sheet background — soft cherry-blossom parchment
    paper='rgb(255, 247, 251)',
    paper_alt='rgb(252, 241, 247)',
    paper_dark='rgb(245, 232, 241)',
    # Text — deep ink, like sumi-e brush
    ink_primary='rgb(30, 20, 40)',
    ink_secondary='rgb(90, 70, 100)',
    link='rgb(190, 60, 110)',
    link_hover='rgb(225, 95, 145)',
    # Borders — petal-pink
    border='rgb(225, 185, 205)',
    separator='rgb(230, 195, 215)',
    # Accent — deep sakura crimson
    accent='rgb(210, 90, 130)',
    accent_dark='rgb(175, 60, 100)',
    accent_light='rgb(245, 135, 170)',
    # Piano frame — deep indigo, unmistakably different from vintage brown
    wood_dark='rgb(232, 200, 218)',
    wood_medium='rgb(244, 228, 238)',
    wood_light='rgb(254, 249, 253)',
    # Piano keys — distinctly pink whites, deep indigo blacks
    white_key='rgb(253, 252, 248)',
    black_key='rgb(20, 20, 18)',
    # Status
    status_active='rgb(60, 170, 100)',
    status_inactive='rgb(140, 110, 150)',
    # Typography — Japanese-flavored serif
    header_font='Hiragino Mincho ProN, Georgia, serif',
    # Urgency: (overdue, soon, today, future)
    urgency_colors=(
        'rgb(200, 50, 80)',
        'rgb(210, 90, 130)',
        'rgb(140, 90, 150)',
        'rgb(210, 175, 195)',
    ),
    menu_stylesheet=_MENU,
    scrollbar_stylesheet=_SCROLLBAR,
    # Sheet painting — soft petal paper with cherry blossom SVG overlay
    sheet_frame='rgb(90, 40, 60)',
    sheet_bg='rgb(255, 235, 245)',
    sheet_shadow='rgba(200, 120, 160, 80)',
    sheet_border='rgb(225, 185, 205)',
    sheet_binding='rgba(190, 100, 140, 45)',
    dog_ear_color='rgb(248, 220, 235)',
    background_svg='gui/cherry_blossoms.svg',
    background_svg_opacity=0.055,
    # Cards
    card_bg='rgba(255, 247, 251, 180)',
    card_bg_completed='rgba(255, 247, 251, 100)',
    card_border='rgb(225, 185, 205)',
    card_hover_border='rgb(210, 90, 130)',
    # Inputs — pink-tinted paper fields
    input_bg='rgba(255, 247, 251, 210)',
    input_focus_border='rgb(210, 90, 130)',
    input_selection='rgba(210, 90, 130, 110)',
    # Buttons — sakura primary, pale secondary
    button_primary_bg='rgba(210, 90, 130, 185)',
    button_primary_hover='rgba(235, 115, 155, 210)',
    button_primary_text='rgb(255, 247, 251)',
    button_secondary_bg='rgba(255, 247, 251, 210)',
    button_secondary_hover='rgba(255, 240, 248, 230)',
    button_secondary_text='rgb(30, 20, 40)',
    # Piano key colors
    black_key_text_color='rgb(240, 175, 210)',
    key_label_color='rgb(30, 20, 40)',
)
