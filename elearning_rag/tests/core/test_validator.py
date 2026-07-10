"""Tests unitaires du service Validator."""

from __future__ import annotations

import pytest

from core.validator import Validator
from exceptions import ValidationError
from models import Chunk, ChunkMetadata, Document, Embedding, Metadata, Paragraph, PipelineInfo


def _make_empty_document() -> Document:
    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=0)
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    return Document(metadata=metadata, pipeline_info=pipeline_info)


def test_validate_loaded_raises_when_no_pages() -> None:
    with pytest.raises(ValidationError):
        Validator().validate_loaded(_make_empty_document())


def test_validate_structure_raises_when_no_paragraphs() -> None:
    with pytest.raises(ValidationError):
        Validator().validate_structure(_make_empty_document())


def test_validate_chunks_raises_on_empty_chunk_text() -> None:
    document = _make_empty_document()
    document.chunks.append(
        Chunk(
            text="   ",
            paragraph_ids=["p1"],
            page_numbers=[1],
            metadata=ChunkMetadata(chunk_index=0, creation_method="fake", word_count=0, char_count=0),
        )
    )

    with pytest.raises(ValidationError):
        Validator().validate_chunks(document)


def test_validate_embeddings_raises_on_count_mismatch() -> None:
    document = _make_empty_document()
    document.chunks.append(
        Chunk(
            text="texte",
            paragraph_ids=["p1"],
            page_numbers=[1],
            metadata=ChunkMetadata(chunk_index=0, creation_method="fake", word_count=1, char_count=5),
        )
    )
    # Aucun embedding ajouté -> mismatch 1 chunk / 0 embedding

    with pytest.raises(ValidationError):
        Validator().validate_embeddings(document)


def test_validate_embeddings_passes_when_consistent() -> None:
    document = _make_empty_document()
    chunk = Chunk(
        text="texte",
        paragraph_ids=["p1"],
        page_numbers=[1],
        metadata=ChunkMetadata(chunk_index=0, creation_method="fake", word_count=1, char_count=5),
    )
    document.chunks.append(chunk)
    document.embeddings.append(
        Embedding(chunk_id=chunk.chunk_id, vector=[0.1, 0.2], model_name="fake", dimension=2)
    )

    Validator().validate_embeddings(document)  # ne doit pas lever


def test_validate_subjects_raises_when_no_subjects() -> None:
    with pytest.raises(ValidationError):
        Validator().validate_subjects(_make_empty_document())


def test_validate_subjects_raises_when_pages_uncovered() -> None:
    from models import Page, Subject

    document = _make_empty_document()
    document.pages.append(Page(page_number=1))
    document.pages.append(Page(page_number=2))
    document.subjects.append(
        Subject(subject_code="mathematics", name="Mathématiques", page_numbers=[1], confidence=0.5)
    )

    with pytest.raises(ValidationError):
        Validator().validate_subjects(document)


def test_validate_subjects_passes_when_all_pages_covered() -> None:
    from models import Page, Subject

    document = _make_empty_document()
    document.pages.append(Page(page_number=1))
    document.subjects.append(
        Subject(subject_code="mathematics", name="Mathématiques", page_numbers=[1], confidence=0.5)
    )

    Validator().validate_subjects(document)  # ne doit pas lever


def test_validate_academic_context_never_raises() -> None:
    Validator().validate_academic_context(_make_empty_document())  # ne doit jamais lever


def test_validate_structure_v2_raises_when_no_paragraphs() -> None:
    with pytest.raises(ValidationError):
        Validator().validate_structure_v2(_make_empty_document())


def test_validate_structure_v2_passes_without_chapters() -> None:
    from models import Paragraph

    document = _make_empty_document()
    document.paragraphs.append(Paragraph(text="Un paragraphe sans chapitre."))

    Validator().validate_structure_v2(document)  # ne doit pas lever, chapitres optionnels
