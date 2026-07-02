"""Domain models."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256


class ProductCategoryLevel1(StrEnum):
    ALIMENTACION = "Alimentación"
    LIMPIEZA = "Limpieza"
    ELECTRONICA = "Electrónica"
    ROPA = "Ropa"
    HOGAR = "Hogar"
    OTROS = "Otros"


class ProductCategoryLevel2(StrEnum):
    LACTEOS = "Lácteos"
    CARNICERIA = "Carne"
    PESCADO = "Pescado"
    VERDURAS = "Verduras"
    FRUTAS = "Frutas"
    PANADERIA = "Panadería"
    LEGUMBRES = "Legumbres"
    CONDIMENTOS = "Condimentos"
    BEBIDAS = "Bebidas"
    CONGELADOS = "Congelados"
    CEREALES = "Cereales"
    DETERGENTE = "Detergente"
    LAVAVAJILLAS = "Lavavajillas"
    LIMPIEZA_HOGAR = "Limpieza Hogar"
    MOVILES = "Móviles"
    ORDENADORES = "Ordenadores"
    ACCESORIOS = "Accesorios"
    CAMISETA = "Camiseta"
    PANTALON = "Pantalón"
    CALZADO = "Calzado"
    DECORACION = "Decoración"
    MUEBLES = "Muebles"
    UTENSILIOS = "Utensilios"
    OTROS = "Otros"


@dataclass(frozen=True, slots=True)
class Attachment:
    attachment_id: str
    filename: str
    mime_type: str
    size: int = 0

    @property
    def extension(self) -> str:
        if "." not in self.filename:
            return ""
        return self.filename.rsplit(".", 1)[1].lower()

    @property
    def is_supported_receipt_type(self) -> bool:
        return self.extension in {"pdf", "txt", "csv"} or self.mime_type in {
            "application/pdf",
            "text/plain",
            "text/csv",
        }


@dataclass(frozen=True, slots=True)
class Product:
    name: str
    quantity: str = "1"
    unit: str = "ud"
    total_price: Decimal = field(default=Decimal("0.00"))
    category_l1: ProductCategoryLevel1 = ProductCategoryLevel1.OTROS
    category_l2: ProductCategoryLevel2 = ProductCategoryLevel2.OTROS

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Product name cannot be empty")
        if self.total_price < 0:
            raise ValueError("Total price cannot be negative")

    @property
    def normalized_quantity(self) -> Decimal:
        return Decimal(self.quantity.replace(",", "."))

    @property
    def unit_price(self) -> Decimal | None:
        quantity = self.normalized_quantity
        if quantity <= 0:
            return None
        return (self.total_price / quantity).quantize(Decimal("0.01"))


@dataclass(frozen=True, slots=True)
class EmailMessage:
    message_id: str
    thread_id: str
    subject: str
    sender: str
    received_at: datetime
    body_text: str
    rfc_message_id: str | None = None
    attachments: tuple[Attachment, ...] = field(default_factory=tuple)

    @property
    def supported_attachments(self) -> tuple[Attachment, ...]:
        return tuple(
            attachment
            for attachment in self.attachments
            if attachment.is_supported_receipt_type
        )

    @property
    def is_receipt_candidate(self) -> bool:
        haystack = " ".join(
            [
                self.subject.lower(),
                self.sender.lower(),
                self.body_text.lower(),
                " ".join(attachment.filename.lower() for attachment in self.attachments),
            ]
        )
        keywords = (
            "ticket",
            "receipt",
            "factura",
            "compra",
            "mercadona",
            "carrefour",
            "lidl",
            "aldi",
            "dia",
            "supermercado",
            "pedido",
        )
        return bool(self.supported_attachments) and any(keyword in haystack for keyword in keywords)


@dataclass(frozen=True, slots=True)
class Purchase:
    id: str
    merchant: str
    purchased_at: datetime
    products: tuple[Product, ...]
    source_message_id: str
    source_attachment_id: str
    source_attachment_name: str
    raw_text: str

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Purchase id cannot be empty")
        if not self.products:
            raise ValueError("Purchase must include at least one product")
        if not self.merchant.strip():
            raise ValueError("Merchant cannot be empty")

    @property
    def total_amount(self) -> Decimal:
        return sum((product.total_price for product in self.products), Decimal("0.00"))

    @property
    def product_count(self) -> int:
        return len(self.products)

    @classmethod
    def build_id(cls, message_id: str, attachment_id: str) -> str:
        digest = sha256(f"{message_id}:{attachment_id}".encode()).hexdigest()
        return digest[:20]

    @classmethod
    def create(
        cls,
        merchant: str,
        purchased_at: datetime,
        products: Iterable[Product],
        source_message_id: str,
        source_attachment_id: str,
        source_attachment_name: str,
        raw_text: str,
    ) -> Purchase:
        normalized_date = purchased_at.astimezone(UTC)
        product_tuple = tuple(products)
        return cls(
            id=cls.build_id(source_message_id, source_attachment_id),
            merchant=merchant,
            purchased_at=normalized_date,
            products=product_tuple,
            source_message_id=source_message_id,
            source_attachment_id=source_attachment_id,
            source_attachment_name=source_attachment_name,
            raw_text=raw_text,
        )


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    message_id: str
    success: bool
    processed_purchases: tuple[str, ...] = field(default_factory=tuple)
    skipped: bool = False
    reason: str | None = None
