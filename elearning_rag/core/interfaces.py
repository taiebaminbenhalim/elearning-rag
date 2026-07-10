"""Ports abstraits (interfaces) utilisés par les services de `core/`.

Ce module matérialise le principe d'inversion des dépendances (DIP) :
les services d'orchestration de `core/` ne dépendent jamais d'une
implémentation technique concrète (Tesseract, SemanticChunker, BGE-M3,
ChromaDB), mais uniquement de ces interfaces. Les implémentations
concrètes vivent dans `pdf/`, `ocr/`, `cleaning/`, `chunking/`,
`embedding/` et `vector_store/`, et sont injectées au moment de la
construction du :class:`~core.pipeline.Pipeline`.

Cela permet de remplacer Tesseract par PaddleOCR, ou BGE-M3 par un autre
modèle, sans modifier une seule ligne de `core/`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from models import Chunk, Embedding


class IOcrEngine(ABC):
    """Port abstrait d'un moteur OCR.

    Toute implémentation (Tesseract, PaddleOCR...) doit produire, pour une
    image de page donnée, le texte brut extrait et une confiance moyenne.
    """

    @abstractmethod
    def extract_text(self, image_path: str, language: str) -> tuple[str, float]:
        """Extrait le texte d'une image de page.

        Args:
            image_path: Chemin de l'image de la page à traiter.
            language: Code langue à utiliser pour l'OCR.

        Returns:
            Un tuple ``(texte_brut, confiance_moyenne)``.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Nom du moteur OCR (utilisé dans OCRData.engine_name)."""
        raise NotImplementedError


class ICleaningStrategy(ABC):
    """Port abstrait d'une stratégie de nettoyage de texte."""

    @abstractmethod
    def clean(self, raw_text: str) -> str:
        """Nettoie un texte brut issu de l'OCR.

        Args:
            raw_text: Texte brut à nettoyer.

        Returns:
            Le texte nettoyé.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Nom de la stratégie de nettoyage (utilisé dans CleaningData.strategy_name)."""
        raise NotImplementedError


class IChunker(ABC):
    """Port abstrait d'une stratégie de découpage sémantique.

    Un chunker doit fonctionner indépendamment du modèle d'embedding final,
    conformément au cahier des charges.
    """

    @abstractmethod
    def split(self, text: str) -> list[str]:
        """Découpe un texte en segments sémantiquement cohérents.

        Args:
            text: Texte à découper (typiquement le texte d'un paragraphe).

        Returns:
            Liste des segments de texte produits.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """Nom de la stratégie de chunking (utilisé dans ChunkMetadata.creation_method)."""
        raise NotImplementedError


class IEmbeddingModel(ABC):
    """Port abstrait d'un modèle de génération d'embeddings.

    L'implémentation concrète doit charger le modèle une seule fois en
    mémoire et le réutiliser pour tous les appels.
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Génère un vecteur d'embedding pour chaque texte fourni.

        Args:
            texts: Liste de textes à encoder (typiquement des textes de chunks).

        Returns:
            Liste de vecteurs, dans le même ordre que ``texts``.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Nom du modèle d'embedding (utilisé dans Embedding.model_name)."""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Dimension des vecteurs produits par le modèle."""
        raise NotImplementedError


class IVectorStore(ABC):
    """Port abstrait d'une base vectorielle."""

    @abstractmethod
    def create_collection(self, collection_name: str) -> None:
        """Crée (ou récupère si déjà existante) une collection.

        Args:
            collection_name: Nom de la collection à créer/récupérer.
        """
        raise NotImplementedError

    @abstractmethod
    def add_embeddings(
        self,
        collection_name: str,
        chunks: list[Chunk],
        embeddings: list[Embedding],
    ) -> None:
        """Enregistre des chunks et leurs embeddings dans la collection.

        Args:
            collection_name: Nom de la collection cible.
            chunks: Chunks à indexer (fournissent le texte et les métadonnées).
            embeddings: Embeddings correspondants, un par chunk, même ordre.
        """
        raise NotImplementedError

    @abstractmethod
    def count(self, collection_name: str) -> int:
        """Retourne le nombre d'éléments indexés dans une collection.

        Args:
            collection_name: Nom de la collection à interroger.

        Returns:
            Nombre d'éléments présents dans la collection.
        """
        raise NotImplementedError
