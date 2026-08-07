"""Structured logging setup using structlog."""

import logging
import sys
import structlog


def configure_logging(env: str = "development", log_level: str = "INFO") -> None:
    """Configure structured logging for Pulse application.

    Args:
        env: Environment mode ('development' or 'production').
        log_level: Minimum log level ('DEBUG', 'INFO', 'WARNING', 'ERROR').
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if env == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,  # type: ignore
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "pulse") -> structlog.BoundLogger:
    """Get a bound structlog logger.

    Args:
        name: Logger component name.

    Returns:
        structlog.BoundLogger: Logger instance.
    """
    return structlog.get_logger(name)
