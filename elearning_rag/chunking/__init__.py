"""Package chunking : stratégies de découpage sémantique.

La Version 1 utilise exclusivement SemanticChunker. L'architecture permet
d'ajouter Recursive Chunking, LLM Chunking ou Hybrid Chunking dans une
future version en implémentant `IChunker`, sans modifier `core/chunk_builder.py`.
"""

from chunking.semantic_chunker_strategy import SemanticChunkerStrategy

__all__ = ["SemanticChunkerStrategy"]
