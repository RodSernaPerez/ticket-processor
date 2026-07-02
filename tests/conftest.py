from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from ticket_processor.config import LlmProvider, Settings, override_settings
from ticket_processor.domain.models import (
    Attachment,
    EmailMessage,
    Product,
    ProductCategoryLevel1,
    ProductCategoryLevel2,
)


@pytest.fixture(autouse=True)
def cleanup_settings_cache() -> None:
    override_settings(None)
    yield
    override_settings(None)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        gmail_refresh_token="refresh-token",
        gmail_client_id="client-id",
        gmail_client_secret="client-secret",
        gmail_account="processor@example.com",
        supabase_url="https://example.supabase.co",
        supabase_service_key="supabase-key",
        sheet_id="sheet-id",
        llm_provider=LlmProvider.OPENROUTER,
        llm_model="openai/gpt-oss-120b:free",
        openrouter_api_key="openrouter-key",
        groq_api_key="groq-key",
    )


@pytest.fixture
def sample_attachment() -> Attachment:
    return Attachment(
        attachment_id="att-1",
        filename="ticket-mercadona.pdf",
        mime_type="application/pdf",
        size=1024,
    )


@pytest.fixture
def sample_email(sample_attachment: Attachment) -> EmailMessage:
    return EmailMessage(
        message_id="msg-1",
        thread_id="thread-1",
        subject="Tu ticket de Mercadona",
        sender="Mercadona <noreply@mercadona.es>",
        received_at=datetime(2026, 7, 2, 10, 30, tzinfo=UTC),
        body_text="Adjuntamos tu ticket de compra.",
        rfc_message_id="<gmail-rfc-message-id@example.com>",
        attachments=(sample_attachment,),
    )


@pytest.fixture
def sample_product() -> Product:
    return Product(
        name="Leche Entera 1L",
        quantity="2",
        unit="ud",
        total_price=Decimal("2.40"),
        category_l1=ProductCategoryLevel1.ALIMENTACION,
        category_l2=ProductCategoryLevel2.LACTEOS,
    )
