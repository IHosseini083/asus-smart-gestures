"""Structured and terminal-adaptive logging for ASUS Smart Gestures."""

import logging
import sys
from typing import ClassVar

# ANSI Escape Sequences
_RESET = "\033[0m"
_BOLD = "\033[1m"
_RED = "\033[31m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_BLUE = "\033[34m"
_CYAN = "\033[36m"
_GRAY = "\033[90m"


class ColoredFormatter(logging.Formatter):
    """TTY-aware formatter that applies ANSI colors to log level and message."""

    LEVEL_COLORS: ClassVar[dict[int, str]] = {
        logging.DEBUG: _GRAY,
        logging.INFO: _CYAN,
        logging.WARNING: _YELLOW,
        logging.ERROR: _RED,
        logging.CRITICAL: f"{_RED}{_BOLD}",
    }

    def format(self, record: logging.LogRecord) -> str:
        color = self.LEVEL_COLORS.get(record.levelno, _RESET)
        level_name = f"{color}{record.levelname:<7}{_RESET}"
        return f"{_GRAY}[{self.formatTime(record, '%H:%M:%S')}]{_RESET} {level_name} {record.getMessage()}"


class JournalFormatter(logging.Formatter):
    """Clean formatter for systemd journald (no timestamps, systemd prepends them)."""

    def format(self, record: logging.LogRecord) -> str:
        if record.levelno >= logging.WARNING:
            return f"[{record.levelname}] {record.getMessage()}"
        return record.getMessage()


def setup_logging(
    level: str = "INFO", *, verbose: bool = False, quiet: bool = False
) -> logging.Logger:
    """Configure the root logger according to environment and verbosity options.

    Args:
        level: Base log level string ("DEBUG", "INFO", "WARNING", "ERROR").
        verbose: If True, override level to DEBUG.
        quiet: If True, override level to WARNING.

    Returns:
        The configured logger instance.
    """
    logger = logging.getLogger("asus_smart_gestures")

    if verbose:
        effective_level = logging.DEBUG
    elif quiet:
        effective_level = logging.WARNING
    else:
        effective_level = getattr(logging, level.upper(), logging.INFO)

    logger.setLevel(effective_level)

    # Remove existing handlers
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(effective_level)

    if sys.stdout.isatty():
        handler.setFormatter(ColoredFormatter())
    else:
        handler.setFormatter(JournalFormatter())

    logger.addHandler(handler)
    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    """Return package logger."""
    return logging.getLogger("asus_smart_gestures")
