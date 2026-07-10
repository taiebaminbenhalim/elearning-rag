"""Configuration centralisée du projet.

Aucun paramètre technique ne doit être codé en dur dans les services. Tous
les services de `core/` reçoivent leurs paramètres via une instance de
:class:`Config` (injection de dépendances), construite ici à partir de
valeurs par défaut éventuellement surchargées par des variables
d'environnement.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_str(key: str, default: str) -> str:
    """Lit une variable d'environnement chaîne, avec valeur par défaut."""
    return os.environ.get(key, default)


def _env_int(key: str, default: int) -> int:
    """Lit une variable d'environnement entière, avec valeur par défaut."""
    value = os.environ.get(key)
    return int(value) if value is not None else default


def _env_float(key: str, default: float) -> float:
    """Lit une variable d'environnement flottante, avec valeur par défaut."""
    value = os.environ.get(key)
    return float(value) if value is not None else default


@dataclass(frozen=True)
class PDFConfig:
    """Paramètres de conversion PDF → image.

    Attributes:
        image_output_dir: Répertoire de sortie des images de pages générées.
        zoom_factor: Facteur de zoom appliqué lors du rendu (qualité OCR).
        image_format: Format des images générées (``"png"`` recommandé).
    """

    image_output_dir: Path = field(
        default_factory=lambda: Path(_env_str("PDF_IMAGE_OUTPUT_DIR", "data/pages"))
    )
    zoom_factor: float = field(default_factory=lambda: _env_float("PDF_ZOOM_FACTOR", 2.0))
    image_format: str = field(default_factory=lambda: _env_str("PDF_IMAGE_FORMAT", "png"))


@dataclass(frozen=True)
class OCRConfig:
    """Paramètres du moteur OCR.

    Attributes:
        engine_name: Nom du moteur OCR utilisé en V1 (``"tesseract"``).
        language: Code(s) langue Tesseract (ex: ``"fra"``, ``"fra+eng"``).
        min_confidence: Confiance minimale en dessous de laquelle une page
            OCR est considérée comme suspecte (utilisé par le Validator).
        apply_preprocessing: Active le prétraitement d'image (OpenCV)
            avant OCR (binarisation, débruitage).
    """

    engine_name: str = "tesseract"
    language: str = field(default_factory=lambda: _env_str("OCR_LANGUAGE", "fra"))
    min_confidence: float = field(default_factory=lambda: _env_float("OCR_MIN_CONFIDENCE", 30.0))
    apply_preprocessing: bool = True
    # Chemin explicite vers l'exécutable Tesseract. Nécessaire sous Windows
    # lorsque Tesseract n'est pas dans le PATH, ex:
    # "C:\\Program Files\\Tesseract-OCR\\tesseract.exe". Laisser à None sous
    # Linux/macOS si `tesseract` est déjà accessible dans le PATH.
    tesseract_cmd: str | None = field(
        default_factory=lambda: os.environ.get("TESSERACT_CMD") or None
    )


@dataclass(frozen=True)
class CleaningConfig:
    """Paramètres de nettoyage du texte OCR.

    Attributes:
        strategy_name: Nom de la stratégie de nettoyage utilisée en V1.
        min_line_length: Longueur minimale d'une ligne pour être conservée.
    """

    strategy_name: str = "basic_cleaning"
    min_line_length: int = 1


@dataclass(frozen=True)
class ChunkingConfig:
    """Paramètres de découpage sémantique.

    Attributes:
        strategy_name: Nom de la stratégie de chunking utilisée en V1.
        breakpoint_threshold_type: Type de seuil du SemanticChunker.
        breakpoint_threshold_amount: Valeur du seuil du SemanticChunker.
    """

    strategy_name: str = "semantic_chunker"
    breakpoint_threshold_type: str = field(
        default_factory=lambda: _env_str("CHUNKING_THRESHOLD_TYPE", "percentile")
    )
    breakpoint_threshold_amount: float = field(
        default_factory=lambda: _env_float("CHUNKING_THRESHOLD_AMOUNT", 95.0)
    )


