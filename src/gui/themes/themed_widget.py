from abc import ABCMeta, abstractmethod
from PyQt6.QtWidgets import QWidget


class CombinedMeta(type(QWidget), ABCMeta):
    pass


class ThemedWidget(metaclass=CombinedMeta):
    """Interface for widgets that apply theme-specific styles.

    Any widget that sets theme-dependent stylesheets must inherit from this
    class and implement _setup_style(). ThemeManager.apply() calls this method
    on every ThemedWidget instance whenever the active theme changes.

    Python enforces the contract at instantiation time: failing to implement
    _setup_style() raises TypeError immediately.
    """

    @abstractmethod
    def _setup_style(self) -> None:
        """Re-apply all theme-specific stylesheets to this widget."""
        ...
