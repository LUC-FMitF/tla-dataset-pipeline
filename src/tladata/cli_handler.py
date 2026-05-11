"""Base class for CLI command handlers."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from .logging import get_logger

if TYPE_CHECKING:
    import argparse


class CLIHandler(ABC):
    """Abstract base class for CLI command handlers.
    
    All CLI command handlers should inherit from this class and implement
    the handle() method. This ensures consistent error handling and exit
    code semantics across the application.
    
    Exit Code Semantics:
        0: Command executed successfully
        1: Command failed (exception, validation error, etc.)
        2+: Reserved for future use
    """

    def __init__(self) -> None:
        """Initialize the CLI handler."""
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def handle(self, args: "argparse.Namespace") -> int:
        """Execute the handler with parsed command-line arguments.
        
        Args:
            args: Parsed command-line arguments from argparse.Namespace
        
        Returns:
            Exit code: 0 for success, 1 for failure
            
        Raises:
            Should NOT raise exceptions; instead catch internally and return
            appropriate exit code.
        """
        pass
