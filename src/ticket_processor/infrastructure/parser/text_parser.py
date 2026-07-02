"""Plain text receipt extractor."""

from __future__ import annotations

from ticket_processor.domain.exceptions import ParsingError
from ticket_processor.domain.models import Attachment
from ticket_processor.domain.ports import AttachmentTextExtractorPort


class TextParser(AttachmentTextExtractorPort):
    def supports(self, attachment: Attachment) -> bool:
        return attachment.extension in {"txt", "csv"} or attachment.mime_type in {
            "text/plain",
            "text/csv",
        }

    def extract_text(self, content: bytes, attachment: Attachment) -> str:
        if not content:
            raise ParsingError("Empty text attachment", context={"filename": attachment.filename})
        text = content.decode("utf-8", errors="replace").strip()
        if not text:
            raise ParsingError(
                "Decoded text attachment is empty",
                context={"filename": attachment.filename},
            )
        return text
