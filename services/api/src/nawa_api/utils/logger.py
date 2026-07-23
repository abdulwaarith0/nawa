"""Structured logging: one config, JSON in production, pretty console in dev."""

import logging
import sys

import structlog

from nawa_api.runtime.settings import get_settings

_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    renderer = (
        structlog.processors.JSONRenderer()
        if settings.environment == "production"
        else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            renderer,
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=logging.INFO)
    _configured = True


def get_logger(**bind: object) -> structlog.stdlib.BoundLogger:
    _configure()
    return structlog.get_logger().bind(**bind)
