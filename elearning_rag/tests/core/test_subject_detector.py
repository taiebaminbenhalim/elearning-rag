"""Tests unitaires du service SubjectDetector (V2)."""

from __future__ import annotations

import pytest

from core.subject_detector import SubjectDetector
from exceptions import SubjectDetectionError
from tests.conftest import make_document_with_pages


def test_detects_and_groups_consecutive_pages(subject_dictionary) -> None:
    document = make_document_with_pages({
        1: "Cours sur les fonctions dérivées, limite et continuité, intégrale et primitive, équation.",
        2: "Suite du cours sur la dérivée et la fonction et le théorème et l'asymptote et la tangente.",
        3: "La cellule et le noyau et la mitose et le chromosome et l'ADN et la photosynthèse et le gène.",
    })

    detector = SubjectDetector(subject_dictionary)
    result = detector.detect(document)

    assert len(result.subjects) == 2
    assert result.subjects[0].page_numbers == [1, 2]
    assert result.subjects[1].page_numbers == [3]
    assert result.subjects[0].subject_code == "mathematics"
    assert result.subjects[1].subject_code == "svt"


def test_raises_when_no_cleaning_data() -> None:
    from models import Document, Metadata, Page, PipelineInfo

    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=1)
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    document = Document(metadata=metadata, pipeline_info=pipeline_info)
    document.pages.append(Page(page_number=1))  # pas de cleaning_data

    with pytest.raises(SubjectDetectionError):
        SubjectDetector({"subjects": {}}).detect(document)


def test_raises_when_dictionary_invalid() -> None:
    with pytest.raises(SubjectDetectionError):
        SubjectDetector({"not_subjects": {}})


def test_unknown_subject_when_no_keywords_match(subject_dictionary) -> None:
    document = make_document_with_pages({1: "xyz abc qwe rien de connu ici du tout."})

    detector = SubjectDetector(subject_dictionary)
    result = detector.detect(document)

    assert result.subjects[0].subject_code == "unknown"
    assert result.subjects[0].confidence == 0.0
