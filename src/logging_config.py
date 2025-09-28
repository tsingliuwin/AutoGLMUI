"""
Logging configuration for AutoGLMUI
"""
import logging
import sys
from typing import Optional

from .config import settings


def setup_logging(name: Optional[str] = None) -> logging.Logger:
    """Set up logging configuration"""
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, settings.log_level.upper()))

        # Create formatter
        formatter = logging.Formatter(settings.log_format)
        console_handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(console_handler)
        logger.setLevel(getattr(logging, settings.log_level.upper()))

    return logger


# Default logger
logger = setup_logging("autoglmui")