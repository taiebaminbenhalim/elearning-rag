"""Package ocr : moteurs OCR concrets implémentant IOcrEngine.

La Version 1 utilise exclusivement Tesseract. L'architecture permet
d'ajouter PaddleOCR dans une future version sans modifier `core/`.
"""

from ocr.tesseract_engine import TesseractEngine

__all__ = ["TesseractEngine"]
