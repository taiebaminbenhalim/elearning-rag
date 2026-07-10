"""Tests unitaires du service OCRService."""

from __future__ import annotations

import pytest

from core.ocr_service import OCRService
from exceptions import OCRError
from models import Document, Metadata, Page, PipelineInfo


def _make_document_with_pages(with_image: bool = True) -> Document:
    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=1)
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    document = Document(metadata=metadata, pipeline_info=pipeline_info)
    document.pages.append(Page(page_number=1, image_path="/tmp/fake.png" if with_image else None))
    return document


def test_ocr_service_fills_ocr_data(fake_ocr_engine) -> None:
    service = OCRService(ocr_engine=fake_ocr_engine, language="fra")
    document = _make_document_with_pages()

    result = service.process(document)

    assert result.pages[0].ocr_data is not None
    assert result.pages[0].ocr_data.engine_name == "fake_ocr"
    assert result.pages[0].ocr_data.language == "fra"


def test_ocr_service_raises_when_no_image(fake_ocr_engine) -> None:
    service = OCRService(ocr_engine=fake_ocr_engine, language="fra")
    document = _make_document_with_pages(with_image=False)

    with pytest.raises(OCRError):
        service.process(document)
