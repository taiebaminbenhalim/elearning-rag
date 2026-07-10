"""Service CleaningService : nettoyage du texte OCR de chaque page."""

from __future__ import annotations

from core.interfaces import ICleaningStrategy
from exceptions import CleaningError
from models import CleaningData, Document, Status
from utils import get_logger

logger = get_logger(__name__)


class CleaningService:
    """Nettoie le texte OCR de chaque page du document.

    Le texte OCR original n'est jamais modifié : il reste disponible dans
    ``page.ocr_data``. Le résultat du nettoyage est stocké séparément dans
    ``page.cleaning_data``.

    La stratégie de nettoyage est injectée via :class:`ICleaningStrategy`,
    ce qui permet de la remplacer sans modifier ce service.

    Attributes:
        cleaning_strategy: Stratégie de nettoyage utilisée.
    """

    def __init__(self, cleaning_strategy: ICleaningStrategy) -> None:
        """Initialise le service de nettoyage.

        Args:
            cleaning_strategy: Implémentation concrète d'une stratégie de nettoyage.
        """
        self._cleaning_strategy = cleaning_strategy

    def process(self, document: Document) -> Document:
        """Nettoie le texte OCR de toutes les pages du document.

        Args:
            document: Document dont les pages possèdent déjà un ``ocr_data``
                (produit par :class:`~core.ocr_service.OCRService`).

        Returns:
            Le même Document, avec ``cleaning_data`` renseigné sur chaque page.

        Raises:
            CleaningError: Si une page n'a pas de données OCR disponibles.
        """
        for page in document.pages:
            if page.ocr_data is None:
                raise CleaningError(
                    "Aucune donnée OCR disponible pour le nettoyage",
                    details={"page_number": page.page_number},
                )

            cleaned_text = self._cleaning_strategy.clean(page.ocr_data.raw_text)
            page.cleaning_data = CleaningData(
                cleaned_text=cleaned_text,
                strategy_name=self._cleaning_strategy.strategy_name,
            )

        document.pipeline_info.current_step = "cleaning"
        document.pipeline_info.status = Status.CLEANED
        document.status = Status.CLEANED

        logger.info("Nettoyage terminé pour %d pages (document %s)", len(document.pages), document.document_id)
        return document
