"""Supabase adapter."""

from __future__ import annotations

import json
from typing import Any

import requests

from ticket_processor.config import Settings
from ticket_processor.domain.exceptions import StorageError
from ticket_processor.domain.models import Purchase
from ticket_processor.domain.ports import SupabasePort


class SupabaseAdapter(SupabasePort):
    def __init__(self, settings: Settings) -> None:
        self._base_url = str(settings.supabase_url).rstrip("/")
        self._api_key = settings.supabase_service_key.get_secret_value()
        self._table = settings.supabase_table
        self._session = requests.Session()
        self._session.headers.update(
            {
                "apikey": self._api_key,
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation",
            }
        )

    def purchase_exists(self, purchase_id: str) -> bool:
        response = self._session.get(
            f"{self._base_url}/rest/v1/{self._table}",
            params={"id": f"eq.{purchase_id}", "select": "id", "limit": "1"},
            timeout=30,
        )
        if response.status_code >= 400:
            raise StorageError(
                "Supabase existence check failed",
                context={"status_code": response.status_code, "body": response.text[:500]},
            )
        return bool(response.json())

    def upsert_purchase(self, purchase: Purchase) -> None:
        response = self._session.post(
            f"{self._base_url}/rest/v1/{self._table}",
            params={"on_conflict": "id"},
            json=self._purchase_to_row(purchase),
            timeout=30,
        )
        if response.status_code >= 400:
            raise StorageError(
                "Supabase upsert failed",
                context={"status_code": response.status_code, "body": response.text[:500]},
            )

    @staticmethod
    def _purchase_to_row(purchase: Purchase) -> dict[str, Any]:
        return {
            "id": purchase.id,
            "merchant": purchase.merchant,
            "purchased_at": purchase.purchased_at.isoformat(),
            "source_message_id": purchase.source_message_id,
            "source_attachment_id": purchase.source_attachment_id,
            "source_attachment_name": purchase.source_attachment_name,
            "products": json.dumps(
                [
                    {
                        "name": product.name,
                        "quantity": product.quantity,
                        "unit": product.unit,
                        "total_price": str(product.total_price),
                        "category_l1": product.category_l1.value,
                        "category_l2": product.category_l2.value,
                    }
                    for product in purchase.products
                ]
            ),
            "total_amount": str(purchase.total_amount),
            "raw_text": purchase.raw_text,
        }
