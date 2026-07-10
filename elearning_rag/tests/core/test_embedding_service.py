"""Tests unitaires du service EmbeddingService."""

from __future__ import annotations

import pytest

from core.embedding_service import EmbeddingService
from exceptions import EmbeddingError
from models import Chunk, ChunkMetadata, Document, Metadata, PipelineInfo


def _make_document_with_chunks() -> Document:
    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=1)
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    document = Document(metadata=metadata, pipeline_info=pipeline_info)
    document.chunks.append(
        Chunk(
            text="texte du chunk",
            paragraph_ids=["p1"],
            page_numbers=[1],
            metadata=ChunkMetadata(chunk_index=0, creation_method="fake", word_count=3, char_count=14),
        )
    )
    return document


def test_embedding_service_generates_one_embedding_per_chunk(fake_embedding_model) -> None:
    service = EmbeddingService(embedding_model=fake_embedding_model)
    document = _make_document_with_chunks()

    result = service.generate(document)

    assert len(result.embeddings) == 1
    assert result.embeddings[0].chunk_id == document.chunks[0].chunk_id
    assert result.embeddings[0].dimension == fake_embedding_model.dimension


def test_embedding_service_raises_without_chunks(fake_embedding_model) -> None:
    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=1)
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    document = Document(metadata=metadata, pipeline_info=pipeline_info)

    with pytest.raises(EmbeddingError):
        EmbeddingService(embedding_model=fake_embedding_model).generate(document)
