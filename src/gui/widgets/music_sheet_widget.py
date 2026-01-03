"""
Music Sheet Widget - Interactive content widget for the toggleable drawer.

Replaces the decorative music sheet with a multi-page book-style interface
that displays habit management functionality.
"""
import traceback
from enum import Enum
import random

from PyQt6.QtWidgets import QWidget, QStackedWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QPolygonF

from .page_turn_animation import PageTurnAnimation
from .sheet_pages import IndexPage, RepertoirePage, HabitDetailPage, HabitStatsPage, StatsPage, ActivityPage, SettingsPage, MoodPage
from .sheet_menu import SheetMenu
from ..managers import SoundManager


class DogEarOverlay(QWidget):
    """Transparent overlay widget that draws only the dog ear on top of everything"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        """Paint only the dog ear"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate paper rect (same logic as parent)
        sheet_margin = 10
        widget_rect = self.parentWidget().rect()
        paper_rect = widget_rect.adjusted(sheet_margin, sheet_margin, -sheet_margin, -sheet_margin)

        # Dog ear size
        ear_size = 18

        # Define the triangular fold
        fold_corner = QPointF(paper_rect.right() - ear_size, paper_rect.top() + ear_size)
        vertical_point = QPointF(paper_rect.right(), paper_rect.top() + ear_size)
        horizontal_point = QPointF(paper_rect.right() - ear_size, paper_rect.top())

        # Draw the folded part (darker, shows back of paper)
        fold_triangle = QPolygonF([horizontal_point, vertical_point, fold_corner])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(220, 210, 185)))
        painter.drawPolygon(fold_triangle)

        # Draw shadow under the fold
        painter.setPen(QPen(QColor(150, 140, 120, 60), 3))
        painter.drawLine(horizontal_point, fold_corner)
        painter.drawLine(fold_corner, vertical_point)


class PageType(Enum):
    """Enum for page types to avoid magic strings"""
    INDEX = "index"
    REPERTOIRE = "repertoire"
    HABIT_DETAIL = "habit_detail"
    HABIT_STATS = "habit_stats"
    STATS = "stats"
    ACTIVITY = "activity"
    SETTINGS = "settings"
    MOOD = "mood"


