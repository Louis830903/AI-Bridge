"""
Logger - Logging configuration for AI-Bridge
"""

import logging
import sys
from typing import Optional


# Default format
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> None:
    """
    Setup logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logging
        format_string: Optional custom format string
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    log_format = format_string or LOG_FORMAT
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format, DATE_FORMAT))
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format, DATE_FORMAT))
        root_logger.addHandler(file_handler)
    
    # Set level for aibridge loggers
    logging.getLogger("aibridge").setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    if not name.startswith("aibridge"):
        name = f"aibridge.{name}"
    return logging.getLogger(name)


# Create default logger
logger = get_logger("aibridge")
