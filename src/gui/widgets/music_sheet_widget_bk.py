"""
Music Sheet Widget - Interactive content widget for the toggleable drawer.

Replaces the decorative music sheet with a multi-page book-style interface
that displays habit management functionality.
"""

from enum import Enum
import random

from PyQt6.QtWidgets import QWidget, QStackedWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient

from .page_turn_animation import PageTurnAnimation
from .sheet_pages import IndexPage, HabitDetailPage, StatsPage, ActivityPage


class PageType(Enum):
    """Enum for page types to avoid magic strings"""
    INDEX = "index"
    HABIT_DETAIL = "habit_detail"
    STATS = "stats"
    ACTIVITY = "activity"


class MusicSheetWidget(QWidget):
    """Main container for the interactive sheet pages"""

    # Signals
    habit_updated = pyqtSignal()  # Emitted when habits are modified

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page_stack = []  # Navigation history
        self._current_page = None
        self._animator = PageTurnAnimation(self)

        # Cache for paper texture noise (consistent pattern)
        random.seed(42)
        self._texture_points = [(random.randint(5, 195), random.randint(5, 295)) for _ in range(200)]

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

        # Stacked widget to hold pages
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self._stack)

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

        # Draw subtle paper texture (cached noise pattern)
        painter.setPen(QPen(QColor(200, 190, 170, 8)))
        for x_offset, y_offset in self._texture_points:
            x = paper_rect.left() + x_offset
            y = paper_rect.top() + y_offset
            if paper_rect.contains(x, y):
                painter.drawPoint(x, y)

        # Draw binding stitches (left edge)
        painter.setPen(QPen(QColor(160, 130, 100), 1))
        stitch_x = paper_rect.left() + 4
        for y in range(paper_rect.top() + 30, paper_rect.bottom() - 30, 25):
            painter.drawLine(stitch_x - 1, y - 2, stitch_x + 1, y + 2)
            painter.drawLine(stitch_x - 1, y + 2, stitch_x + 1, y - 2)

    def _navigate_to_index(self):
        """Navigate to the index page (habit list)"""
        self._navigate_to(PageType.INDEX.value, None)

    def _navigate_to(self, page_type: str, data=None):
        """
        Navigate to a specific page type.

        Args:
            page_type: Type of page (PageType enum value)
            data: Optional data for the page (e.g., habit_id for detail page)
        """
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

        # Pop from stack
        previous_page = self._page_stack.pop()
        old_page = self._current_page

        # Switch to previous page immediately
        self._stack.setCurrentWidget(previous_page)
        self._current_page = previous_page

        # Animate transition
        if old_page and previous_page:
            old_page.show()  # Ensure old page is visible for animation
            previous_page.show()  # Ensure previous page is visible for animation
            self._animator.animate_transition(
                old_page,
                previous_page,
                on_complete=lambda: self._cleanup_after_back(old_page)
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
            elif page_type == PageType.HABIT_DETAIL.value:
                return HabitDetailPage(habit_id=data, parent=self)
            elif page_type == PageType.STATS.value:
                return StatsPage(self)
            elif page_type == PageType.ACTIVITY.value:
                return ActivityPage(self)
            else:
                print(f"Unknown page type: {page_type}")
                return None
        except Exception as e:
            print(f"Error creating page {page_type}: {e}")
            return None

    def refresh_current_page(self):
        """Refresh the currently displayed page"""
        if self._current_page:
            self._current_page.refresh()
