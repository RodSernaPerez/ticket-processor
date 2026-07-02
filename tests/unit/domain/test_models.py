from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from ticket_processor.domain.models import (
    Attachment,
    EmailMessage,
    Product,
    ProductCategoryLevel1,
    ProductCategoryLevel2,
    Purchase,
)


def test_product_computes_unit_price() -> None:
    product = Product(
        name="Leche Entera 1L",
        quantity="2",
        unit="ud",
        total_price=Decimal("2.40"),
        category_l1=ProductCategoryLevel1.ALIMENTACION,
        category_l2=ProductCategoryLevel2.LACTEOS,
    )
    assert product.unit_price == Decimal("1.20")


def test_product_rejects_negative_price() -> None:
    with pytest.raises(ValueError):
        Product(name="Invalid", total_price=Decimal("-1.00"))


def test_email_message_detects_receipt_candidate(sample_attachment: Attachment) -> None:
    email = EmailMessage(
        message_id="msg-1",
        thread_id="thread-1",
        subject="Tu ticket de Mercadona",
        sender="noreply@mercadona.es",
        received_at=datetime.now(UTC),
        body_text="Gracias por tu compra",
        rfc_message_id="<receipt@example.com>",
        attachments=(sample_attachment,),
    )
    assert email.is_receipt_candidate is True


def test_purchase_builds_deterministic_id(sample_product: Product) -> None:
    purchase_one = Purchase.create(
        merchant="Mercadona",
        purchased_at=datetime(2026, 7, 2, 10, 30, tzinfo=UTC),
        products=[sample_product],
        source_message_id="msg-1",
        source_attachment_id="att-1",
        source_attachment_name="ticket.pdf",
        raw_text="receipt",
    )
    purchase_two = Purchase.create(
        merchant="Mercadona",
        purchased_at=datetime(2026, 7, 2, 11, 30, tzinfo=UTC),
        products=[sample_product],
        source_message_id="msg-1",
        source_attachment_id="att-1",
        source_attachment_name="ticket.pdf",
        raw_text="receipt",
    )
    assert purchase_one.id == purchase_two.id
    assert purchase_one.total_amount == Decimal("2.40")
