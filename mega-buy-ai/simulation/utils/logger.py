"""
Logging configuration for the simulation system.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


# Log format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(
    name: str = "simulation",
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True
) -> logging.Logger:
    """
    Setup and configure a logger.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logging
        console: Whether to log to console

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers = []

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "simulation") -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name (usually module name)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# Create default logger
_default_logger: Optional[logging.Logger] = None


def init_logging(level: str = "INFO", log_dir: Optional[str] = None) -> logging.Logger:
    """
    Initialize the default logger for the simulation system.

    Args:
        level: Log level
        log_dir: Directory for log files

    Returns:
        Configured logger
    """
    global _default_logger

    log_file = None
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d")
        log_file = str(log_path / f"simulation_{date_str}.log")

    _default_logger = setup_logger(
        name="simulation",
        level=level,
        log_file=log_file,
        console=True
    )

    return _default_logger
