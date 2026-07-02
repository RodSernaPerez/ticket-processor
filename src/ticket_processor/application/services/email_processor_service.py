"""Email-centric service wrappers."""

from __future__ import annotations

from ticket_processor.application.dtos import ProcessingResult
from ticket_processor.application.services.ticket_processor_service import TicketProcessorService


class EmailProcessorService:
    def __init__(self, ticket_processor: TicketProcessorService) -> None:
        self._ticket_processor = ticket_processor

    def process_email(self, message_id: str) -> ProcessingResult:
        return self._ticket_processor.process_email(message_id)

    def process_unread_emails(self) -> list[ProcessingResult]:
        return self._ticket_processor.process_unread_emails()
