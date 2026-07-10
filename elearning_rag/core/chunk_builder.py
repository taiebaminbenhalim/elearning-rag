"""Service ChunkBuilder : construction des chunks sémantiques."""

from __future__ import annotations

from core.interfaces import IChunker
from exceptions import ChunkingError
from models import Chunk, ChunkMetadata, Document, Status
from utils import count_chars, count_words, get_logger

logger = get_logger(__name__)


class ChunkBuilder:
    """Parcourt les paragraphes du document et construit les chunks sémantiques.

    Utilise exclusivement la stratégie injectée via :class:`IChunker`
    (SemanticChunker en V1). Ce service fonctionne indépendamment du
    modèle d'embedding : il ne connaît que l'interface de chunking, jamais
    directement BGE-M3 ou SentenceTransformers.

    Attributes:
        chunker: Stratégie de chunking utilisée.
        language: Code langue renseigné dans les métadonnées des chunks.
    """

    def __init__(self, chunker: IChunker, language: str) -> None:
        """Initialise le ChunkBuilder.

        Args:
            chunker: Implémentation concrète d'une stratégie de chunking.
            language: Code langue à renseigner dans ``ChunkMetadata``.
        """
        self._chunker = chunker
        self._language = language

    def build(self, document: Document) -> Document:
        """Construit les chunks sémantiques à partir des paragraphes du document.

        Args:
            document: Document dont ``paragraphs`` a déjà été rempli par le
                :class:`~core.structure_analyzer.StructureAnalyzer`.

        Returns:
            Le même Document, avec ``chunks`` rempli.

        Raises:
            ChunkingError: Si aucun paragraphe n'est disponible.
        """
        if not document.paragraphs:
            raise ChunkingError(
                "Aucun paragraphe disponible pour le chunking",
                details={"document_id": document.document_id},
            )

        chunks: list[Chunk] = []
        chunk_index = 0

        for paragraph in document.paragraphs:
            segments = self._chunker.split(paragraph.text)
            for segment in segments:
                chunk = Chunk(
                    text=segment,
                    paragraph_ids=[paragraph.paragraph_id],
                    page_numbers=list(paragraph.page_numbers),
                    metadata=ChunkMetadata(
                        chunk_index=chunk_index,
                        creation_method=self._chunker.strategy_name,
                        word_count=count_words(segment),
                        char_count=count_chars(segment),
                        language=self._language,
                    ),
                    context={"chapter_id": paragraph.chapter_id, "page_numbers": paragraph.page_numbers},
                )
                chunks.append(chunk)
                chunk_index += 1

        document.chunks = chunks
        document.pipeline_info.chunking_strategy = self._chunker.strategy_name
        document.pipeline_info.current_step = "chunking"
        document.pipeline_info.status = Status.CHUNKED
        document.status = Status.CHUNKED

        logger.info("%d chunks construits (document %s)", len(chunks), document.document_id)
        return document
