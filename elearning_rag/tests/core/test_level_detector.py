"""Tests unitaires du service LevelDetector (V2)."""

from __future__ import annotations

from core.level_detector import LevelDetector
from tests.conftest import make_document_with_pages


def test_detects_full_academic_context(level_dictionary) -> None:
    document = make_document_with_pages({
        1: "4ème année secondaire\nSection Mathématiques\n1er trimestre\nAnnée scolaire 2023-2024",
    })

    result = LevelDetector(level_dictionary).detect(document)

    assert result.academic_context.level == "4ème année secondaire"
    assert result.academic_context.section == "Mathématiques"
    assert result.academic_context.trimester == "1er trimestre"
    assert result.academic_context.school_year == "2023-2024"
    assert result.academic_context.confidence == 1.0


def test_returns_none_fields_when_nothing_found(level_dictionary) -> None:
    document = make_document_with_pages({1: "Un texte qui ne contient aucun indice de niveau."})

    result = LevelDetector(level_dictionary).detect(document)

    assert result.academic_context.level is None
    assert result.academic_context.confidence == 0.0


def test_only_scans_configured_number_of_pages(level_dictionary) -> None:
    pages = {i: "texte neutre" for i in range(1, 8)}
    pages[7] = "4ème année secondaire"  # au-delà de pages_to_scan=5 par défaut
    document = make_document_with_pages(pages)

    result = LevelDetector(level_dictionary, pages_to_scan=5).detect(document)

    assert result.academic_context.level is None
