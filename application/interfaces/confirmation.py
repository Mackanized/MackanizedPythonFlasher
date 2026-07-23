"""
Confirmation Provider Interfaces for User Verification Prompts.
"""

from abc import ABC, abstractmethod


class IConfirmationProvider(ABC):
    """Abstract interface for pre-flash user confirmations."""

    @abstractmethod
    def confirm(self, prompt: str) -> bool:
        """Prompt user for confirmation. Returns True if approved."""
        pass


class CliConfirmationProvider(IConfirmationProvider):
    """CLI implementation of confirmation provider using stdin."""

    def confirm(self, prompt: str) -> bool:
        try:
            answer = input(prompt).strip().lower()
            return answer in ('y', 'yes')
        except (EOFError, KeyboardInterrupt):
            return False


class AlwaysApproveConfirmationProvider(IConfirmationProvider):
    """Non-interactive provider that automatically approves confirmations."""

    def confirm(self, prompt: str) -> bool:
        return True


class GuiConfirmationProvider(IConfirmationProvider):
    """GUI implementation of confirmation provider.

    Defaults to **deny** (return ``False``) when no callback is wired, so that
    a missing signal connection never silently auto-approves a destructive
    operation.
    """

    def __init__(self, callback=None):
        self._callback = callback

    def confirm(self, prompt: str) -> bool:
        if self._callback:
            return self._callback(prompt)
        return False
