"""Fixtures pytest partagées par les tests unitaires et d'intégration."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from core.interfaces import ICleaningStrategy, IChunker, IEmbeddingModel, IOcrEngine, IVectorStore
from models import Chunk, Embedding


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Crée un petit PDF de test à deux pages et retourne son chemin."""
    pdf_path = tmp_path / "sample.pdf"
    document = fitz.open()
    document.new_page().insert_text((50, 72), "Page un de test.", fontsize=11)
    document.new_page().insert_text((50, 72), "Page deux de test.", fontsize=11)
    document.save(pdf_path)
    document.close()
    return pdf_path


class FakeOcrEngine(IOcrEngine):
    """Faux moteur OCR déterministe, utilisé pour les tests."""

    def __init__(self, text_by_page: dict[int, str] | None = None) -> None:
        self._text_by_page = text_by_page or {}
        self._call_count = 0

    @property
    def engine_name(self) -> str:
        return "fake_ocr"

    def extract_text(self, image_path: str, language: str) -> tuple[str, float]:
        self._call_count += 1
        text = self._text_by_page.get(
            self._call_count, f"Texte OCR simulé numero {self._call_count}."
        )
        return text, 90.0


class FakeCleaningStrategy(ICleaningStrategy):
    """Fausse stratégie de nettoyage : ne fait qu'un strip()."""

    @property
    def strategy_name(self) -> str:
        return "fake_cleaning"

    def clean(self, raw_text: str) -> str:
        return raw_text.strip()


class FakeChunker(IChunker):
    """Faux chunker : retourne le texte entier comme unique segment."""

    @property
    def strategy_name(self) -> str:
        return "fake_chunker"

    def split(self, text: str) -> list[str]:
        return [text]


class FakeEmbeddingModel(IEmbeddingModel):
    """Faux modèle d'embedding : vecteurs déterministes de dimension 4."""

    @property
    def model_name(self) -> str:
        return "fake-embedding-model"

    @property
    def dimension(self) -> int:
        return 4

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t)), 0.0, 0.0, 0.0] for t in texts]


class FakeVectorStore(IVectorStore):
    """Fausse base vectorielle en mémoire."""

    def __init__(self) -> None:
        self.collections: dict[str, list[tuple[Chunk, Embedding]]] = {}

    def create_collection(self, collection_name: str) -> None:
        self.collections.setdefault(collection_name, [])

    def add_embeddings(
        self, collection_name: str, chunks: list[Chunk], embeddings: list[Embedding]
    ) -> None:
        self.collections.setdefault(collection_name, [])
        self.collections[collection_name].extend(zip(chunks, embeddings))

    def count(self, collection_name: str) -> int:
        return len(self.collections.get(collection_name, []))


@pytest.fixture
def fake_ocr_engine() -> FakeOcrEngine:
    return FakeOcrEngine()


@pytest.fixture
def fake_cleaning_strategy() -> FakeCleaningStrategy:
    return FakeCleaningStrategy()


@pytest.fixture
def fake_chunker() -> FakeChunker:
    return FakeChunker()


@pytest.fixture
def fake_embedding_model() -> FakeEmbeddingModel:
    return FakeEmbeddingModel()


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()


@pytest.fixture
def subject_dictionary() -> dict:
    """Charge le vrai dictionnaire subject_detection.json du projet."""
    from config import load_config
    from utils import load_json_dictionary

    return load_json_dictionary(load_config().dictionaries.subject_detection_path)


@pytest.fixture
def level_dictionary() -> dict:
    """Charge le vrai dictionnaire level_indicators.json du projet."""
    from config import load_config
    from utils import load_json_dictionary

    return load_json_dictionary(load_config().dictionaries.level_indicators_path)


@pytest.fixture
def structure_dictionary() -> dict:
    """Charge le vrai dictionnaire structure_indicators.json du projet."""
    from config import load_config
    from utils import load_json_dictionary

    return load_json_dictionary(load_config().dictionaries.structure_indicators_path)


def make_document_with_pages(pages_cleaned_text: dict[int, str]):
    """Construit un Document avec des pages ayant déjà un cleaning_data.

    Utilitaire partagé par les tests des détecteurs V2.
    """
    from models import CleaningData, Document, Metadata, Page, PipelineInfo

    metadata = Metadata(filename="livre.pdf", file_size_bytes=10, total_pages=len(pages_cleaned_text))
    pipeline_info = PipelineInfo(ocr_engine="fake", embedding_model="fake", chunking_strategy="fake")
    document = Document(metadata=metadata, pipeline_info=pipeline_info)
    for page_number, text in pages_cleaned_text.items():
        page = Page(page_number=page_number)
        page.cleaning_data = CleaningData(cleaned_text=text, strategy_name="fake")
        document.pages.append(page)
    return document
