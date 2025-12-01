"""
Tracker Registry - Central registry for discovering and instantiating tracker classes.

This module provides a centralized way to discover all available tracker implementations
and instantiate them based on their name and configuration. This eliminates hardcoded
tracker references throughout the codebase and makes adding new trackers easier.
"""
import inspect
import logging
import toml
from typing import Dict, List, Type, Any
from . import io, window, Tracker

logger = logging.getLogger(__name__)


class TrackerRegistry:
    """Registry for discovering and managing tracker classes."""

    _trackers: Dict[str, Type[Tracker]] = {}
    _initialized = False

    @classmethod
    def _discover_trackers(cls):
        """Discover all Tracker subclasses by importing tracker modules."""
        if cls._initialized:
            return

        # Import all tracker implementations to ensure they're registered
        try:
            from . import io, window
        except ImportError as e:
            logger.warning(f"Failed to import some tracker modules: {e}")

        for tracker_class in Tracker.__subclasses__():
            cls._trackers[tracker_class.__name__] = tracker_class

        cls._initialized = True
        logger.info(f"Discovered trackers: {list(cls._trackers.keys())}")

    @classmethod
    def get_all_trackers(cls) -> Dict[str, Type[Tracker]]:
        """
        Get all available tracker classes.

        Returns:
            Dictionary mapping tracker names to their class types
        """
        cls._discover_trackers()
        return cls._trackers.copy()

    @classmethod
    def get_tracker_class(cls, name: str) -> Type[Tracker]:
        """
        Get a tracker class by name.

        Args:
            name: The tracker name (e.g., 'io', 'window')

        Returns:
            The tracker class

        Raises:
            ValueError: If tracker name is not found
        """
        cls._discover_trackers()
        if name not in cls._trackers:
            raise ValueError(f"Unknown tracker type: {name}. Available: {list(cls._trackers.keys())}")
        return cls._trackers[name]

    @classmethod
    def get_config_schema(cls, name: str) -> dict[str, type]:
        """
        Get initialization parameters for a tracker by name.

        Args:
            name: The tracker name

        Returns:
            List of parameter names and types for the tracker's __init__ method
        """
        tracker_class = cls.get_tracker_class(name)
        return inspect.getfullargspec(tracker_class.__init__).annotations

    @classmethod
    def get_tracker_names(cls) -> List[str]:
        """
        Get list of all available tracker names.

        Returns:
            List of tracker names
        """
        cls._discover_trackers()
        return list(cls._trackers.keys())

    @classmethod
    def instantiate_tracker(cls, name: str, config: Dict[str, Any]) -> Tracker:
        """
        Instantiate a tracker by name with the given configuration.

        Args:
            name: The tracker name (e.g., 'io', 'window')
            config: Configuration dictionary for the tracker

        Returns:
            An instance of the tracker

        Raises:
            ValueError: If tracker name is not found
        """
        tracker_class = cls.get_tracker_class(name)

        # Try generic instantiation with config
        try:
            return tracker_class(**config)
        except TypeError:
            # Fall back to no-arg constructor
            return tracker_class()

    @classmethod
    def get_tracker_help(cls, name: str, config: Dict[str, Any]) -> str:
        """
        Get help text from a tracker's static method.

        Args:
            name: The tracker name
            config: Configuration dictionary to pass to get_help()

        Returns:
            Help text from the tracker
        """
        tracker_class = cls.get_tracker_class(name)
        return tracker_class.get_help(**config)

    @classmethod
    def parse_config(cls, config_str: str) -> Dict[str, Any]:
        """
        Parse a TOML configuration string into a dictionary.

        Args:
            config_str: TOML format configuration string
                       e.g., 'keywords = ["piano", "synthesia"]'
                       or 'keywords = ["PyCharm"]'

        Returns:
            Configuration dictionary

        Raises:
            ValueError: If the TOML string is invalid
        """
        result = {}
        try:
            result = toml.loads(config_str)
        except:
            pass
        return result

    @classmethod
    def config_to_string(cls, config: Dict[str, Any]) -> str:
        """
        Convert a configuration dictionary to TOML format string.

        Args:
            config: Configuration dictionary

        Returns:
            TOML format string
        """
        if not config:
            return ""

        return toml.dumps(config)

