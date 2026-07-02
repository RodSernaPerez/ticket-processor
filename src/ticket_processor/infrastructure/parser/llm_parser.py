"""LLM-based receipt item extraction."""

from __future__ import annotations

import json
import re
from decimal import Decimal

from ticket_processor.domain.exceptions import ParsingError
from ticket_processor.domain.models import Product
from ticket_processor.domain.ports import LlmPort, ReceiptItemsExtractorPort

SYSTEM_PROMPT = """You extract grocery receipt line items from Spanish receipts.
Return valid JSON only with this shape:
{
  "products": [
    {"name": "LECHE ENTERA", "quantity": "2", "unit": "ud", "total_price": "2.40"}
  ]
}

Rules:
- Extract only purchased items, never totals or discounts.
- quantity must be a string.
- unit must be one of: ud, kg, l, g, ml.
- total_price must be a decimal string with two digits.
- If there are no products, return {"products":[]}.
"""


class LlmParser(ReceiptItemsExtractorPort):
    def __init__(self, llm: LlmPort) -> None:
        self._llm = llm

    def extract_products(self, receipt_text: str, attachment_name: str) -> list[Product]:
        if not receipt_text.strip():
            raise ParsingError("Receipt text is empty", context={"filename": attachment_name})

        response = self._llm.complete(
            f"Receipt text:\n{receipt_text[:12000]}\n\nJSON:",
            SYSTEM_PROMPT,
        )
        match = re.search(r"\{[\s\S]*\}", response)
        if match is None:
            raise ParsingError(
                "LLM response did not contain JSON",
                context={"filename": attachment_name, "response": response[:500]},
            )

        try:
            payload = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise ParsingError(
                "Invalid JSON returned by LLM",
                context={"filename": attachment_name, "response": response[:500]},
            ) from exc

        products: list[Product] = []
        for item in payload.get("products", []):
            if not isinstance(item, dict):
                continue
            try:
                products.append(
                    Product(
                        name=str(item["name"]).strip(),
                        quantity=str(item.get("quantity", "1")),
                        unit=str(item.get("unit", "ud")).lower(),
                        total_price=Decimal(str(item["total_price"])).quantize(Decimal("0.01")),
                    )
                )
            except Exception:
                continue

        if not products:
            raise ParsingError("No valid products extracted", context={"filename": attachment_name})
        return products
