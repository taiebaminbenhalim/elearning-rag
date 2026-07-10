"""Tests unitaires du service ChunkBuilder."""

from __future__ import annotations

import pytest

from core.chunk_builder import ChunkBuilder
from exceptions import ChunkingError
from models import Document, Metadata, Paragraph, PipelineInfo


def _make_document_with_paragraphs() -> Document:
    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=1)
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    document = Document(metadata=metadata, pipeline_info=pipeline_info)
    document.paragraphs.append(Paragraph(text="Un paragraphe de test.", page_numbers=[1]))
    return document


def test_chunk_builder_creates_chunks(fake_chunker) -> None:
    builder = ChunkBuilder(chunker=fake_chunker, language="fra")
    document = _make_document_with_paragraphs()

    result = builder.build(document)

    assert len(result.chunks) == 1
    assert result.chunks[0].metadata.creation_method == "fake_chunker"
    assert result.chunks[0].metadata.chunk_index == 0


def test_chunk_builder_raises_without_paragraphs(fake_chunker) -> None:
    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=1)
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    document = Document(metadata=metadata, pipeline_info=pipeline_info)

    with pytest.raises(ChunkingError):
        ChunkBuilder(chunker=fake_chunker, language="fra").build(document)
