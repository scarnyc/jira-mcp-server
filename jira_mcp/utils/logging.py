"""Logging utilities for JIRA MCP Server."""

import logging
import sys
from functools import lru_cache
from typing import Optional


@lru_cache
def get_logger(name: str = "jira_mcp", level: Optional[str] = None) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        # Set level
        log_level = getattr(logging, level or "INFO")
        logger.setLevel(log_level)

        # Console handler with structured format
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(log_level)

        # Format: timestamp - level - name - message
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Prevent propagation to root logger
        logger.propagate = False

    return logger


def configure_logging(level: str = "INFO") -> None:
    """Configure global logging settings.

    Args:
        level: Log level to set
    """
    # Clear the cache to allow reconfiguration
    get_logger.cache_clear()

    # Configure root jira_mcp logger
    get_logger("jira_mcp", level)

    # Reduce noise from httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