@dataclass(frozen=True)
class EmbeddingConfig:
    """Paramètres du modèle d'embedding.

    Attributes:
        model_name: Nom du modèle d'embedding imposé en V1.
        device: Device d'inférence (``"cpu"`` ou ``"cuda"``).
        normalize_embeddings: Normalise les vecteurs (norme L2 = 1).
        batch_size: Taille de batch pour la génération des embeddings.
    """

    model_name: str = field(
        default_factory=lambda: _env_str("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
    )
    device: str = field(default_factory=lambda: _env_str("EMBEDDING_DEVICE", "cpu"))
    normalize_embeddings: bool = True
    batch_size: int = field(default_factory=lambda: _env_int("EMBEDDING_BATCH_SIZE", 16))


@dataclass(frozen=True)
class VectorStoreConfig:
    """Paramètres de la base vectorielle.

    Attributes:
        persist_directory: Répertoire de persistance de ChromaDB.
        collection_name: Nom de la collection ChromaDB utilisée en V1.
    """

    persist_directory: Path = field(
        default_factory=lambda: Path(_env_str("VECTOR_STORE_DIR", "data/vector_store"))
    )
    collection_name: str = field(
        default_factory=lambda: _env_str("VECTOR_STORE_COLLECTION", "elearning_documents")
    )


_PROJECT_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class DictionariesConfig:
    """Chemins des dictionnaires JSON de référence utilisés par la V2.

    Introduit en V2 pour la détection des matières, du niveau scolaire et
    de la structure pédagogique. Aucun de ces chemins ne doit être codé en
    dur dans un service : ils sont toujours lus depuis cette configuration.

    Attributes:
        subject_detection_path: Chemin de ``subject_detection.json``.
        level_indicators_path: Chemin de ``level_indicators.json``.
        structure_indicators_path: Chemin de ``structure_indicators.json``.
    """

    subject_detection_path: Path = field(
        default_factory=lambda: Path(
            _env_str(
                "SUBJECT_DETECTION_DICT_PATH",
                str(_PROJECT_ROOT / "data" / "dictionaries" / "subject_detection.json"),
            )
        )
    )
    level_indicators_path: Path = field(
        default_factory=lambda: Path(
            _env_str(
                "LEVEL_INDICATORS_DICT_PATH",
                str(_PROJECT_ROOT / "data" / "dictionaries" / "level_indicators.json"),
            )
        )
    )
    structure_indicators_path: Path = field(
        default_factory=lambda: Path(
            _env_str(
                "STRUCTURE_INDICATORS_DICT_PATH",
                str(_PROJECT_ROOT / "data" / "dictionaries" / "structure_indicators.json"),
            )
        )
    )


@dataclass(frozen=True)
class Config:
    """Configuration globale du projet, agrégeant toutes les sous-configurations.

    Une seule instance de :class:`Config` doit être créée (dans ``main.py``
    ou ``api/app.py``) puis injectée dans les services qui en ont besoin.

    Attributes:
        pdf: Configuration de conversion PDF → image.
        ocr: Configuration du moteur OCR.
        cleaning: Configuration du nettoyage de texte.
        chunking: Configuration du chunking sémantique.
        embedding: Configuration du modèle d'embedding.
        vector_store: Configuration de la base vectorielle.
        dictionaries: Chemins des dictionnaires JSON de référence (V2).
        pipeline_version: Version du pipeline exposée dans PipelineInfo.
    """

    pdf: PDFConfig = field(default_factory=PDFConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    cleaning: CleaningConfig = field(default_factory=CleaningConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    dictionaries: DictionariesConfig = field(default_factory=DictionariesConfig)
    pipeline_version: str = "1.0.0"


def load_config() -> Config:
    """Construit la configuration globale du projet.

    Point d'entrée unique pour obtenir une :class:`Config`. Centralise la
    lecture des variables d'environnement afin que les services n'aient
    jamais à lire ``os.environ`` directement.

    Returns:
        Une instance de :class:`Config` prête à être injectée dans le pipeline.
    """
    return Config()
