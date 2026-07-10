"""Service VectorStoreService : indexation des embeddings dans la base vectorielle."""

from __future__ import annotations

from core.interfaces import IVectorStore
from exceptions import VectorStoreError
from models import Document, Status
from utils import get_logger

logger = get_logger(__name__)


class VectorStoreService:
    """Enregistre les chunks et leurs embeddings dans la base vectorielle.

    La base vectorielle est injectée via :class:`IVectorStore` (ChromaDB en
    V1). Ce service ne connaît jamais directement ChromaDB.

    Attributes:
        vector_store: Implémentation concrète de la base vectorielle.
        collection_name: Nom de la collection cible.
    """

    def __init__(self, vector_store: IVectorStore, collection_name: str) -> None:
        """Initialise le service de stockage vectoriel.

        Args:
            vector_store: Implémentation concrète d'une base vectorielle.
            collection_name: Nom de la collection cible.
        """
        self._vector_store = vector_store
        self._collection_name = collection_name

    def index(self, document: Document) -> Document:
        """Indexe les chunks et embeddings du document dans la base vectorielle.

        Args:
            document: Document dont ``chunks`` et ``embeddings`` ont déjà
                été remplis par les services précédents.

        Returns:
            Le même Document, avec le statut final ``INDEXED``.

        Raises:
            VectorStoreError: Si les embeddings sont absents ou si
                l'indexation échoue.
        """
        if not document.embeddings:
            raise VectorStoreError(
                "Aucun embedding disponible pour l'indexation",
                details={"document_id": document.document_id},
            )

        self._vector_store.create_collection(self._collection_name)
        self._vector_store.add_embeddings(self._collection_name, document.chunks, document.embeddings)

        document.pipeline_info.current_step = "vector_store_indexing"
        document.pipeline_info.status = Status.INDEXED
        document.status = Status.INDEXED

        total = self._vector_store.count(self._collection_name)
        logger.info(
            "Document %s indexé dans la collection '%s' (total collection: %d)",
            document.document_id,
            self._collection_name,
            total,
        )
        return document
