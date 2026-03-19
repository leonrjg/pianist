"""
Task module for unified task representation.
"""

from .task import Task, TaskType
from .service import get_upcoming_tasks

__all__ = ['Task', 'TaskType', 'get_upcoming_tasks']
