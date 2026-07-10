"""Tests unitaires du service StructureAnalyzer."""

from __future__ import annotations

import pytest

from core.structure_analyzer import StructureAnalyzer
from exceptions import StructureAnalysisError
from models import CleaningData, Document, Metadata, Page, PipelineInfo


def _make_document(cleaned_texts: dict[int, str]) -> Document:
    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=len(cleaned_texts))
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    document = Document(metadata=metadata, pipeline_info=pipeline_info)
    for page_number, text in cleaned_texts.items():
        page = Page(page_number=page_number)
        page.cleaning_data = CleaningData(cleaned_text=text, strategy_name="fake")
        document.pages.append(page)
    return document


def test_detects_chapters_and_paragraphs() -> None:
    document = _make_document({
        1: "Chapitre 1 Introduction\n\nPremier paragraphe du chapitre un.\n\nSecond paragraphe.",
        2: "Chapitre 2 Suite\n\nParagraphe du chapitre deux.",
    })

    result = StructureAnalyzer().analyze(document)

    assert len(result.chapters) == 2
    assert len(result.paragraphs) == 3
    assert all(p.chapter_id is not None for p in result.paragraphs)


def test_fallback_chapter_when_no_titles_found() -> None:
    document = _make_document({1: "Un simple paragraphe sans titre de chapitre."})

    result = StructureAnalyzer().analyze(document)

    assert len(result.chapters) == 1
    assert result.chapters[0].title == "Document sans chapitres détectés"
    assert len(result.paragraphs) == 1


def test_raises_when_no_cleaned_text_available() -> None:
    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=1)
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    document = Document(metadata=metadata, pipeline_info=pipeline_info)
    document.pages.append(Page(page_number=1))  # pas de cleaning_data

    with pytest.raises(StructureAnalysisError):
        StructureAnalyzer().analyze(document)
