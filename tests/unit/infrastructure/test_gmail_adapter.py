from __future__ import annotations

from base64 import urlsafe_b64encode
from unittest.mock import Mock

from ticket_processor.infrastructure.email.gmail_adapter import GmailAdapter


def test_get_email_extracts_rfc_message_id_and_plain_text() -> None:
    gog_client = Mock()
    gog_client.get_message.return_value = {
        "id": "gmail-id-1",
        "threadId": "thread-1",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Tu ticket"},
                {"name": "From", "value": "Shop <noreply@example.com>"},
                {"name": "Date", "value": "Thu, 02 Jul 2026 10:30:00 +0000"},
                {"name": "Message-Id", "value": "<rfc-123@example.com>"},
            ],
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {
                        "data": urlsafe_b64encode(b"Gracias por tu compra").decode("utf-8")
                    },
                },
                {
                    "filename": "ticket.pdf",
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "att-1", "size": 1234},
                },
            ],
        },
    }

    adapter = GmailAdapter(gog_client)

    email = adapter.get_email("gmail-id-1")

    assert email.rfc_message_id == "<rfc-123@example.com>"
    assert email.body_text == "Gracias por tu compra"
    assert email.attachments[0].attachment_id == "att-1"


def test_reply_to_email_uses_clean_recipient_and_rfc_message_id(sample_email) -> None:
    gog_client = Mock()
    adapter = GmailAdapter(gog_client)

    adapter.reply_to_email(sample_email, "Procesado correctamente")

    gog_client.send_reply.assert_called_once_with(
        to="noreply@mercadona.es",
        subject="Re: Tu ticket de Mercadona",
        thread_id="thread-1",
        in_reply_to="<gmail-rfc-message-id@example.com>",
        body="Procesado correctamente",
    )
