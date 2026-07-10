"""Service StructureBuilder : orchestre la construction de la structure logique."""

from __future__ import annotations

from core.chapter_detector import ChapterDetector
from core.paragraph_detector import ParagraphDetector
from core.pedagogical_detector import PedagogicalDetector
from exceptions import PipelineError, StructureBuildError
from models import Document, Status
from utils import get_logger

logger = get_logger(__name__)


class StructureBuilder:
    """Orchestre la construction complète de la structure logique du document.

    Enchaîne, dans l'ordre du cahier des charges de la V2 :
        1. :class:`~core.chapter_detector.ChapterDetector` (chapitres, si présents) ;
        2. :class:`~core.pedagogical_detector.PedagogicalDetector` (éléments pédagogiques) ;
        3. :class:`~core.paragraph_detector.ParagraphDetector` (paragraphes, logique V1 inchangée).

    Ce service ne contient aucune logique de détection lui-même : il ne
    fait qu'orchestrer les trois détecteurs spécialisés, chacun injecté
    séparément (SRP + injection de dépendances), puis finalise le statut
    du document.

    Attributes:
        chapter_detector: Détecteur de chapitres.
        pedagogical_detector: Détecteur d'éléments pédagogiques.
        paragraph_detector: Détecteur de paragraphes.
    """

    def __init__(
        self,
        chapter_detector: ChapterDetector,
        pedagogical_detector: PedagogicalDetector,
        paragraph_detector: ParagraphDetector,
    ) -> None:
        """Initialise l'orchestrateur de structure logique.

        Args:
            chapter_detector: Détecteur de chapitres.
            pedagogical_detector: Détecteur d'éléments pédagogiques.
            paragraph_detector: Détecteur de paragraphes.
        """
        self._chapter_detector = chapter_detector
        self._pedagogical_detector = pedagogical_detector
        self._paragraph_detector = paragraph_detector

    def build(self, document: Document) -> Document:
        """Construit la structure logique complète du document.

        Args:
            document: Document dont les matières et le niveau scolaire ont
                déjà été détectés.

        Returns:
            Le même Document, avec ``chapters``, ``pedagogical_elements``
            et ``paragraphs`` remplis.

        Raises:
            StructureBuildError: Si l'un des détecteurs orchestrés échoue.
                L'exception d'origine est indiquée dans ``details``.
        """
        try:
            document = self._chapter_detector.detect(document)
            document = self._pedagogical_detector.detect(document)
            document = self._paragraph_detector.detect(document)
        except PipelineError as exc:
            raise StructureBuildError(
                "Echec de la construction de la structure logique",
                details={"document_id": document.document_id, "cause": str(exc)},
            ) from exc

        document.pipeline_info.current_step = "structure_building"
        document.pipeline_info.status = Status.STRUCTURED
        document.status = Status.STRUCTURED

        logger.info(
            "Structure logique construite (document %s): %d chapitre(s), "
            "%d élément(s) pédagogique(s), %d paragraphe(s)",
            document.document_id,
            len(document.chapters),
            len(document.pedagogical_elements),
            len(document.paragraphs),
        )
        return document
