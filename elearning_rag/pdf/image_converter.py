"""Conversion des pages PDF en images (PyMuPDF + Pillow)."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from exceptions import PDFLoadError
from utils import build_page_image_filename, ensure_directory, get_logger

logger = get_logger(__name__)


class ImageConverter:
    """Convertit une page PDF en fichier image, prêt pour l'OCR.

    Attributes:
        output_dir: Répertoire dans lequel les images de pages sont écrites.
        zoom_factor: Facteur de zoom appliqué au rendu (améliore la qualité OCR).
        image_format: Format d'image de sortie (ex: ``"png"``).
    """

    def __init__(self, output_dir: Path, zoom_factor: float = 2.0, image_format: str = "png") -> None:
        """Initialise le convertisseur.

        Args:
            output_dir: Répertoire de sortie des images générées.
            zoom_factor: Facteur de zoom appliqué au rendu PDF → image.
            image_format: Format d'image de sortie.
        """
        self.output_dir = ensure_directory(output_dir)
        self.zoom_factor = zoom_factor
        self.image_format = image_format

    def convert_page(self, document: fitz.Document, page_number: int, document_id: str) -> str:
        """Convertit une page PDF en image et l'enregistre sur disque.

        Args:
            document: Document PyMuPDF ouvert.
            page_number: Numéro de page à convertir (commence à 1).
            document_id: Identifiant du document, utilisé pour nommer le fichier.

        Returns:
            Le chemin absolu du fichier image généré.

        Raises:
            PDFLoadError: Si la conversion de la page échoue.
        """
        try:
            page = document.load_page(page_number - 1)
            matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)
            pixmap = page.get_pixmap(matrix=matrix)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)

            filename = build_page_image_filename(document_id, page_number, self.image_format)
            output_path = self.output_dir / filename
            image.save(output_path)
        except Exception as exc:
            raise PDFLoadError(
                "Echec de la conversion de la page en image",
                details={"page_number": page_number, "cause": str(exc)},
            ) from exc

        logger.debug("Page %d convertie en image: %s", page_number, output_path)
        return str(output_path)
