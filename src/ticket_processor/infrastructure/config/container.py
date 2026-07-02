"""Dependency container."""

from __future__ import annotations

from ticket_processor.application.services.classification_service import ClassificationService
from ticket_processor.application.services.email_processor_service import EmailProcessorService
from ticket_processor.application.services.ticket_processor_service import TicketProcessorService
from ticket_processor.application.use_cases import (
    ProcessEmailUseCase,
    ProcessWebhookUseCase,
    SyncPurchasesUseCase,
)
from ticket_processor.config import Settings, get_settings, override_settings
from ticket_processor.domain.classifiers import (
    CompositeClassifier,
    KeywordClassifier,
    LlmClassifier,
)
from ticket_processor.infrastructure.email.gmail_adapter import GmailAdapter
from ticket_processor.infrastructure.email.gog_client import GogClient
from ticket_processor.infrastructure.llm.openrouter_client import OpenRouterClient
from ticket_processor.infrastructure.logging.setup import StructlogLogger, get_logger, setup_logging
from ticket_processor.infrastructure.parser.llm_parser import LlmParser
from ticket_processor.infrastructure.parser.pdf_parser import PdfParser
from ticket_processor.infrastructure.parser.text_parser import TextParser
from ticket_processor.infrastructure.storage.sheets_adapter import SheetsAdapter
from ticket_processor.infrastructure.storage.supabase_adapter import SupabaseAdapter


class Container:
    _instance: Container | None = None

    def __new__(cls, _settings: Settings | None = None) -> Container:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, settings: Settings | None = None) -> None:
        if hasattr(self, "_initialized"):
            return

        self.settings = settings or get_settings()
        setup_logging(self.settings)
        self.logger = StructlogLogger(get_logger("ticket_processor"))

        self.gog_client = GogClient(self.settings)
        self.email_port = GmailAdapter(self.gog_client)
        self.pdf_parser = PdfParser()
        self.text_parser = TextParser()
        self.llm_port = OpenRouterClient(self.settings)
        self.receipt_items_extractor = LlmParser(self.llm_port)
        self.keyword_classifier = KeywordClassifier()
        self.llm_classifier = LlmClassifier(self.llm_port)
        self.composite_classifier = CompositeClassifier(
            self.keyword_classifier,
            self.llm_classifier,
        )
        self.classification_service = ClassificationService(self.composite_classifier)
        self.sheets_port = SheetsAdapter(self.gog_client, self.settings)
        self.supabase_port = SupabaseAdapter(self.settings)

        self.ticket_processor = TicketProcessorService(
            settings=self.settings,
            email_port=self.email_port,
            text_extractors=[self.pdf_parser, self.text_parser],
            receipt_items_extractor=self.receipt_items_extractor,
            classification_service=self.classification_service,
            sheets_port=self.sheets_port,
            supabase_port=self.supabase_port,
            logger=self.logger,
        )
        self.email_processor = EmailProcessorService(self.ticket_processor)
        self.process_email_use_case = ProcessEmailUseCase(self.ticket_processor)
        self.process_webhook_use_case = ProcessWebhookUseCase(self.ticket_processor)
        self.sync_purchases_use_case = SyncPurchasesUseCase(self.ticket_processor)
        self._initialized = True


def get_container(settings: Settings | None = None) -> Container:
    return Container(settings)


def reset_container() -> None:
    Container._instance = None
    override_settings(None)
