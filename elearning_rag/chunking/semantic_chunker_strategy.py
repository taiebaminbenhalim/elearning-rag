"""Stratégie de chunking sémantique basée sur LangChain SemanticChunker."""

from __future__ import annotations

from typing import Any

from langchain_experimental.text_splitter import SemanticChunker

from core.interfaces import IChunker, IEmbeddingModel
from exceptions import ChunkingError
from utils import get_logger

logger = get_logger(__name__)


class _EmbeddingsAdapter:
    """Adapte un :class:`IEmbeddingModel` du projet à l'interface attendue par LangChain.

    LangChain attend un objet exposant ``embed_documents`` et
    ``embed_query``. Cet adaptateur permet de réutiliser le même
    :class:`IEmbeddingModel` (BGE-M3) pour le chunking sémantique sans
    dupliquer le chargement du modèle, tout en gardant ``ChunkBuilder``
    découplé du modèle d'embedding via l'injection de dépendances.
    """

    def __init__(self, embedding_model: IEmbeddingModel) -> None:
        self._embedding_model = embedding_model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embedding_model.embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._embedding_model.embed([text])[0]


class SemanticChunkerStrategy(IChunker):
    """Stratégie de chunking V1, utilisant exclusivement SemanticChunker.

    Attributes:
        breakpoint_threshold_type: Type de seuil utilisé par SemanticChunker
            pour détecter les points de coupure sémantiques.
        breakpoint_threshold_amount: Valeur du seuil associé.
    """

    def __init__(
        self,
        embedding_model: IEmbeddingModel,
        breakpoint_threshold_type: str = "percentile",
        breakpoint_threshold_amount: float = 95.0,
    ) -> None:
        """Initialise la stratégie de chunking sémantique.

        Args:
            embedding_model: Modèle d'embedding déjà chargé, réutilisé pour
                détecter les ruptures sémantiques (évite un second chargement
                de modèle).
            breakpoint_threshold_type: Type de seuil SemanticChunker.
            breakpoint_threshold_amount: Valeur du seuil SemanticChunker.
        """
        adapter = _EmbeddingsAdapter(embedding_model)
        self._splitter = SemanticChunker(
            adapter,
            breakpoint_threshold_type=breakpoint_threshold_type,
            breakpoint_threshold_amount=breakpoint_threshold_amount,
        )

    @property
    def strategy_name(self) -> str:
        """Nom de la stratégie de chunking."""
        return "semantic_chunker"

    def split(self, text: str) -> list[str]:
        """Découpe un texte en segments sémantiquement cohérents.

        Args:
            text: Texte à découper (typiquement le texte d'un paragraphe).

        Returns:
            Liste des segments de texte produits, textes vides exclus.

        Raises:
            ChunkingError: Si le découpage échoue.
        """
        if not text or not text.strip():
            raise ChunkingError("Impossible de découper un texte vide")

        try:
            segments: list[Any] = self._splitter.create_documents([text])
        except Exception as exc:
            raise ChunkingError("Echec du SemanticChunker", details={"cause": str(exc)}) from exc

        return [segment.page_content for segment in segments if segment.page_content.strip()]
