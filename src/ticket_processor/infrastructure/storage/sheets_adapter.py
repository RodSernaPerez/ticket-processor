"""Google Sheets adapter."""

from __future__ import annotations

from decimal import Decimal

from ticket_processor.config import Settings
from ticket_processor.domain.models import Purchase
from ticket_processor.domain.ports import SheetsPort
from ticket_processor.infrastructure.email.gog_client import GogClient


class SheetsAdapter(SheetsPort):
    def __init__(self, gog_client: GogClient, settings: Settings) -> None:
        self._gog = gog_client
        self._settings = settings

    def purchase_exists(self, purchase_id: str) -> bool:
        values = self._gog.sheets_get(self._settings.sheet_id, "C:C")
        return any(len(row) > 0 and row[0] == purchase_id for row in values)

    def append_purchase(self, purchase: Purchase) -> None:
        rows: list[list[str]] = []
        for product in purchase.products:
            rows.append(
                [
                    purchase.purchased_at.strftime("%Y-%m-%d"),
                    purchase.merchant,
                    purchase.id,
                    product.name,
                    product.quantity,
                    self._format_decimal(product.unit_price or Decimal("0.00")),
                    self._format_decimal(product.total_price),
                    product.category_l1.value,
                    product.category_l2.value,
                ]
            )
        self._gog.sheets_append(self._settings.sheet_id, self._settings.sheet_range, rows)

    @staticmethod
    def _format_decimal(value: Decimal) -> str:
        return f"{value:.2f}".replace(".", ",")
