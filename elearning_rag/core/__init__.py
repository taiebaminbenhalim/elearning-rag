"""Package core : logique métier du pipeline (services d'orchestration).

Contrairement au dossier `models`, ce package ne stocke aucune donnée. Son
rôle est de transformer progressivement un objet Document depuis un
simple fichier PDF jusqu'à un document entièrement indexé dans ChromaDB.

Les services ne dépendent jamais d'une implémentation technique concrète :
ils dépendent uniquement des interfaces définies dans `core.interfaces`,
injectées au moment de leur construction (voir `main.py`).

Ce package contient à la fois :
    * les services V1 (`Pipeline`, `StructureAnalyzer`...), inchangés ;
    * les nouveaux services V2 (`PipelineV2`, `SubjectDetector`,
      `LevelDetector`, `ChapterDetector`, `PedagogicalDetector`,
      `ParagraphDetector`, `StructureBuilder`), additifs.
"""

from core.chapter_detector import ChapterDetector
from core.chunk_builder import ChunkBuilder
from core.cleaning_service import CleaningService
from core.embedding_service import EmbeddingService
from core.level_detector import LevelDetector
from core.ocr_service import OCRService
from core.paragraph_detector import ParagraphDetector
from core.pdf_loader import PDFLoader
from core.pedagogical_detector import PedagogicalDetector
from core.pipeline import Pipeline
from core.pipeline_v2 import PipelineV2
from core.structure_analyzer import StructureAnalyzer
from core.structure_builder import StructureBuilder
from core.subject_detector import SubjectDetector
from core.validator import Validator
from core.vector_store import VectorStoreService

__all__ = [
    # V1 (inchangé)
    "PDFLoader",
    "OCRService",
    "CleaningService",
    "StructureAnalyzer",
    "ChunkBuilder",
    "EmbeddingService",
    "VectorStoreService",
    "Validator",
    "Pipeline",
    # V2 (additif)
    "SubjectDetector",
    "LevelDetector",
    "ChapterDetector",
    "PedagogicalDetector",
    "ParagraphDetector",
    "StructureBuilder",
    "PipelineV2",
]
