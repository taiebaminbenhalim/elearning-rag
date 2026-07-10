"""Tests unitaires du service ParagraphDetector (V2, logique V1 inchangée)."""

from __future__ import annotations

import pytest

from core.paragraph_detector import ParagraphDetector
from exceptions import StructureAnalysisError
from models import Chapter
from tests.conftest import make_document_with_pages


def test_detects_paragraphs_and_attaches_chapter() -> None:
    document = make_document_with_pages({1: "Premier paragraphe.\n\nSecond paragraphe."})
    chapter = Chapter(title="Chapitre 1", number=1, page_numbers=[1])
    document.chapters = [chapter]

    result = ParagraphDetector().detect(document)

    assert len(result.paragraphs) == 2
    assert all(p.chapter_id == chapter.chapter_id for p in result.paragraphs)
    assert chapter.paragraph_ids == [p.paragraph_id for p in result.paragraphs]


def test_works_without_any_chapter() -> None:
    document = make_document_with_pages({1: "Un paragraphe sans chapitre."})

    result = ParagraphDetector().detect(document)

    assert len(result.paragraphs) == 1
    assert result.paragraphs[0].chapter_id is None


def test_raises_when_no_paragraph_detected() -> None:
    document = make_document_with_pages({1: ""})

    with pytest.raises(StructureAnalysisError):
        ParagraphDetector().detect(document)
