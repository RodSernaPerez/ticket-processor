from __future__ import annotations

from dataclasses import dataclass

from ticket_processor.application.dtos import ProcessingResult
from ticket_processor.application.services.ticket_processor_service import TicketProcessorService


@dataclass(frozen=True, slots=True)
class SyncPurchasesUseCase:
    ticket_processor: TicketProcessorService

    def execute(self) -> list[ProcessingResult]:
        return self.ticket_processor.process_unread_emails()
