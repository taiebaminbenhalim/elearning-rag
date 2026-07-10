"""Package vector_store : bases vectorielles concrètes implémentant IVectorStore.

La Version 1 utilise exclusivement ChromaDB. Aucune autre base vectorielle
n'est concernée par cette version.
"""

from vector_store.chroma_store import ChromaStore

__all__ = ["ChromaStore"]
