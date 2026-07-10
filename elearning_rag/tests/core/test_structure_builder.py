"""Tests unitaires du service StructureBuilder (V2)."""

from __future__ import annotations

from core.chapter_detector import ChapterDetector
from core.paragraph_detector import ParagraphDetector
from core.pedagogical_detector import PedagogicalDetector
from core.structure_builder import StructureBuilder
from models import Status
from tests.conftest import make_document_with_pages


def test_orchestrates_all_three_detectors(structure_dictionary) -> None:
    document = make_document_with_pages({
        1: "Chapitre 1 : Les fonctions\n\nExercice 1\nCalculer la derivee.",
    })

    builder = StructureBuilder(
        chapter_detector=ChapterDetector(structure_dictionary),
        pedagogical_detector=PedagogicalDetector(structure_dictionary),
        paragraph_detector=ParagraphDetector(),
    )
    result = builder.build(document)

    assert len(result.chapters) == 1
    assert len(result.paragraphs) >= 1
    assert result.status == Status.STRUCTURED
    assert result.pipeline_info.status == Status.STRUCTURED