class MusicSheetWidget(QWidget):
    """Main container for the interactive sheet pages"""

    # Signals
    habit_updated = pyqtSignal()  # Emitted when habits are modified

    def __init__(self, parent=None, sound_manager: SoundManager=None):
        super().__init__(parent)
        self.sound_manager = sound_manager
        self._page_stack = []  # Navigation history
        self._current_page = None
        self._animator = PageTurnAnimation(self)

        # Generate darker spots/stains - more and larger
        self._paper_stains = []
        for _ in range(40):
            x = random.randint(20, 380)
            y = random.randint(20, 580)
            size = random.randint(4, 12)
            opacity = random.randint(20, 40)
            self._paper_stains.append((x, y, size, opacity))

        # Ensure widget accepts focus and consumes mouse events
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_NoMousePropagation, True)

        self._setup_ui()
        self._navigate_to_index()

    def _setup_ui(self):
        """Setup the widget UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)  # Margin to show dark wooden container
        layout.setSpacing(0)
        self.setLayout(layout)

        # Add menu at the top (fixed, doesn't animate)
        self._menu = SheetMenu(self, current_page_type=PageType.INDEX.value)
        self._menu.navigate_to.connect(self._navigate_to)
        layout.addWidget(self._menu)

        # Stacked widget to hold pages
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._stack)

        # Dog ear overlay - always on top
        self._dog_ear_overlay = DogEarOverlay(self)
        self._dog_ear_overlay.setGeometry(self.rect())
        self._dog_ear_overlay.raise_()

        # Widget itself is transparent, we paint the container manually
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setStyleSheet("""
            MusicSheetWidget {
                background-color: transparent;
                border: none;
            }
        """)

    def paintEvent(self, event):
        """Custom paint to draw vintage paper with book aesthetic"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        from PyQt6.QtCore import QRect

        # Dark wooden container (background holder)
        widget_rect = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(44, 24, 16)))  # Very dark wood
        painter.drawRect(widget_rect)

        # Draw inner shadow for depth on container edges
        shadow_color = QColor(20, 10, 5, 100)
        painter.setPen(QPen(shadow_color, 2))
        painter.drawRect(widget_rect.adjusted(1, 1, -1, -1))

        # Aged paper colors with sepia tones
        paper_center = QColor(252, 248, 235)  # Cream center
        paper_shadow = QColor(160, 140, 110, 100)  # Warm shadow
        paper_border = QColor(200, 185, 160)  # Sepia border
        binding_shadow = QColor(120, 100, 75, 60)  # Left edge shadow

        # Calculate paper sheet dimensions (inset from dark container)
        sheet_margin = 10
        sheet_rect = widget_rect.adjusted(sheet_margin, sheet_margin, -sheet_margin, -sheet_margin)

        # Draw paper shadow (offset right and down for depth)
        shadow_rect = sheet_rect.adjusted(2, 2, 2, 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(paper_shadow))
        painter.drawRect(shadow_rect)

        # Draw main paper sheet
        painter.setPen(QPen(paper_border, 1))
        painter.setBrush(QBrush(paper_center))
        painter.drawRect(sheet_rect)

        # Use sheet_rect for remaining drawing
        paper_rect = sheet_rect

        # Draw aging gradient (darker at edges)
        # Top edge darkening
        top_gradient = QLinearGradient(0, paper_rect.top(), 0, paper_rect.top() + 20)
        top_gradient.setColorAt(0, QColor(220, 210, 185, 40))
        top_gradient.setColorAt(1, QColor(220, 210, 185, 0))
        painter.fillRect(paper_rect.adjusted(0, 0, 0, -paper_rect.height() + 20), top_gradient)

        # Bottom edge darkening
        bottom_gradient = QLinearGradient(0, paper_rect.bottom() - 20, 0, paper_rect.bottom())
        bottom_gradient.setColorAt(0, QColor(220, 210, 185, 0))
        bottom_gradient.setColorAt(1, QColor(220, 210, 185, 40))
        painter.fillRect(paper_rect.adjusted(0, paper_rect.height() - 20, 0, 0), bottom_gradient)

        # Left edge binding shadow
        binding_gradient = QLinearGradient(paper_rect.left(), 0, paper_rect.left() + 12, 0)
        binding_gradient.setColorAt(0, binding_shadow)
        binding_gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.fillRect(paper_rect.adjusted(0, 0, -paper_rect.width() + 12, 0), binding_gradient)

        # Draw music stand holder below container
        self._draw_music_stand_holder(painter, widget_rect)

    def _navigate_to_index(self):
        """Navigate to the index page"""
        self._navigate_to(PageType.INDEX.value, None)

    def _navigate_to(self, page_type: str, data=None):
        """
        Navigate to a specific page type.

        Args:
            page_type: Type of page (PageType enum value)
            data: Optional data for the page (e.g., habit_id for detail page)
        """
        # Cancel any ongoing animation to prevent overlapping pages
        if self._animator.is_running():
            self._animator.cancel()
        
        # Update menu's active page
        self._menu.set_current_page(page_type)

        # Create the new page
        new_page = self._create_page(page_type, data)
        if not new_page:
            print(f"Failed to create page: {page_type}")
            return

        # Connect page signals
        new_page.navigate_to.connect(self._navigate_to)
        new_page.go_back.connect(self._go_back)
        new_page.content_updated.connect(self.habit_updated.emit)

        # Get current page
        old_page = self._current_page

        # Clean up old page if moving forward (to prevent memory leak)
        # Keep in stack widget only if going back
        if old_page and len(self._page_stack) > 3:  # Limit history depth
            # Remove oldest page from stack
            oldest = self._page_stack.pop(0)
            self._disconnect_page_signals(oldest)
            self._stack.removeWidget(oldest)
            oldest.deleteLater()

        # Add to stack widget
        self._stack.addWidget(new_page)

        # Update history before switching
        if old_page:
            self._page_stack.append(old_page)

        self._current_page = new_page

        # Switch to new page immediately (before animation)
        self._stack.setCurrentWidget(new_page)

        # Animate transition (only if there was a previous page)
        if old_page:
            old_page.show()  # Ensure old page is visible for animation
            new_page.show()  # Ensure new page is visible for animation
            self._animator.animate_transition(old_page, new_page, on_complete=None)
            if self.sound_manager:
                self.sound_manager.play_sound('page')
        else:
            new_page.show()

    def _disconnect_page_signals(self, page):
        """Safely disconnect all signals from a page"""
        try:
            page.navigate_to.disconnect(self._navigate_to)
            page.go_back.disconnect(self._go_back)
            page.content_updated.disconnect(self.habit_updated.emit)
        except:
            pass  # Signals already disconnected

    def _go_back(self):
        """Navigate back to previous page"""
        if not self._page_stack:
            return

        # Cancel any ongoing animation to prevent overlapping pages
        if self._animator.is_running():
            self._animator.cancel()

        # Pop from stack
        previous_page = self._page_stack.pop()
        old_page = self._current_page

        # Switch to previous page immediately
        self._stack.setCurrentWidget(previous_page)
        self._current_page = previous_page

        # Animate transition (reverse direction for back navigation)
        if old_page and previous_page:
            old_page.show()  # Ensure old page is visible for animation
            previous_page.show()  # Ensure previous page is visible for animation
            self._animator.animate_transition(
                old_page,
                previous_page,
                on_complete=lambda: self._cleanup_after_back(old_page),
                reverse=True
            )

    def _cleanup_after_back(self, old_page):
        """Clean up after back navigation animation completes"""
        if old_page:
            self._disconnect_page_signals(old_page)
            self._stack.removeWidget(old_page)
            old_page.deleteLater()

    def _create_page(self, page_type: str, data):
        """Factory method to create pages with error handling"""
        try:
            if page_type == PageType.INDEX.value:
                return IndexPage(self)
            elif page_type == PageType.REPERTOIRE.value:
                return RepertoirePage(self)
            elif page_type == PageType.HABIT_DETAIL.value:
                return HabitDetailPage(habit_id=data, parent=self)
            elif page_type == PageType.HABIT_STATS.value:
                return HabitStatsPage(habit_id=data, parent=self)
            elif page_type == PageType.STATS.value:
                return StatsPage(self)
            elif page_type == PageType.ACTIVITY.value:
                return ActivityPage(self)
            elif page_type == PageType.SETTINGS.value:
                return SettingsPage(self)
            elif page_type == PageType.MOOD.value:
                return MoodPage(self)
            else:
                print(f"Unknown page type: {page_type}")
                return None
        except Exception as e:
            traceback.print_exc()
            return None

    def refresh_current_page(self):
        """Refresh the currently displayed page"""
        if self._current_page:
            self._current_page.refresh()

    def navigate_to_habit_detail(self, habit):
        """
        Navigate to the habit detail page for the given habit.

        Args:
            habit: Habit object to view/edit
        """
        self._navigate_to(PageType.HABIT_DETAIL.value, habit.id)

    def navigate_to_mood_page(self):
        """Navigate to the mood management page"""
        self._navigate_to(PageType.MOOD.value, None)

    def resizeEvent(self, event):
        """Update overlay geometry when widget is resized"""
        super().resizeEvent(event)
        if hasattr(self, '_dog_ear_overlay'):
            self._dog_ear_overlay.setGeometry(self.rect())

    def _draw_music_stand_holder(self, painter, widget_rect):
        """Draw a music stand holder/ledge at the bottom of the container"""
        from PyQt6.QtCore import QRect

        # Holder dimensions
        holder_height = 8
        holder_y = widget_rect.bottom() - holder_height

        # Draw the wooden ledge
        holder_rect = QRect(widget_rect.left(), holder_y, widget_rect.width(), holder_height)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(60, 35, 20)))  # Slightly lighter dark wood
        painter.drawRect(holder_rect)

        # Draw highlight on top edge
        painter.setPen(QPen(QColor(80, 50, 30), 3))
        painter.drawLine(holder_rect.left(), holder_y, holder_rect.right(), holder_y)

        # Draw shadow on bottom edge
        painter.setPen(QPen(QColor(30, 15, 8), 1))
        painter.drawLine(holder_rect.left(), holder_rect.bottom(), holder_rect.right(), holder_rect.bottom())
