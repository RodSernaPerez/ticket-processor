"""Product classifiers."""

from __future__ import annotations

import unicodedata
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ticket_processor.domain.models import ProductCategoryLevel1, ProductCategoryLevel2

if TYPE_CHECKING:
    from ticket_processor.domain.classifiers.llm_classifier import LlmClassifier


class BaseClassifier(ABC):
    @abstractmethod
    def classify(self, product_name: str) -> tuple[ProductCategoryLevel1, ProductCategoryLevel2]:
        raise NotImplementedError

    def _normalize(self, name: str) -> str:
        normalized = unicodedata.normalize("NFKD", name.upper().strip())
        return "".join(char for char in normalized if not unicodedata.combining(char))


class KeywordClassifier(BaseClassifier):
    RULES: dict[str, tuple[ProductCategoryLevel1, ProductCategoryLevel2]] = {
        "YOGUR": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.LACTEOS),
        "QUESO": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.LACTEOS),
        "LECHE": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.LACTEOS),
        "PAN": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.PANADERIA),
        "BAGUETTE": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.PANADERIA),
        "GALLETA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.PANADERIA),
        "PIMIENTO": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.VERDURAS),
        "CEBOLLA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.VERDURAS),
        "TOMATE": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.VERDURAS),
        "LECHUGA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.VERDURAS),
        "PATATA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.VERDURAS),
        "MANZANA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.FRUTAS),
        "PERA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.FRUTAS),
        "PLATANO": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.FRUTAS),
        "NARANJA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.FRUTAS),
        "MANDARINA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.FRUTAS),
        "POLLO": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CARNICERIA),
        "TERNERA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CARNICERIA),
        "JAMON": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CARNICERIA),
        "SALMON": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.PESCADO),
        "ATUN": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.PESCADO),
        "MERLUZA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.PESCADO),
        "LENTEJA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.LEGUMBRES),
        "GARBANZO": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.LEGUMBRES),
        "ALUBIA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.LEGUMBRES),
        "ACEITE": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CONDIMENTOS),
        "SAL ": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CONDIMENTOS),
        "AZUCAR": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CONDIMENTOS),
        "HUEVO": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CONDIMENTOS),
        "AGUA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.BEBIDAS),
        "REFRESCO": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.BEBIDAS),
        "ZUMO": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.BEBIDAS),
        "CERVEZA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.BEBIDAS),
        "HELADO": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CONGELADOS),
        "CONGELAD": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CONGELADOS),
        "ARROZ": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CEREALES),
        "PASTA": (ProductCategoryLevel1.ALIMENTACION, ProductCategoryLevel2.CEREALES),
        "DETERGENTE": (ProductCategoryLevel1.LIMPIEZA, ProductCategoryLevel2.DETERGENTE),
        "LAVAVAJILLAS": (ProductCategoryLevel1.LIMPIEZA, ProductCategoryLevel2.LAVAVAJILLAS),
        "LEJIA": (ProductCategoryLevel1.LIMPIEZA, ProductCategoryLevel2.LIMPIEZA_HOGAR),
        "AMONIACO": (ProductCategoryLevel1.LIMPIEZA, ProductCategoryLevel2.LIMPIEZA_HOGAR),
        "JABON": (ProductCategoryLevel1.LIMPIEZA, ProductCategoryLevel2.LIMPIEZA_HOGAR),
        "IPHONE": (ProductCategoryLevel1.ELECTRONICA, ProductCategoryLevel2.MOVILES),
        "MOVIL": (ProductCategoryLevel1.ELECTRONICA, ProductCategoryLevel2.MOVILES),
        "PORTATIL": (ProductCategoryLevel1.ELECTRONICA, ProductCategoryLevel2.ORDENADORES),
        "FUNDA": (ProductCategoryLevel1.ELECTRONICA, ProductCategoryLevel2.ACCESORIOS),
        "CAMISETA": (ProductCategoryLevel1.ROPA, ProductCategoryLevel2.CAMISETA),
        "VAQUERO": (ProductCategoryLevel1.ROPA, ProductCategoryLevel2.PANTALON),
        "ZAPATILLA": (ProductCategoryLevel1.ROPA, ProductCategoryLevel2.CALZADO),
        "SOFA": (ProductCategoryLevel1.HOGAR, ProductCategoryLevel2.MUEBLES),
        "SARTEN": (ProductCategoryLevel1.HOGAR, ProductCategoryLevel2.UTENSILIOS),
        "JARRON": (ProductCategoryLevel1.HOGAR, ProductCategoryLevel2.DECORACION),
    }

    def classify(self, product_name: str) -> tuple[ProductCategoryLevel1, ProductCategoryLevel2]:
        normalized = self._normalize(product_name)
        for keyword, categories in self.RULES.items():
            if keyword in normalized:
                return categories
        return ProductCategoryLevel1.OTROS, ProductCategoryLevel2.OTROS


class CompositeClassifier(BaseClassifier):
    def __init__(self, keyword: KeywordClassifier, llm: LlmClassifier | None = None) -> None:
        self._keyword = keyword
        self._llm = llm

    def classify(self, product_name: str) -> tuple[ProductCategoryLevel1, ProductCategoryLevel2]:
        category_l1, category_l2 = self._keyword.classify(product_name)
        if (
            category_l1 == ProductCategoryLevel1.OTROS
            and category_l2 == ProductCategoryLevel2.OTROS
            and self._llm is not None
        ):
            try:
                return self._llm.classify(product_name)
            except Exception:
                return category_l1, category_l2
        return category_l1, category_l2
