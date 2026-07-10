"""Implémentation du moteur OCR Tesseract."""

from __future__ import annotations

import cv2
import numpy as np
import pytesseract
from PIL import Image

from core.interfaces import IOcrEngine
from exceptions import OCRError
from utils import get_logger

logger = get_logger(__name__)


class TesseractEngine(IOcrEngine):
    """Moteur OCR basé sur Tesseract, implémentation V1 de :class:`IOcrEngine`.

    Applique un prétraitement OpenCV optionnel (niveaux de gris +
    binarisation) avant d'appeler Tesseract, afin d'améliorer la qualité
    d'extraction sur des scans de livres scolaires.

    L'architecture permet d'ajouter un ``PaddleOcrEngine`` ultérieurement
    en implémentant la même interface :class:`IOcrEngine`, sans modifier
    ``core/ocr_service.py``.
    """

    def __init__(self, apply_preprocessing: bool = True, tesseract_cmd: str | None = None) -> None:
        """Initialise le moteur Tesseract.

        Args:
            apply_preprocessing: Active le prétraitement d'image (OpenCV)
                avant l'appel à Tesseract.
            tesseract_cmd: Chemin explicite vers l'exécutable Tesseract.
                Nécessaire sous Windows lorsque Tesseract n'est pas dans le
                PATH (ex: ``"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"``).
                Laisser à ``None`` sous Linux/macOS si `tesseract` est déjà
                accessible dans le PATH.
        """
        self._apply_preprocessing = apply_preprocessing
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    @property
    def engine_name(self) -> str:
        """Nom du moteur OCR."""
        return "tesseract"

    def extract_text(self, image_path: str, language: str) -> tuple[str, float]:
        """Extrait le texte d'une image de page via Tesseract.

        Args:
            image_path: Chemin de l'image à traiter.
            language: Code(s) langue Tesseract (ex: ``"fra"``).

        Returns:
            Un tuple ``(texte_brut, confiance_moyenne)``.

        Raises:
            OCRError: Si l'image ne peut pas être lue ou si Tesseract échoue.
        """
        try:
            image = self._prepare_image(image_path)
            text = pytesseract.image_to_string(image, lang=language)
            confidence = self._compute_mean_confidence(image, language)
        except OCRError:
            raise
        except Exception as exc:
            raise OCRError(
                "Echec de l'extraction OCR",
                details={"image_path": image_path, "language": language, "cause": str(exc)},
            ) from exc

        return text, confidence

    def _prepare_image(self, image_path: str) -> Image.Image:
        """Charge l'image et applique un prétraitement optionnel.

        Args:
            image_path: Chemin de l'image source.

        Returns:
            Une image PIL prête à être envoyée à Tesseract.

        Raises:
            OCRError: Si l'image ne peut pas être chargée.
        """
        raw_image = cv2.imread(image_path)
        if raw_image is None:
            raise OCRError("Image illisible pour l'OCR", details={"image_path": image_path})

        if not self._apply_preprocessing:
            return Image.fromarray(cv2.cvtColor(raw_image, cv2.COLOR_BGR2RGB))

        grayscale = cv2.cvtColor(raw_image, cv2.COLOR_BGR2GRAY)
        _, binarized = cv2.threshold(
            grayscale, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        return Image.fromarray(binarized)

    def _compute_mean_confidence(self, image: Image.Image, language: str) -> float:
        """Calcule la confiance moyenne de l'OCR sur une image.

        Args:
            image: Image préparée pour l'OCR.
            language: Code(s) langue Tesseract.

        Returns:
            Confiance moyenne entre 0 et 100 (0.0 si aucune donnée exploitable).
        """
        data = pytesseract.image_to_data(image, lang=language, output_type=pytesseract.Output.DICT)
        confidences = [float(c) for c in data.get("conf", []) if c not in ("-1", -1)]
        if not confidences:
            return 0.0
        return float(np.mean(confidences))
