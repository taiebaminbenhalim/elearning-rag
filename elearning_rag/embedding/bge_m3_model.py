"""Implémentation du modèle d'embedding BAAI/bge-m3 (SentenceTransformers)."""

from __future__ import annotations

from sentence_transformers import SentenceTransformer

from core.interfaces import IEmbeddingModel
from exceptions import EmbeddingError
from utils import get_logger

logger = get_logger(__name__)


class BgeM3Model(IEmbeddingModel):
    """Modèle d'embedding V1, chargé une seule fois en mémoire.

    Implémente :class:`IEmbeddingModel` avec ``BAAI/bge-m3`` via
    SentenceTransformers, conformément au cahier des charges. Le modèle
    est chargé au moment de la construction de l'instance, puis réutilisé
    pour tous les appels (partagé dans tout le pipeline via injection de
    dépendances, jamais rechargé).

    Attributes:
        device: Device d'inférence (``"cpu"`` ou ``"cuda"``).
        normalize: Indique si les vecteurs produits sont normalisés (L2).
        batch_size: Taille de batch utilisée lors de l'encodage.
    """

    _MODEL_NAME = "BAAI/bge-m3"

    def __init__(self, device: str = "cpu", normalize: bool = True, batch_size: int = 16) -> None:
        """Charge le modèle BGE-M3.

        Args:
            device: Device d'inférence (``"cpu"`` ou ``"cuda"``).
            normalize: Normalise les vecteurs produits (norme L2 = 1).
            batch_size: Taille de batch utilisée lors de l'encodage.

        Raises:
            EmbeddingError: Si le chargement du modèle échoue.
        """
        self.device = device
        self.normalize = normalize
        self.batch_size = batch_size

        try:
            self._model = SentenceTransformer(self._MODEL_NAME, device=device)
        except Exception as exc:
            raise EmbeddingError(
                "Echec du chargement du modèle d'embedding",
                details={"model_name": self._MODEL_NAME, "cause": str(exc)},
            ) from exc

        self._dimension = int(self._model.get_sentence_embedding_dimension())
        logger.info("Modèle d'embedding chargé: %s (dim=%d)", self._MODEL_NAME, self._dimension)

    @property
    def model_name(self) -> str:
        """Nom du modèle d'embedding."""
        return self._MODEL_NAME

    @property
    def dimension(self) -> int:
        """Dimension des vecteurs produits par le modèle."""
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Génère un vecteur d'embedding pour chaque texte fourni.

        Args:
            texts: Liste de textes à encoder.

        Returns:
            Liste de vecteurs (listes de flottants), même ordre que ``texts``.

        Raises:
            EmbeddingError: Si l'encodage échoue ou si ``texts`` est vide.
        """
        if not texts:
            raise EmbeddingError("Impossible de générer des embeddings pour une liste vide")

        try:
            vectors = self._model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=self.normalize,
                show_progress_bar=False,
            )
        except Exception as exc:
            raise EmbeddingError("Echec de la génération des embeddings", details={"cause": str(exc)}) from exc

        return [vector.tolist() for vector in vectors]
