"""Package pdf : traitements bas niveau liés au format PDF.

Ne réalise jamais d'OCR ni de nettoyage. Se limite à l'ouverture des
documents et à la conversion des pages en images.
"""

from pdf.image_converter import ImageConverter
from pdf.pdf_reader import PDFReader

__all__ = ["PDFReader", "ImageConverter"]
