"""
Vintage Styles - Shared stylesheet definitions for vintage-themed widgets.
"""

# Common vintage color palette
VINTAGE_COLORS = {
    'paper': 'rgb(255, 252, 245)',
    'paper_alt': 'rgb(252, 248, 235)',
    'paper_dark': 'rgb(245, 240, 225)',
    'border': 'rgb(200, 185, 160)',
    'brass': 'rgb(184, 134, 11)',
    'brass_dark': 'rgb(160, 115, 10)',
    'brass_light': 'rgb(200, 150, 30)',
    'text': 'rgb(70, 50, 35)',
    'text_secondary': 'rgb(100, 80, 65)',
    'text_link': 'rgb(120, 80, 50)',
    'text_link_hover': 'rgb(160, 110, 70)',
}

# Vintage menu styling (used by dropdowns and calendar popups)
VINTAGE_MENU_STYLE = """
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
