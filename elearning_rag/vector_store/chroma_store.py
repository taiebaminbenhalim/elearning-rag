"""Implémentation du vector store basée sur ChromaDB."""

from __future__ import annotations

from pathlib import Path

import chromadb

from core.interfaces import IVectorStore
from exceptions import VectorStoreError
from models import Chunk, Embedding
from utils import ensure_directory, get_logger

logger = get_logger(__name__)


class ChromaStore(IVectorStore):
    """Base vectorielle V1, basée exclusivement sur ChromaDB.

    Attributes:
        persist_directory: Répertoire de persistance de la base ChromaDB.
    """

    def __init__(self, persist_directory: Path) -> None:
        """Initialise le client ChromaDB persistant.

        Args:
            persist_directory: Répertoire dans lequel ChromaDB persiste ses données.

        Raises:
            VectorStoreError: Si le client ChromaDB ne peut pas être initialisé.
        """
        self.persist_directory = ensure_directory(persist_directory)
        try:
            self._client = chromadb.PersistentClient(path=str(self.persist_directory))
        except Exception as exc:
            raise VectorStoreError(
                "Echec de l'initialisation du client ChromaDB",
                details={"persist_directory": str(self.persist_directory), "cause": str(exc)},
            ) from exc

    def create_collection(self, collection_name: str) -> None:
        """Crée (ou récupère) une collection ChromaDB.

        Args:
            collection_name: Nom de la collection à créer/récupérer.

        Raises:
            VectorStoreError: Si la création de la collection échoue.
        """
        try:
            self._client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Embeddings de la plateforme RAG e-learning"},
            )
        except Exception as exc:
            raise VectorStoreError(
                "Echec de la création de la collection ChromaDB",
                details={"collection_name": collection_name, "cause": str(exc)},
            ) from exc

    def add_embeddings(
        self,
        collection_name: str,
        chunks: list[Chunk],
        embeddings: list[Embedding],
    ) -> None:
        """Enregistre des chunks et leurs embeddings dans la collection.

        Args:
            collection_name: Nom de la collection cible.
            chunks: Chunks à indexer.
            embeddings: Embeddings correspondants, un par chunk, même ordre.

        Raises:
            VectorStoreError: Si le nombre de chunks et d'embeddings diffère,
                ou si l'écriture dans ChromaDB échoue.
        """
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                "Le nombre de chunks doit correspondre au nombre d'embeddings",
                details={"chunks": len(chunks), "embeddings": len(embeddings)},
            )
        if not chunks:
            return

        collection = self._client.get_or_create_collection(name=collection_name)

        ids = [embedding.embedding_id for embedding in embeddings]
        vectors = [embedding.vector for embedding in embeddings]
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                "chunk_id": chunk.chunk_id,
                "chunk_index": chunk.metadata.chunk_index,
                "word_count": chunk.metadata.word_count,
                "char_count": chunk.metadata.char_count,
                "page_numbers": ",".join(str(page) for page in chunk.page_numbers),
                "paragraph_ids": ",".join(chunk.paragraph_ids),
            }
            for chunk in chunks
        ]

        try:
            collection.add(
                ids=ids,
                embeddings=vectors,
                documents=documents,
                metadatas=metadatas,
            )
        except Exception as exc:
            raise VectorStoreError(
                "Echec de l'indexation des embeddings dans ChromaDB",
                details={"collection_name": collection_name, "cause": str(exc)},
            ) from exc

        logger.info("%d embeddings indexés dans la collection '%s'", len(ids), collection_name)

    def count(self, collection_name: str) -> int:
        """Retourne le nombre d'éléments indexés dans une collection.

        Args:
            collection_name: Nom de la collection à interroger.

        Returns:
            Nombre d'éléments présents dans la collection (0 si absente).
        """
        try:
            collection = self._client.get_or_create_collection(name=collection_name)
            return collection.count()
        except Exception as exc:
            raise VectorStoreError(
                "Echec du comptage des éléments de la collection",
                details={"collection_name": collection_name, "cause": str(exc)},
            ) from exc
