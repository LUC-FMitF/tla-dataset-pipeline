"""Logging infrastructure for TLA dataset pipeline."""

import logging
import sys
from typing import Optional


# Global logger instances cache
_loggers: dict[str, logging.Logger] = {}


def configure_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """Configure logging for the entire application.

    Sets up structured logging with appropriate handlers for console output.
    Should be called early in application startup (e.g., in CLI entry point).

    Args:
        verbose: If True, set log level to DEBUG; otherwise INFO
        log_file: Optional path to write logs to file in addition to console
    """
    root_logger = logging.getLogger()

    # Set root logger level
    level = logging.DEBUG if verbose else logging.INFO
    root_logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatters
    detailed_formatter = logging.Formatter("[%(levelname)s] %(name)s - %(message)s")

    # Console handler (stderr for warnings/errors, stdout for info/debug)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(console_handler)

    # File handler if requested
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(detailed_formatter)
            root_logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            root_logger.warning(f"Could not configure file logging: {e}")


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance.

    This function provides a simple factory for creating loggers.
    Loggers are cached to avoid recreating them.

    Args:
        name: Name of the logger (typically __name__ from calling module)

    Returns:
        Configured logger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)
    return _loggers[name]


# Convenience: Create a module-level logger for this module
logger = get_logger(__name__)
