"""Service OCRService : extraction du texte brut de chaque page."""

from __future__ import annotations

from core.interfaces import IOcrEngine
from exceptions import OCRError
from models import Document, OCRData, Status
from utils import get_logger

logger = get_logger(__name__)


class OCRService:
    """Parcourt les pages d'un Document et remplit leur OCRData.

    Le moteur OCR est injecté via l'interface :class:`IOcrEngine`, ce qui
    permet de remplacer Tesseract par un autre moteur (ex: PaddleOCR) sans
    modifier ce service.

    Attributes:
        ocr_engine: Moteur OCR utilisé pour l'extraction.
        language: Code langue utilisé pour l'OCR.
    """

    def __init__(self, ocr_engine: IOcrEngine, language: str) -> None:
        """Initialise le service OCR.

        Args:
            ocr_engine: Implémentation concrète d'un moteur OCR.
            language: Code langue à utiliser pour l'OCR.
        """
        self._ocr_engine = ocr_engine
        self._language = language

    def process(self, document: Document) -> Document:
        """Exécute l'OCR sur toutes les pages du document.

        Args:
            document: Document dont les pages possèdent déjà une image
                (produite par :class:`~core.pdf_loader.PDFLoader`).

        Returns:
            Le même Document, avec ``ocr_data`` renseigné sur chaque page.

        Raises:
            OCRError: Si une page n'a pas d'image associée, ou si
                l'extraction OCR échoue.
        """
        for page in document.pages:
            if not page.image_path:
                raise OCRError(
                    "Aucune image disponible pour la page",
                    details={"page_number": page.page_number},
                )

            raw_text, confidence = self._ocr_engine.extract_text(page.image_path, self._language)
            page.ocr_data = OCRData(
                raw_text=raw_text,
                mean_confidence=confidence,
                engine_name=self._ocr_engine.engine_name,
                language=self._language,
            )

        document.pipeline_info.ocr_engine = self._ocr_engine.engine_name
        document.pipeline_info.current_step = "ocr"
        document.pipeline_info.status = Status.OCR_DONE
        document.status = Status.OCR_DONE

        logger.info("OCR terminé pour %d pages (document %s)", len(document.pages), document.document_id)
        return document
