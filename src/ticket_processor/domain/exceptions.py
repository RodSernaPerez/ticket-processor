"""Domain exception hierarchy."""

from __future__ import annotations

from typing import Any


class TicketProcessorError(Exception):
    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class ConfigurationError(TicketProcessorError):
    pass


class AuthenticationError(TicketProcessorError):
    pass


class ParsingError(TicketProcessorError):
    pass


class ClassificationError(TicketProcessorError):
    pass


class StorageError(TicketProcessorError):
    pass


class ExternalServiceError(TicketProcessorError):
    pass


class LlmError(ExternalServiceError):
    pass


class EmailError(ExternalServiceError):
    pass


class IdempotencyError(TicketProcessorError):
    pass
