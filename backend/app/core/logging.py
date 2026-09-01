"""CIRUS — Structured logging configuration.

Falls back gracefully to stdlib logging if structlog is not installed.
"""
from __future__ import annotations

import logging
import sys
from typing import Any


_USE_STRUCTLOG = False
try:
    import structlog  # type: ignore
    _USE_STRUCTLOG = True
except ImportError:
    pass


def configure_logging(level: str = "INFO") -> None:
    """Configure logging for the application. Call once at startup."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        level=numeric_level,
        stream=sys.stdout,
    )

    if _USE_STRUCTLOG:
        import structlog

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


def get_logger(name: str) -> Any:
    """Return a logger — structlog if available, else stdlib."""
    if _USE_STRUCTLOG:
        import structlog
        return structlog.get_logger(name)
    return logging.getLogger(name)
