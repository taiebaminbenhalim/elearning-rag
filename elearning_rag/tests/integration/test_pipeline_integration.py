"""Test d'intégration du Pipeline complet, avec des implémentations factices.

Ce test vérifie l'orchestration bout en bout (PDFLoader -> OCR -> Cleaning
-> StructureAnalyzer -> ChunkBuilder -> EmbeddingService ->
VectorStoreService) sans dépendre de Tesseract, SemanticChunker, BGE-M3 ou
ChromaDB réels : seule la conversion PDF -> image (PyMuPDF/Pillow) est
réelle, tout le reste passe par les fakes définis dans conftest.py.
"""

from __future__ import annotations

from pathlib import Path

from core.chunk_builder import ChunkBuilder
from core.cleaning_service import CleaningService
from core.embedding_service import EmbeddingService
from core.ocr_service import OCRService
from core.pdf_loader import PDFLoader
from core.pipeline import Pipeline
from core.structure_analyzer import StructureAnalyzer
from core.validator import Validator
from core.vector_store import VectorStoreService
from models import Status
from pdf import ImageConverter, PDFReader


def test_pipeline_runs_end_to_end(
    sample_pdf: Path,
    tmp_path: Path,
    fake_ocr_engine,
    fake_cleaning_strategy,
    fake_chunker,
    fake_embedding_model,
    fake_vector_store,
) -> None:
    pdf_loader = PDFLoader(
        pdf_reader=PDFReader(),
        image_converter=ImageConverter(output_dir=tmp_path / "pages"),
        ocr_engine_name=fake_ocr_engine.engine_name,
        embedding_model_name=fake_embedding_model.model_name,
        chunking_strategy_name=fake_chunker.strategy_name,
        pipeline_version="1.0.0",
    )
    pipeline = Pipeline(
        pdf_loader=pdf_loader,
        ocr_service=OCRService(ocr_engine=fake_ocr_engine, language="fra"),
        cleaning_service=CleaningService(cleaning_strategy=fake_cleaning_strategy),
        structure_analyzer=StructureAnalyzer(),
        chunk_builder=ChunkBuilder(chunker=fake_chunker, language="fra"),
        embedding_service=EmbeddingService(embedding_model=fake_embedding_model),
        vector_store_service=VectorStoreService(
            vector_store=fake_vector_store, collection_name="test_collection"
        ),
        validator=Validator(),
    )

    document = pipeline.run(sample_pdf)

    assert document.status == Status.INDEXED
    assert len(document.pages) == 2
    assert len(document.chunks) > 0
    assert len(document.embeddings) == len(document.chunks)
    assert fake_vector_store.count("test_collection") == len(document.chunks)
    assert document.pipeline_info.duration_seconds is not None
