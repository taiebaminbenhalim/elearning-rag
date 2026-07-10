"""Package des exceptions métier du pipeline RAG.

Réexporte toutes les exceptions définies dans ``pipeline_exceptions`` afin
de permettre des imports concis dans le reste du projet, par exemple :

    from exceptions import OCRError, PDFLoadError
"""

from exceptions.pipeline_exceptions import (
    ChapterDetectionError,
    ChunkingError,
    CleaningError,
    DictionaryLoadError,
    EmbeddingError,
    LevelDetectionError,
    OCRError,
    PDFLoadError,
    PedagogicalDetectionError,
    PipelineError,
    StructureAnalysisError,
    StructureBuildError,
    SubjectDetectionError,
    ValidationError,
    VectorStoreError,
)

__all__ = [
    "PipelineError",
    "PDFLoadError",
    "OCRError",
    "CleaningError",
    "StructureAnalysisError",
    "ChunkingError",
    "EmbeddingError",
    "VectorStoreError",
    "ValidationError",
    "SubjectDetectionError",
    "LevelDetectionError",
    "ChapterDetectionError",
    "PedagogicalDetectionError",
    "StructureBuildError",
    "DictionaryLoadError",
]
