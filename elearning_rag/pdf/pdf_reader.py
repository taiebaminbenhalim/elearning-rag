"""Ouverture et lecture bas niveau des fichiers PDF (PyMuPDF)."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from exceptions import PDFLoadError
from utils import ensure_file_exists, get_logger

logger = get_logger(__name__)


class PDFReader:
    """Encapsule l'ouverture et la lecture bas niveau d'un fichier PDF.

    Ce composant ne réalise jamais d'OCR ni de nettoyage : il se limite à
    l'ouverture du document et à l'accès à ses pages, conformément au
    cahier des charges (dossier `pdf/`).
    """

    def open(self, pdf_path: Path) -> fitz.Document:
        """Ouvre un fichier PDF et retourne le document PyMuPDF correspondant.

        Args:
            pdf_path: Chemin du fichier PDF à ouvrir.

        Returns:
            Le document PyMuPDF ouvert.

        Raises:
            PDFLoadError: Si le fichier n'existe pas ou ne peut pas être
                ouvert en tant que PDF valide.
        """
        ensure_file_exists(pdf_path)
        try:
            document = fitz.open(str(pdf_path))
        except Exception as exc:  # PyMuPDF lève des erreurs génériques
            raise PDFLoadError(
                "Impossible d'ouvrir le fichier PDF",
                details={"path": str(pdf_path), "cause": str(exc)},
            ) from exc

        if document.page_count == 0:
            document.close()
            raise PDFLoadError("Le PDF ne contient aucune page", details={"path": str(pdf_path)})

        logger.info("PDF ouvert: %s (%d pages)", pdf_path.name, document.page_count)
        return document

    def get_page_count(self, document: fitz.Document) -> int:
        """Retourne le nombre de pages d'un document PyMuPDF ouvert.

        Args:
            document: Document PyMuPDF déjà ouvert.

        Returns:
            Nombre total de pages.
        """
        return document.page_count
