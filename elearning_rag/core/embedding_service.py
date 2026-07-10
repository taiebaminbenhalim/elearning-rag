"""Service EmbeddingService : génération des embeddings pour chaque chunk."""

from __future__ import annotations

from core.interfaces import IEmbeddingModel
from exceptions import EmbeddingError
from models import Document, Embedding, Status
from utils import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Génère un embedding pour chaque chunk du document.

    Le modèle d'embedding est injecté via :class:`IEmbeddingModel` et
    chargé une seule fois en amont (voir ``main.py``), afin d'éviter les
    rechargements inutiles pendant le pipeline.

    Attributes:
        embedding_model: Modèle d'embedding utilisé.
    """

    def __init__(self, embedding_model: IEmbeddingModel) -> None:
        """Initialise le service d'embedding.

        Args:
            embedding_model: Implémentation concrète d'un modèle d'embedding,
                déjà chargée en mémoire.
        """
        self._embedding_model = embedding_model

    def generate(self, document: Document) -> Document:
        """Génère les embeddings de tous les chunks du document.

        Args:
            document: Document dont ``chunks`` a déjà été rempli par le
                :class:`~core.chunk_builder.ChunkBuilder`.

        Returns:
            Le même Document, avec ``embeddings`` rempli.

        Raises:
            EmbeddingError: Si aucun chunk n'est disponible.
        """
        if not document.chunks:
            raise EmbeddingError(
                "Aucun chunk disponible pour la génération d'embeddings",
                details={"document_id": document.document_id},
            )

        texts = [chunk.text for chunk in document.chunks]
        vectors = self._embedding_model.embed(texts)

        embeddings: list[Embedding] = []
        for chunk, vector in zip(document.chunks, vectors):
            embeddings.append(
                Embedding(
                    chunk_id=chunk.chunk_id,
                    vector=vector,
                    model_name=self._embedding_model.model_name,
                    dimension=self._embedding_model.dimension,
                    normalized=True,
                )
            )

        document.embeddings = embeddings
        document.pipeline_info.embedding_model = self._embedding_model.model_name
        document.pipeline_info.current_step = "embedding"
        document.pipeline_info.status = Status.EMBEDDED
        document.status = Status.EMBEDDED

        logger.info("%d embeddings générés (document %s)", len(embeddings), document.document_id)
        return document
