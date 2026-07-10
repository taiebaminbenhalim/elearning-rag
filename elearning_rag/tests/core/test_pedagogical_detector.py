"""Tests unitaires du service PedagogicalDetector (V2)."""

from __future__ import annotations

import pytest

from core.pedagogical_detector import PedagogicalDetector
from exceptions import PedagogicalDetectionError
from models import Chapter, PedagogicalType
from tests.conftest import make_document_with_pages


def test_detects_exercise_and_attaches_to_chapter(structure_dictionary) -> None:
    document = make_document_with_pages({1: "Exercice 1\nCalculer la derivee de f(x)."})
    chapter = Chapter(title="Chapitre 1", number=1, page_numbers=[1])
    document.chapters = [chapter]

    result = PedagogicalDetector(structure_dictionary).detect(document)

    assert len(result.pedagogical_elements) >= 1
    element = result.pedagogical_elements[0]
    assert element.pedagogical_type == PedagogicalType.EXERCICE
    assert element.chapter_id == chapter.chapter_id


def test_raises_when_dictionary_invalid() -> None:
    with pytest.raises(PedagogicalDetectionError):
        PedagogicalDetector({"structure_indicators": {}})


def test_no_elements_detected_is_not_an_error(structure_dictionary) -> None:
    document = make_document_with_pages({1: "Un texte neutre sans aucun marqueur pedagogique."})

    result = PedagogicalDetector(structure_dictionary).detect(document)

    assert result.pedagogical_elements == []
