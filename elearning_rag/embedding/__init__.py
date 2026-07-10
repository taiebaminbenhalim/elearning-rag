"""Package embedding : modèles d'embeddings concrets implémentant IEmbeddingModel.

La Version 1 utilise un unique modèle, BAAI/bge-m3, chargé une seule fois
en mémoire et partagé dans tout le pipeline.
"""

from embedding.bge_m3_model import BgeM3Model

__all__ = ["BgeM3Model"]
