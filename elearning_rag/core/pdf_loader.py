"""Service PDFLoader : construit le Document initial à partir d'un PDF."""

from __future__ import annotations

from pathlib import Path

from exceptions import PDFLoadError
from models import Document, Metadata, Page, PhysicalStructure, PipelineInfo, Status
from pdf import ImageConverter, PDFReader
from utils import get_logger

logger = get_logger(__name__)


class PDFLoader:
    """Charge un PDF et construit le Document initial du pipeline.

    Responsabilités : ouvrir le fichier PDF, vérifier son existence,
    convertir chaque page en image, créer les objets Page, créer le
    Document initial, remplir Metadata et construire PhysicalStructure.
    Ne réalise jamais d'OCR.

    Attributes:
        pdf_reader: Composant d'ouverture/lecture bas niveau du PDF.
        image_converter: Composant de conversion page PDF → image.
        ocr_engine_name: Nom du moteur OCR utilisé (renseigné dans PipelineInfo).
        embedding_model_name: Nom du modèle d'embedding (renseigné dans PipelineInfo).
        chunking_strategy_name: Nom de la stratégie de chunking (renseigné dans PipelineInfo).
        pipeline_version: Version du pipeline (renseignée dans PipelineInfo).
        default_language: Langue par défaut du document.
    """

    def __init__(
        self,
        pdf_reader: PDFReader,
        image_converter: ImageConverter,
        ocr_engine_name: str,
        embedding_model_name: str,
        chunking_strategy_name: str,
        pipeline_version: str,
        default_language: str = "fra",
    ) -> None:
        """Initialise le PDFLoader avec ses dépendances injectées.

        Args:
            pdf_reader: Composant d'ouverture/lecture bas niveau du PDF.
            image_converter: Composant de conversion page PDF → image.
            ocr_engine_name: Nom du moteur OCR utilisé par le pipeline.
            embedding_model_name: Nom du modèle d'embedding utilisé par le pipeline.
            chunking_strategy_name: Nom de la stratégie de chunking utilisée.
            pipeline_version: Version du pipeline.
            default_language: Langue par défaut à associer au document.
        """
        self._pdf_reader = pdf_reader
        self._image_converter = image_converter
        self._ocr_engine_name = ocr_engine_name
        self._embedding_model_name = embedding_model_name
        self._chunking_strategy_name = chunking_strategy_name
        self._pipeline_version = pipeline_version
        self._default_language = default_language

    def load(self, pdf_path: Path) -> Document:
        """Charge un PDF et retourne le Document initial du pipeline.

        Args:
            pdf_path: Chemin du fichier PDF à charger.

        Returns:
            Un :class:`~models.document.Document` avec ses pages et images
            générées, prêt pour l'étape OCR.

        Raises:
            PDFLoadError: Si le chargement ou la conversion échoue.
        """
        pdf_document = self._pdf_reader.open(pdf_path)
        total_pages = self._pdf_reader.get_page_count(pdf_document)

        metadata = Metadata(
            filename=pdf_path.name,
            file_size_bytes=pdf_path.stat().st_size,
            total_pages=total_pages,
            language=self._default_language,
        )
        pipeline_info = PipelineInfo(
            ocr_engine=self._ocr_engine_name,
            embedding_model=self._embedding_model_name,
            chunking_strategy=self._chunking_strategy_name,
            pipeline_version=self._pipeline_version,
            status=Status.CREATED,
            current_step="pdf_loading",
        )

        document = Document(metadata=metadata, pipeline_info=pipeline_info)

        try:
            for page_number in range(1, total_pages + 1):
                image_path = self._image_converter.convert_page(
                    pdf_document, page_number, document.document_id
                )
                document.pages.append(Page(page_number=page_number, image_path=image_path))
        finally:
            pdf_document.close()

        document.physical_structure = PhysicalStructure(
            page_ids=[page.page_id for page in document.pages],
            total_pages=total_pages,
        )
        document.pipeline_info.status = Status.LOADED
        document.status = Status.LOADED

        logger.info("Document chargé: %s (%d pages)", metadata.filename, total_pages)
        return document
