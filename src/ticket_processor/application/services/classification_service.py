"""Application-level classification helpers."""

from __future__ import annotations

from ticket_processor.domain.models import Product
from ticket_processor.domain.ports import ClassifierPort


class ClassificationService:
    def __init__(self, classifier: ClassifierPort) -> None:
        self._classifier = classifier

    def classify_product(self, product: Product) -> Product:
        category_l1, category_l2 = self._classifier.classify(product.name)
        return Product(
            name=product.name,
            quantity=product.quantity,
            unit=product.unit,
            total_price=product.total_price,
            category_l1=category_l1,
            category_l2=category_l2,
        )
