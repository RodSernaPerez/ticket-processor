from __future__ import annotations

from ticket_processor.domain.classifiers import CompositeClassifier, KeywordClassifier
from ticket_processor.domain.models import ProductCategoryLevel1, ProductCategoryLevel2


def test_keyword_classifier_matches_known_taxonomy() -> None:
    classifier = KeywordClassifier()
    category_l1, category_l2 = classifier.classify("Leche Entera 1L")
    assert category_l1 == ProductCategoryLevel1.ALIMENTACION
    assert category_l2 == ProductCategoryLevel2.LACTEOS


def test_keyword_classifier_returns_otros_for_unknown() -> None:
    classifier = KeywordClassifier()
    category_l1, category_l2 = classifier.classify("Producto Alienigena")
    assert category_l1 == ProductCategoryLevel1.OTROS
    assert category_l2 == ProductCategoryLevel2.OTROS


def test_composite_classifier_falls_back_to_keyword_when_no_llm() -> None:
    classifier = CompositeClassifier(KeywordClassifier())
    category_l1, category_l2 = classifier.classify("Detergente Lavadora")
    assert category_l1 == ProductCategoryLevel1.LIMPIEZA
    assert category_l2 == ProductCategoryLevel2.DETERGENTE
