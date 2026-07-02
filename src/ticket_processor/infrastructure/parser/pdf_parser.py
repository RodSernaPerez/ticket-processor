"""PDF receipt text extractor."""

from __future__ import annotations

import io

import pypdf

from ticket_processor.domain.exceptions import ParsingError
from ticket_processor.domain.models import Attachment
from ticket_processor.domain.ports import AttachmentTextExtractorPort


class PdfParser(AttachmentTextExtractorPort):
    def supports(self, attachment: Attachment) -> bool:
        return attachment.extension == "pdf" or attachment.mime_type == "application/pdf"

    def extract_text(self, content: bytes, attachment: Attachment) -> str:
        if not content:
            raise ParsingError("Empty PDF attachment", context={"filename": attachment.filename})
        try:
            reader = pypdf.PdfReader(io.BytesIO(content))
        except Exception as exc:
            raise ParsingError(
                "Could not read PDF attachment", context={"filename": attachment.filename}
            ) from exc

        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if not text:
            raise ParsingError(
                "No text extracted from PDF",
                context={"filename": attachment.filename},
            )
        return text
