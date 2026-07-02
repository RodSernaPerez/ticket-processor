"""Structured logging setup."""

from __future__ import annotations

import logging
import sys
from typing import Any, cast

import structlog
from structlog.typing import FilteringBoundLogger

from ticket_processor.config import Settings
from ticket_processor.domain.ports import LoggerPort


class StructlogLogger(LoggerPort):
    def __init__(self, logger: FilteringBoundLogger) -> None:
        self._logger = logger

    def debug(self, message: str, **kwargs: object) -> None:
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: object) -> None:
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: object) -> None:
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: object) -> None:
        self._logger.error(message, **kwargs)

    def exception(self, message: str, **kwargs: object) -> None:
        self._logger.exception(message, **kwargs)

    def bind(self, **kwargs: object) -> StructlogLogger:
        return StructlogLogger(self._logger.bind(**kwargs))


def setup_logging(settings: Settings) -> None:
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="%(message)s", stream=sys.stdout)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    if settings.log_format.lower() == "json":
        processors.extend(
            [
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ]
        )
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> FilteringBoundLogger:
    logger = cast(FilteringBoundLogger, structlog.get_logger())
    if name:
        return logger.bind(component=name)
    return logger
