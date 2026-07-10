"""PipelineV2 : chef d'orchestre du traitement complet, étendu en V2.

Ce module ne modifie jamais ``core/pipeline.py`` (V1), qui reste
disponible, testé et fonctionnel tel quel. ``PipelineV2`` est un nouveau
chef d'orchestre, superset de la V1, ajoutant les étapes de
compréhension de la structure pédagogique définies dans le cahier des
charges de la V2.
"""

from __future__ import annotations

import time
from pathlib import Path

from core.chunk_builder import ChunkBuilder
from core.cleaning_service import CleaningService
from core.embedding_service import EmbeddingService
from core.level_detector import LevelDetector
from core.ocr_service import OCRService
from core.pdf_loader import PDFLoader
from core.structure_builder import StructureBuilder
from core.subject_detector import SubjectDetector
from core.validator import Validator
from core.vector_store import VectorStoreService
from exceptions import PipelineError
from models import Document, Status
from utils import get_logger

logger = get_logger(__name__)


class PipelineV2:
    """Chef d'orchestre du pipeline complet V2, du PDF jusqu'à ChromaDB.

    Exécute les étapes dans l'ordre officiel du cahier des charges de la V2 :

        PDF → PDFLoader → OCRService → CleaningService → SubjectDetector
        → LevelDetector → StructureBuilder (chapitres, éléments
        pédagogiques, paragraphes) → ChunkBuilder → EmbeddingService
        → VectorStoreService

    Le Validator est invoqué après chaque étape. Comme en V1, ce service
    ne contient aucun traitement spécifique : il appelle uniquement les
    services, dans l'ordre, sur le même objet Document.

    Attributes:
        pdf_loader: Service de chargement du PDF (réutilisé de la V1).
        ocr_service: Service d'extraction OCR (réutilisé de la V1).
        cleaning_service: Service de nettoyage du texte (réutilisé de la V1).
        subject_detector: Service de détection des matières (V2).
        level_detector: Service de détection du niveau scolaire (V2).
        structure_builder: Orchestrateur de la structure logique (V2).
        chunk_builder: Service de construction des chunks (réutilisé de la V1).
        embedding_service: Service de génération des embeddings (réutilisé de la V1).
        vector_store_service: Service d'indexation vectorielle (réutilisé de la V1).
        validator: Service de validation de cohérence (étendu en V2).
    """

    def __init__(
        self,
        pdf_loader: PDFLoader,
        ocr_service: OCRService,
        cleaning_service: CleaningService,
        subject_detector: SubjectDetector,
        level_detector: LevelDetector,
        structure_builder: StructureBuilder,
        chunk_builder: ChunkBuilder,
        embedding_service: EmbeddingService,
        vector_store_service: VectorStoreService,
        validator: Validator,
    ) -> None:
        """Initialise le PipelineV2 avec tous ses services, injectés.

        Args:
            pdf_loader: Service de chargement du PDF.
            ocr_service: Service d'extraction OCR.
            cleaning_service: Service de nettoyage du texte.
            subject_detector: Service de détection des matières.
            level_detector: Service de détection du niveau scolaire.
            structure_builder: Orchestrateur de la structure logique.
            chunk_builder: Service de construction des chunks sémantiques.
            embedding_service: Service de génération des embeddings.
            vector_store_service: Service d'indexation dans la base vectorielle.
            validator: Service de validation de cohérence.
        """
        self._pdf_loader = pdf_loader
        self._ocr_service = ocr_service
        self._cleaning_service = cleaning_service
        self._subject_detector = subject_detector
        self._level_detector = level_detector
        self._structure_builder = structure_builder
        self._chunk_builder = chunk_builder
        self._embedding_service = embedding_service
        self._vector_store_service = vector_store_service
        self._validator = validator

    def run(self, pdf_path: Path) -> Document:
        """Exécute le pipeline V2 complet sur un fichier PDF.

        Args:
            pdf_path: Chemin du fichier PDF scanné à traiter.

        Returns:
            Le :class:`~models.document.Document` complètement indexé,
            enrichi des matières, du contexte académique et des éléments
            pédagogiques détectés.

        Raises:
            PipelineError: Si une étape du pipeline échoue. L'exception
                d'origine (plus spécifique) est propagée telle quelle.
        """
        started_at = time.monotonic()
        logger.info("Démarrage du pipeline V2 pour: %s", pdf_path)

        try:
            document = self._pdf_loader.load(pdf_path)
            self._validator.validate_loaded(document)

            document = self._ocr_service.process(document)
            self._validator.validate_ocr(document)

            document = self._cleaning_service.process(document)
            self._validator.validate_cleaning(document)

            document = self._subject_detector.detect(document)
            self._validator.validate_subjects(document)

            document = self._level_detector.detect(document)
            self._validator.validate_academic_context(document)

            document = self._structure_builder.build(document)
            self._validator.validate_structure_v2(document)

            document = self._chunk_builder.build(document)
            self._validator.validate_chunks(document)

            document = self._embedding_service.generate(document)
            self._validator.validate_embeddings(document)

            document = self._vector_store_service.index(document)

        except PipelineError as exc:
            logger.error("Echec du pipeline V2: %s", exc)
            raise
        finally:
            duration = time.monotonic() - started_at

        document.pipeline_info.duration_seconds = duration
        document.pipeline_info.current_step = "completed"
        document.status = Status.INDEXED

        logger.info(
            "Pipeline V2 terminé en %.2fs pour le document %s "
            "(%d matière(s), %d chapitre(s), %d élément(s) pédagogique(s), "
            "%d paragraphe(s), %d chunks, %d embeddings)",
            duration,
            document.document_id,
            len(document.subjects),
            len(document.chapters),
            len(document.pedagogical_elements),
            len(document.paragraphs),
            len(document.chunks),
            len(document.embeddings),
        )
        return document
