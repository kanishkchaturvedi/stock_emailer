"""Logging configuration for Smart Money Tracker."""

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only add handlers if they haven't been added yet
    if not logger.handlers:
        # Create console handler with formatting
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Set default level
    if logger.level == logging.NOTSET:
        logger.setLevel(logging.INFO)

    return logger
