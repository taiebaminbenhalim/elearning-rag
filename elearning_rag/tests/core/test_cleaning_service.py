"""Tests unitaires du service CleaningService."""

from __future__ import annotations

import pytest

from core.cleaning_service import CleaningService
from exceptions import CleaningError
from models import Document, Metadata, OCRData, Page, PipelineInfo


def _make_document_with_ocr(with_ocr: bool = True) -> Document:
    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=1)
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    document = Document(metadata=metadata, pipeline_info=pipeline_info)
    page = Page(page_number=1)
    if with_ocr:
        page.ocr_data = OCRData(raw_text="  Texte brut.  ", mean_confidence=90.0, engine_name="fake", language="fra")
    document.pages.append(page)
    return document


def test_cleaning_service_fills_cleaning_data(fake_cleaning_strategy) -> None:
    service = CleaningService(cleaning_strategy=fake_cleaning_strategy)
    document = _make_document_with_ocr()

    result = service.process(document)

    assert result.pages[0].cleaning_data is not None
    assert result.pages[0].cleaning_data.cleaned_text == "Texte brut."
    assert result.pages[0].ocr_data.raw_text == "  Texte brut.  "  # texte original intact


def test_cleaning_service_raises_without_ocr_data(fake_cleaning_strategy) -> None:
    service = CleaningService(cleaning_strategy=fake_cleaning_strategy)
    document = _make_document_with_ocr(with_ocr=False)

    with pytest.raises(CleaningError):
        service.process(document)
