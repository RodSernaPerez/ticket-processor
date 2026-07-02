"""Main ticket processing orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from ticket_processor.application.dtos import ProcessingResult
from ticket_processor.application.services.classification_service import ClassificationService
from ticket_processor.config import Settings
from ticket_processor.domain.exceptions import ParsingError
from ticket_processor.domain.models import Attachment, EmailMessage, Product, Purchase
from ticket_processor.domain.ports import (
    AttachmentTextExtractorPort,
    EmailPort,
    LoggerPort,
    ReceiptItemsExtractorPort,
    SheetsPort,
    SupabasePort,
)


class TicketProcessorService:
    def __init__(
        self,
        settings: Settings,
        email_port: EmailPort,
        text_extractors: list[AttachmentTextExtractorPort],
        receipt_items_extractor: ReceiptItemsExtractorPort,
        classification_service: ClassificationService,
        sheets_port: SheetsPort,
        supabase_port: SupabasePort,
        logger: LoggerPort,
    ) -> None:
        self._settings = settings
        self._email_port = email_port
        self._text_extractors = text_extractors
        self._receipt_items_extractor = receipt_items_extractor
        self._classification_service = classification_service
        self._sheets_port = sheets_port
        self._supabase_port = supabase_port
        self._logger = logger.bind(service="ticket_processor")

    def process_unread_emails(self) -> list[ProcessingResult]:
        emails = self._email_port.search_candidate_emails(self._settings.gmail_search_query)
        return [self.process_email(email.message_id) for email in emails]

    def process_email(self, message_id: str) -> ProcessingResult:
        email = self._email_port.get_email(message_id)
        logger = self._logger.bind(message_id=message_id)

        if not email.is_receipt_candidate:
            logger.info("email_skipped_not_receipt")
            return ProcessingResult(
                message_id=message_id,
                success=False,
                skipped=True,
                reason="not_receipt",
            )

        processed_purchase_ids: list[str] = []
        supported_attachments = email.supported_attachments
        if not supported_attachments:
            logger.info("email_skipped_no_supported_attachments")
            return ProcessingResult(
                message_id=message_id,
                success=False,
                skipped=True,
                reason="no_supported_attachments",
            )

        for attachment in supported_attachments:
            purchase = self._build_purchase(email, attachment)
            purchase_logger = logger.bind(
                attachment_id=attachment.attachment_id,
                attachment_name=attachment.filename,
                purchase_id=purchase.id,
            )

            sheets_exists = self._sheets_port.purchase_exists(purchase.id)
            supabase_exists = self._supabase_port.purchase_exists(purchase.id)

            if sheets_exists and supabase_exists:
                purchase_logger.info("purchase_already_processed")
                processed_purchase_ids.append(purchase.id)
                continue

            if not sheets_exists:
                self._sheets_port.append_purchase(purchase)
                purchase_logger.info("purchase_saved_to_sheets")
            if not supabase_exists:
                self._supabase_port.upsert_purchase(purchase)
                purchase_logger.info("purchase_saved_to_supabase")

            processed_purchase_ids.append(purchase.id)

        self._email_port.reply_to_email(email, self._success_reply_body(processed_purchase_ids))
        self._email_port.mark_as_processed(message_id, self._settings.gmail_processed_label)
        logger.info("email_processed", purchases=len(processed_purchase_ids))
        return ProcessingResult(
            message_id=message_id,
            success=True,
            processed_purchases=tuple(processed_purchase_ids),
        )

    def process_webhook_payload(self, payload: dict[str, object]) -> ProcessingResult:
        message_id = str(payload["message_id"])
        attachment_id = str(payload["attachment_id"])
        attachment_name = str(payload["attachment_name"])
        raw_text = str(payload["raw_text"])
        merchant = str(payload.get("merchant") or "Unknown")
        purchased_at = datetime.fromisoformat(str(payload["purchased_at"]))
        raw_products = payload["products"]
        if not isinstance(raw_products, list):
            raise ParsingError("Webhook payload products must be a list")

        products: list[Product] = []
        for item in raw_products:
            if not isinstance(item, dict):
                raise ParsingError("Webhook product entries must be objects")
            product = Product(
                name=str(item["name"]),
                quantity=str(item.get("quantity", "1")),
                unit=str(item.get("unit", "ud")),
                total_price=self._decimal_from(item.get("total_price", "0")),
            )
            products.append(self._classification_service.classify_product(product))

        purchase = Purchase.create(
            merchant=merchant,
            purchased_at=purchased_at,
            products=products,
            source_message_id=message_id,
            source_attachment_id=attachment_id,
            source_attachment_name=attachment_name,
            raw_text=raw_text,
        )
        if not self._sheets_port.purchase_exists(purchase.id):
            self._sheets_port.append_purchase(purchase)
        if not self._supabase_port.purchase_exists(purchase.id):
            self._supabase_port.upsert_purchase(purchase)
        return ProcessingResult(
            message_id=message_id,
            success=True,
            processed_purchases=(purchase.id,),
        )

    def _build_purchase(self, email: EmailMessage, attachment: Attachment) -> Purchase:
        content = self._email_port.download_attachment(email.message_id, attachment)
        extractor = self._select_text_extractor(attachment)
        raw_text = extractor.extract_text(content, attachment)
        products = self._receipt_items_extractor.extract_products(raw_text, attachment.filename)
        classified_products = [
            self._classification_service.classify_product(product) for product in products
        ]
        merchant = self._detect_merchant(email, raw_text, attachment)
        purchased_at = self._detect_purchase_date(email)
        return Purchase.create(
            merchant=merchant,
            purchased_at=purchased_at,
            products=classified_products,
            source_message_id=email.message_id,
            source_attachment_id=attachment.attachment_id,
            source_attachment_name=attachment.filename,
            raw_text=raw_text,
        )

    def _select_text_extractor(self, attachment: Attachment) -> AttachmentTextExtractorPort:
        for extractor in self._text_extractors:
            if extractor.supports(attachment):
                return extractor
        raise ParsingError("No extractor available", context={"filename": attachment.filename})

    def _detect_merchant(self, email: EmailMessage, raw_text: str, attachment: Attachment) -> str:
        haystack = " ".join(
            [
                email.sender.lower(),
                email.subject.lower(),
                attachment.filename.lower(),
                raw_text.lower(),
            ]
        )
        for merchant in ("mercadona", "carrefour", "lidl", "aldi", "dia", "eroski"):
            if merchant in haystack:
                return merchant.capitalize()
        sender_domain = email.sender.split("@")[-1] if "@" in email.sender else email.sender
        return sender_domain.split(".")[0].capitalize() or "Unknown"

    def _detect_purchase_date(self, email: EmailMessage) -> datetime:
        return email.received_at.astimezone(UTC)

    def _success_reply_body(self, purchase_ids: list[str]) -> str:
        joined = ", ".join(purchase_ids)
        return (
            "Receipt processed successfully.\n\n"
            f"Processed purchase ids: {joined}\n"
            "The items were extracted, categorized, and stored in Supabase and Google Sheets."
        )

    @staticmethod
    def _decimal_from(value: object) -> Decimal:
        from decimal import Decimal

        return Decimal(str(value))
