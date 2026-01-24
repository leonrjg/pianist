"""
Text Search Engine - Find and highlight text in widget trees.

Provides text search functionality across Qt widget hierarchies with
highlighting support.
"""

from typing import List, Optional
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QScrollArea


class TextMatch:
    """Represents a single text match in a widget."""
    
    def __init__(self, widget: QWidget):
        """
        Initialize a text match.
        
        Args:
            widget: The widget containing the matched text
        """
        self.widget = widget


class TextSearchEngine:
    """Engine for searching and highlighting text in widget trees."""
    
    def __init__(self):
        """Initialize the search engine."""
        self._current_matches: List[TextMatch] = []
    
    def search(self, root_widget: QWidget, query: str, case_sensitive: bool = False) -> List[TextMatch]:
        """
        Search for text in all widgets under root_widget.
        
        Args:
            root_widget: The root widget to search from
            query: The text to search for
            case_sensitive: Whether search should be case-sensitive
            
        Returns:
            List of TextMatch objects for all matches found
        """
        if not query:
            return []
        
        matches = []
        search_query = query if case_sensitive else query.lower()
        
        # Get all descendant widgets (including root)
        all_widgets = [root_widget] + root_widget.findChildren(QWidget)
        
        # Search through all widgets
        for widget in all_widgets:
            if self._is_text_widget(widget):
                text = self._get_widget_text(widget)
                if text:
                    search_text = text if case_sensitive else text.lower()
                    if search_query in search_text:
                        # Store match
                        match = TextMatch(widget)
                        matches.append(match)
        
        return matches
    
    def _is_text_widget(self, widget: QWidget) -> bool:
        """Check if widget is a text-containing widget we want to search."""
        # Check for common text widgets
        return isinstance(widget, (QLabel, QPushButton))
    
    def _get_widget_text(self, widget: QWidget) -> Optional[str]:
        """
        Extract text from a widget.
        
        Args:
            widget: Widget to extract text from
            
        Returns:
            Text content or None if widget has no text
        """
        if isinstance(widget, (QLabel, QPushButton)):
            return widget.text()
        return None
    
    def highlight_all_matches(self, matches: List[TextMatch]):
        """
        Apply highlight to all matches using widget property + inline style.
        
        Uses property for state tracking and inline style to override any existing styles.
        
        Args:
            matches: List of TextMatch objects to highlight
        """
        for match in matches:
            try:
                if match.widget and not match.widget.isHidden():
                    # Store original stylesheet on the widget itself
                    if not match.widget.property("_search_original_style"):
                        match.widget.setProperty("_search_original_style", match.widget.styleSheet())
                    
                    # Apply inline highlight (overrides any existing inline styles)
                    original_style = match.widget.property("_search_original_style")
                    highlight_style = f"{original_style}; background-color: rgba(255, 255, 0, 0.6);" if original_style else "background-color: rgba(255, 255, 0, 0.6);"
                    match.widget.setStyleSheet(highlight_style)
            except RuntimeError:
                # Widget has been deleted, skip it
                pass
    
    def clear_highlights(self, matches: List[TextMatch]):
        """
        Remove highlights from all matches using widget property.
        
        Args:
            matches: List of TextMatch objects to clear
        """
        for match in matches:
            try:
                if match.widget:
                    # Restore original inline stylesheet
                    original_style = match.widget.property("_search_original_style")
                    # Check for both None and empty string (Qt sometimes returns empty string for unset properties)
                    if original_style:
                        match.widget.setStyleSheet(original_style)
                    else:
                        # Widget had no style - explicitly clear the stylesheet
                        match.widget.setStyleSheet("")
                    
                    # Force style refresh and repaint
                    match.widget.style().unpolish(match.widget)
                    match.widget.style().polish(match.widget)
                    match.widget.update()
                    
                    # Clear the stored property
                    match.widget.setProperty("_search_original_style", None)
            except RuntimeError:
                # Widget has been deleted, skip it
                pass
    
    def scroll_to_match(self, match: TextMatch):
        """
        Scroll to make a match visible in its scroll area.
        
        Args:
            match: The TextMatch to scroll to
        """
        if not match.widget:
            return
        
        # Find parent scroll area
        scroll_area = self._find_scroll_area(match.widget)
        if scroll_area:
            scroll_area.ensureWidgetVisible(match.widget)
    
    def _find_scroll_area(self, widget: QWidget) -> Optional[QScrollArea]:
        """
        Find the parent QScrollArea of a widget.
        
        Args:
            widget: Widget to find scroll area for
            
        Returns:
            Parent QScrollArea or None if not found
        """
        parent = widget.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                return parent
            parent = parent.parent()
        return None
