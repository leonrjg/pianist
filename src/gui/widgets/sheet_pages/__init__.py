"""
Sheet Pages - Interactive pages for the music sheet widget.

Each page represents different content/functionality in the toggleable drawer.
"""

from .base_page import SheetPage
from .index_page import IndexPage
from .repertoire_page import RepertoirePage
from .habit_detail_page import HabitDetailPage
from .stats_page import StatsPage
from .activity_page import ActivityPage

__all__ = [
    'SheetPage',
    'IndexPage',
    'RepertoirePage',
    'HabitDetailPage',
    'StatsPage',
    'ActivityPage'
]
