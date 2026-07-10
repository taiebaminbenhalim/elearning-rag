"""Test d'intégration du PipelineV2 complet.

Utilise les vrais dictionnaires JSON de référence (subject_detection,
level_indicators, structure_indicators) pour SubjectDetector,
LevelDetector, ChapterDetector et PedagogicalDetector, mais des fakes
pour OCR, chunking, embedding et vector store (conftest.py), afin de ne
pas dépendre de Tesseract, SemanticChunker, BGE-M3 ou ChromaDB réels.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from core.chapter_detector import ChapterDetector
from core.chunk_builder import ChunkBuilder
from core.cleaning_service import CleaningService
from core.embedding_service import EmbeddingService
from core.level_detector import LevelDetector
from core.ocr_service import OCRService
from core.paragraph_detector import ParagraphDetector
from core.pdf_loader import PDFLoader
from core.pedagogical_detector import PedagogicalDetector
from core.pipeline_v2 import PipelineV2
from core.structure_builder import StructureBuilder
from core.subject_detector import SubjectDetector
from core.validator import Validator
from core.vector_store import VectorStoreService
from models import Status
from pdf import ImageConverter, PDFReader

from core.interfaces import ICleaningStrategy, IOcrEngine


class _ScriptedOcrEngine(IOcrEngine):
    """OCR factice retournant un texte scolaire réaliste par page."""

    def __init__(self, texts: list[str]) -> None:
        self._texts = texts
        self._index = 0

    @property
    def engine_name(self) -> str:
        return "scripted_ocr"

    def extract_text(self, image_path: str, language: str) -> tuple[str, float]:
        text = self._texts[self._index]
        self._index += 1
        return text, 91.0


class _PassthroughCleaning(ICleaningStrategy):
    @property
    def strategy_name(self) -> str:
        return "passthrough"

    def clean(self, raw_text: str) -> str:
        return raw_text.strip()


@pytest.fixture
def two_page_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "manuel.pdf"
    document = fitz.open()
    document.new_page()
    document.new_page()
    document.save(pdf_path)
    document.close()
    return pdf_path


def test_pipeline_v2_runs_end_to_end(
    two_page_pdf: Path,
    tmp_path: Path,
    subject_dictionary,
    level_dictionary,
    structure_dictionary,
    fake_chunker,
    fake_embedding_model,
    fake_vector_store,
) -> None:
    scripted_texts = [
        "4ème année secondaire\nSection Mathématiques\n1er trimestre\n\n"
        "Chapitre 1 : Les fonctions\n\n"
        "Cours sur les fonctions dérivées, limite et continuité, intégrale et primitive, équation.\n\n"
        "Exercice 1\nCalculer la dérivée de f(x) = x^2 + 3x en utilisant le théorème de Rolle.",
        "Chapitre 2 : La cellule\n\n"
        "La cellule et le noyau et la mitose et le chromosome et l'ADN et la photosynthèse et le gène.",
    ]

    pdf_loader = PDFLoader(
        pdf_reader=PDFReader(),
        image_converter=ImageConverter(output_dir=tmp_path / "pages"),
        ocr_engine_name="scripted_ocr",
        embedding_model_name=fake_embedding_model.model_name,
        chunking_strategy_name=fake_chunker.strategy_name,
        pipeline_version="2.0.0",
    )

    pipeline = PipelineV2(
        pdf_loader=pdf_loader,
        ocr_service=OCRService(ocr_engine=_ScriptedOcrEngine(scripted_texts), language="fra"),
        cleaning_service=CleaningService(cleaning_strategy=_PassthroughCleaning()),
        subject_detector=SubjectDetector(subject_dictionary),
        level_detector=LevelDetector(level_dictionary),
        structure_builder=StructureBuilder(
            chapter_detector=ChapterDetector(structure_dictionary),
            pedagogical_detector=PedagogicalDetector(structure_dictionary),
            paragraph_detector=ParagraphDetector(),
        ),
        chunk_builder=ChunkBuilder(chunker=fake_chunker, language="fra"),
        embedding_service=EmbeddingService(embedding_model=fake_embedding_model),
        vector_store_service=VectorStoreService(
            vector_store=fake_vector_store, collection_name="test_v2_collection"
        ),
        validator=Validator(),
    )

    document = pipeline.run(two_page_pdf)

    assert document.status == Status.INDEXED
    assert len(document.subjects) >= 1
    assert document.subjects[0].subject_code == "mathematics"
    assert document.academic_context.level == "4ème année secondaire"
    assert document.academic_context.section == "Mathématiques"
    assert len(document.chapters) == 2
    assert any(e.pedagogical_type.value == "exercice" for e in document.pedagogical_elements)
    assert len(document.paragraphs) > 0
    assert len(document.chunks) > 0
    assert len(document.embeddings) == len(document.chunks)
    assert fake_vector_store.count("test_v2_collection") == len(document.chunks)
