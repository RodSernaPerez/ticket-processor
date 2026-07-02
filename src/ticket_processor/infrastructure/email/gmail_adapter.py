"""Gmail adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parseaddr, parsedate_to_datetime
from typing import Any

from ticket_processor.domain.models import Attachment, EmailMessage
from ticket_processor.domain.ports import EmailPort
from ticket_processor.infrastructure.email.gog_client import GogClient


class GmailAdapter(EmailPort):
    def __init__(self, gog_client: GogClient) -> None:
        self._gog = gog_client

    def search_candidate_emails(self, query: str) -> list[EmailMessage]:
        messages = self._gog.search_messages(query=query)
        return [self.get_email(message["id"]) for message in messages]

    def get_email(self, message_id: str) -> EmailMessage:
        payload = self._gog.get_message(message_id)
        headers = self._headers(payload)
        body_text = self._extract_plain_text(payload.get("payload", {}))
        attachments = tuple(self._extract_attachments(payload.get("payload", {})))
        return EmailMessage(
            message_id=str(payload["id"]),
            thread_id=str(payload["threadId"]),
            subject=headers.get("subject", ""),
            sender=headers.get("from", ""),
            received_at=self._parse_received_at(headers.get("date", "")),
            body_text=body_text,
            rfc_message_id=headers.get("message-id"),
            attachments=attachments,
        )

    def download_attachment(self, message_id: str, attachment: Attachment) -> bytes:
        return self._gog.get_attachment(message_id, attachment.attachment_id)

    def reply_to_email(self, email: EmailMessage, body: str) -> None:
        subject = (
            email.subject
            if email.subject.lower().startswith("re:")
            else f"Re: {email.subject}"
        )
        reply_to = email.rfc_message_id or email.message_id
        recipient = parseaddr(email.sender)[1] or email.sender
        self._gog.send_reply(
            to=recipient,
            subject=subject,
            thread_id=email.thread_id,
            in_reply_to=reply_to,
            body=body,
        )

    def mark_as_processed(self, message_id: str, label_name: str) -> None:
        self._gog.add_label(message_id, label_name)

    def _headers(self, payload: dict[str, Any]) -> dict[str, str]:
        return {
            str(header["name"]).lower(): str(header["value"])
            for header in payload.get("payload", {}).get("headers", [])
        }

    def _extract_attachments(self, part: dict[str, Any]) -> list[Attachment]:
        attachments: list[Attachment] = []
        filename = str(part.get("filename") or "")
        body = part.get("body", {})
        if filename and body.get("attachmentId"):
            attachments.append(
                Attachment(
                    attachment_id=str(body["attachmentId"]),
                    filename=filename,
                    mime_type=str(part.get("mimeType", "")),
                    size=int(body.get("size", 0)),
                )
            )
        for child in part.get("parts", []):
            attachments.extend(self._extract_attachments(child))
        return attachments

    def _extract_plain_text(self, part: dict[str, Any]) -> str:
        import base64

        mime_type = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if mime_type == "text/plain" and data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        for child in part.get("parts", []):
            text = self._extract_plain_text(child)
            if text:
                return text
        return ""

    def _parse_received_at(self, value: str) -> datetime:
        if not value:
            return datetime.now(UTC)
        try:
            return parsedate_to_datetime(value)
        except Exception:
            return datetime.now(UTC)
