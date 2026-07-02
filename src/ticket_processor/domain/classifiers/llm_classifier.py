"""LLM-backed classifier."""

from __future__ import annotations

import json
import re

from ticket_processor.domain.classifiers.base import BaseClassifier
from ticket_processor.domain.exceptions import ClassificationError
from ticket_processor.domain.models import ProductCategoryLevel1, ProductCategoryLevel2
from ticket_processor.domain.ports import LlmPort

SYSTEM_PROMPT = """Clasifica un producto usando SOLO esta taxonomía.
Devuelve JSON con este formato exacto:
{"nivel1":"Alimentación","nivel2":"Lácteos"}

Categorias nivel1:
- Alimentación
- Limpieza
- Electrónica
- Ropa
- Hogar
- Otros

Categorias nivel2:
- Lácteos
- Carne
- Pescado
- Verduras
- Frutas
- Panadería
- Legumbres
- Condimentos
- Bebidas
- Congelados
- Cereales
- Detergente
- Lavavajillas
- Limpieza Hogar
- Móviles
- Ordenadores
- Accesorios
- Camiseta
- Pantalón
- Calzado
- Decoración
- Muebles
- Utensilios
- Otros"""


class LlmClassifier(BaseClassifier):
    def __init__(self, llm: LlmPort) -> None:
        self._llm = llm

    def classify(self, product_name: str) -> tuple[ProductCategoryLevel1, ProductCategoryLevel2]:
        prompt = f"Producto: {product_name}\nJSON:"
        response = self._llm.complete(prompt, SYSTEM_PROMPT)
        match = re.search(r"\{[\s\S]*\}", response)
        if match is None:
            raise ClassificationError(
                "No JSON found in LLM response",
                context={"response": response[:200]},
            )

        try:
            payload = json.loads(match.group(0))
            category_l1 = ProductCategoryLevel1(payload["nivel1"])
            category_l2 = ProductCategoryLevel2(payload["nivel2"])
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise ClassificationError(
                "Invalid LLM classification response",
                context={"response": response[:200], "product_name": product_name},
            ) from exc

        return category_l1, category_l2
