"""
Centralized logging configuration for the flightcomp application.
Configure once at startup; modules use getLogger(__name__).
"""
import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> None:
    """
    Configure logging for the application. Call once from main() before creating UI.

    Args:
        level: Logging level (default INFO).
        log_file: Optional file path to also write logs to.
        format_string: Optional format; default includes level, name, and message.
    """
    if format_string is None:
        format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(format_string)

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers if called more than once
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        root.addHandler(handler)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name. Use getLogger(__name__) in modules."""
    return logging.getLogger(name)
