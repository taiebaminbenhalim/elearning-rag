"""Pipeline : chef d'orchestre du traitement complet d'un document."""

from __future__ import annotations

import time
from pathlib import Path

from core.chunk_builder import ChunkBuilder
from core.cleaning_service import CleaningService
from core.embedding_service import EmbeddingService
from core.ocr_service import OCRService
from core.pdf_loader import PDFLoader
from core.structure_analyzer import StructureAnalyzer
from core.validator import Validator
from core.vector_store import VectorStoreService
from exceptions import PipelineError
from models import Document, Status
from utils import get_logger

logger = get_logger(__name__)


class Pipeline:
    """Chef d'orchestre du pipeline complet, du PDF jusqu'à ChromaDB.

    C'est le seul composant qui connaît l'ensemble des services. Il exécute
    les étapes dans l'ordre officiel défini par le cahier des charges :

        PDF → PDFLoader → OCRService → CleaningService → StructureAnalyzer
        → ChunkBuilder → EmbeddingService → VectorStoreService

    Le Validator est invoqué après chaque étape afin de détecter au plus
    tôt toute incohérence. Le Pipeline ne contient aucun traitement
    spécifique : il ne fait qu'appeler les différents services, dans
    l'ordre, sur le même objet Document qui circule pendant tout le
    traitement.

    Attributes:
        pdf_loader: Service de chargement du PDF.
        ocr_service: Service d'extraction OCR.
        cleaning_service: Service de nettoyage du texte.
        structure_analyzer: Service d'analyse de structure logique.
        chunk_builder: Service de construction des chunks sémantiques.
        embedding_service: Service de génération des embeddings.
        vector_store_service: Service d'indexation dans la base vectorielle.
        validator: Service de validation de cohérence.
    """

    def __init__(
        self,
        pdf_loader: PDFLoader,
        ocr_service: OCRService,
        cleaning_service: CleaningService,
        structure_analyzer: StructureAnalyzer,
        chunk_builder: ChunkBuilder,
        embedding_service: EmbeddingService,
        vector_store_service: VectorStoreService,
        validator: Validator,
    ) -> None:
        """Initialise le Pipeline avec tous ses services, injectés.

        Args:
            pdf_loader: Service de chargement du PDF.
            ocr_service: Service d'extraction OCR.
            cleaning_service: Service de nettoyage du texte.
            structure_analyzer: Service d'analyse de structure logique.
            chunk_builder: Service de construction des chunks sémantiques.
            embedding_service: Service de génération des embeddings.
            vector_store_service: Service d'indexation dans la base vectorielle.
            validator: Service de validation de cohérence.
        """
        self._pdf_loader = pdf_loader
        self._ocr_service = ocr_service
        self._cleaning_service = cleaning_service
        self._structure_analyzer = structure_analyzer
        self._chunk_builder = chunk_builder
        self._embedding_service = embedding_service
        self._vector_store_service = vector_store_service
        self._validator = validator

    def run(self, pdf_path: Path) -> Document:
        """Exécute le pipeline complet sur un fichier PDF.

        Args:
            pdf_path: Chemin du fichier PDF scanné à traiter.

        Returns:
            Le :class:`~models.document.Document` complètement indexé.

        Raises:
            PipelineError: Si une étape du pipeline échoue. L'exception
                d'origine (plus spécifique) est propagée telle quelle.
        """
        started_at = time.monotonic()
        logger.info("Démarrage du pipeline pour: %s", pdf_path)

        try:
            document = self._pdf_loader.load(pdf_path)
            self._validator.validate_loaded(document)

            document = self._ocr_service.process(document)
            self._validator.validate_ocr(document)

            document = self._cleaning_service.process(document)
            self._validator.validate_cleaning(document)

            document = self._structure_analyzer.analyze(document)
            self._validator.validate_structure(document)

            document = self._chunk_builder.build(document)
            self._validator.validate_chunks(document)

            document = self._embedding_service.generate(document)
            self._validator.validate_embeddings(document)

            document = self._vector_store_service.index(document)

        except PipelineError as exc:
            logger.error("Echec du pipeline: %s", exc)
            raise
        finally:
            duration = time.monotonic() - started_at

        document.pipeline_info.duration_seconds = duration
        document.pipeline_info.current_step = "completed"
        document.status = Status.INDEXED

        logger.info(
            "Pipeline terminé en %.2fs pour le document %s (%d chunks, %d embeddings)",
            duration,
            document.document_id,
            len(document.chunks),
            len(document.embeddings),
        )
        return document
