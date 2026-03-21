"""
vintage_styles.py — kept for import compatibility.
All styling is now theme-driven via theme_styles.py and ThemeManager.
"""
# VINTAGE_COLORS is retained as a static fallback for any code that reads
# colors directly from this dict (should be migrated to ThemeManager).
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

