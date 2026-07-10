"""Tests unitaires du service ChapterDetector (V2)."""

from __future__ import annotations

import pytest

from core.chapter_detector import ChapterDetector
from exceptions import ChapterDetectionError
from models import Subject
from tests.conftest import make_document_with_pages


def test_detects_chapters_and_extends_page_ranges(structure_dictionary) -> None:
    document = make_document_with_pages({
        1: "Chapitre 1 : Les fonctions\n\nContenu de la page un.",
        2: "Contenu de la page deux, toujours dans le chapitre un.",
        3: "Chapitre 2 : La cellule\n\nContenu de la page trois.",
    })

    result = ChapterDetector(structure_dictionary).detect(document)

    assert len(result.chapters) == 2
    assert result.chapters[0].page_numbers == [1, 2]
    assert result.chapters[1].page_numbers == [3]


def test_no_chapters_detected_is_not_an_error(structure_dictionary) -> None:
    document = make_document_with_pages({1: "Un simple recueil d'exercices sans titre de chapitre."})

    result = ChapterDetector(structure_dictionary).detect(document)

    assert result.chapters == []


def test_assigns_subject_to_chapter(structure_dictionary) -> None:
    document = make_document_with_pages({1: "Chapitre 1 : Les fonctions\n\nContenu."})
    document.subjects = [Subject(subject_code="mathematics", name="Mathématiques", page_numbers=[1], confidence=0.9)]

    result = ChapterDetector(structure_dictionary).detect(document)

    assert result.chapters[0].subject_id == document.subjects[0].subject_id


def test_raises_when_dictionary_invalid() -> None:
    with pytest.raises(ChapterDetectionError):
        ChapterDetector({"structure_indicators": {}})
