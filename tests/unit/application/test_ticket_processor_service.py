from __future__ import annotations

from decimal import Decimal
from unittest.mock import Mock

from ticket_processor.application.services.classification_service import ClassificationService
from ticket_processor.application.services.ticket_processor_service import TicketProcessorService
from ticket_processor.config import Settings
from ticket_processor.domain.classifiers import KeywordClassifier
from ticket_processor.domain.models import Product


def build_service(
    settings: Settings,
    sample_email,
) -> tuple[TicketProcessorService, Mock, Mock, Mock]:
    email_port = Mock()
    extractor = Mock()
    items_extractor = Mock()
    sheets_port = Mock()
    supabase_port = Mock()
    logger = Mock()
    email_port.get_email.return_value = sample_email
    email_port.download_attachment.return_value = b"%PDF-1.4"
    extractor.supports.return_value = True
    extractor.extract_text.return_value = "LECHE ENTERA 2 2.40"
    items_extractor.extract_products.return_value = [
        Product(name="Leche Entera 1L", quantity="2", unit="ud", total_price=Decimal("2.40"))
    ]
    sheets_port.purchase_exists.return_value = False
    supabase_port.purchase_exists.return_value = False
    logger.bind.return_value = logger
    service = TicketProcessorService(
        settings=settings,
        email_port=email_port,
        text_extractors=[extractor],
        receipt_items_extractor=items_extractor,
        classification_service=ClassificationService(KeywordClassifier()),
        sheets_port=sheets_port,
        supabase_port=supabase_port,
        logger=logger,
    )
    return service, email_port, sheets_port, supabase_port


def test_process_email_happy_path(settings: Settings, sample_email) -> None:
    service, email_port, sheets_port, supabase_port = build_service(settings, sample_email)

    result = service.process_email(sample_email.message_id)

    assert result.success is True
    assert len(result.processed_purchases) == 1
    sheets_port.append_purchase.assert_called_once()
    supabase_port.upsert_purchase.assert_called_once()
    email_port.reply_to_email.assert_called_once()
    email_port.mark_as_processed.assert_called_once_with(
        sample_email.message_id,
        settings.gmail_processed_label,
    )


def test_process_email_is_idempotent_when_both_sinks_have_purchase(
    settings: Settings,
    sample_email,
) -> None:
    service, email_port, sheets_port, supabase_port = build_service(settings, sample_email)
    sheets_port.purchase_exists.return_value = True
    supabase_port.purchase_exists.return_value = True

    result = service.process_email(sample_email.message_id)

    assert result.success is True
    sheets_port.append_purchase.assert_not_called()
    supabase_port.upsert_purchase.assert_not_called()
    email_port.reply_to_email.assert_called_once()
