"""
Application Layer - Base Command Interface

Defines the command pattern interface for executable application workflows.
Supports validation, execution, logging, and undo/redo capabilities.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Optional


class ICommand(ABC):
    """Abstract Base Class for Application Commands."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Returns readable name of command."""
        pass

    @abstractmethod
    def validate(self) -> Tuple[bool, str]:
        """Validates command prerequisites before execution. Returns (is_valid, error_msg)."""
        pass

    @abstractmethod
    def execute(self) -> bool:
        """Executes the command logic. Returns True on success."""
        pass

    def can_undo(self) -> bool:
        """Returns True if command supports undo."""
        return False

    def undo(self) -> bool:
        """Reverts command effects if supported."""
        return False
