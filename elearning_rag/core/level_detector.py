"""Service LevelDetector : détection du niveau scolaire, section, trimestre."""

from __future__ import annotations

import re
from typing import Any

from exceptions import LevelDetectionError
from models import AcademicContext, Document, Status
from utils import get_logger

logger = get_logger(__name__)


class LevelDetector:
    """Détecte le contexte académique du document (niveau, section, trimestre).

    Utilise exclusivement ``level_indicators.json``. Le résultat est stocké
    dans :class:`~models.academic_context.AcademicContext`, un objet
    séparé de :class:`~models.metadata.Metadata` conformément au cahier
    des charges de la V2.

    Le document est généralement identifiable dès les premières pages
    (couverture, page de titre) : par défaut, seules les
    ``pages_to_scan`` premières pages sont analysées.

    Attributes:
        level_dictionary: Contenu de ``level_indicators.json``.
        pages_to_scan: Nombre de pages initiales analysées.
    """

    _SCHOOL_YEAR_PATTERN = re.compile(r"\b(20\d{2})\s*[-/]\s*(20\d{2})\b")

    def __init__(self, level_dictionary: dict[str, Any], pages_to_scan: int = 5) -> None:
        """Initialise le détecteur de niveau scolaire.

        Args:
            level_dictionary: Contenu déjà chargé de ``level_indicators.json``.
            pages_to_scan: Nombre de pages initiales à analyser (les
                informations de niveau se trouvent généralement en début
                de document).

        Raises:
            LevelDetectionError: Si le dictionnaire ne contient aucune des
                clés attendues.
        """
        expected_keys = {"college", "sections", "trimesters"}
        if not expected_keys.intersection(level_dictionary.keys()):
            raise LevelDetectionError(
                "Dictionnaire de niveaux invalide : aucune clé attendue trouvée",
                details={"expected_keys": sorted(expected_keys)},
            )
        self._level_dictionary = level_dictionary
        self._pages_to_scan = pages_to_scan

    def detect(self, document: Document) -> Document:
        """Détecte le contexte académique du document.

        Args:
            document: Document dont les pages possèdent déjà un ``cleaning_data``.

        Returns:
            Le même Document, avec ``academic_context`` rempli.
        """
        scanned_pages = sorted(document.pages, key=lambda p: p.page_number)[: self._pages_to_scan]
        combined_text = "\n".join(
            page.cleaning_data.cleaned_text for page in scanned_pages if page.cleaning_data
        )

        level = self._find_first_match(combined_text, self._level_dictionary.get("college", []))
        section = self._find_first_match(combined_text, self._level_dictionary.get("sections", []))
        trimester = self._find_first_match(
            combined_text, self._level_dictionary.get("trimesters", [])
        )
        school_year = self._find_school_year(combined_text)

        found_count = sum(1 for value in (level, section, trimester, school_year) if value)
        confidence = found_count / 4.0

        document.academic_context = AcademicContext(
            level=level,
            section=section,
            trimester=trimester,
            school_year=school_year,
            confidence=confidence,
        )
        document.pipeline_info.current_step = "level_detection"
        document.pipeline_info.status = Status.LEVEL_DETECTED
        document.status = Status.LEVEL_DETECTED

        logger.info(
            "Contexte académique détecté (document %s): niveau=%s, section=%s, trimestre=%s, année=%s",
            document.document_id,
            level,
            section,
            trimester,
            school_year,
        )
        return document

    def _find_first_match(self, text: str, candidates: list[str]) -> str | None:
        """Retourne le premier candidat trouvé (insensible à la casse) dans le texte.

        Args:
            text: Texte dans lequel chercher.
            candidates: Liste de motifs candidats issus du dictionnaire de niveaux.

        Returns:
            Le candidat trouvé (avec sa casse d'origine du dictionnaire),
            ou ``None`` si aucun n'est présent.
        """
        lowered_text = text.lower()
        for candidate in candidates:
            if candidate.lower() in lowered_text:
                return candidate
        return None

    def _find_school_year(self, text: str) -> str | None:
        """Détecte une année scolaire au format ``AAAA-AAAA`` dans le texte.

        Cette information n'étant pas présente dans ``level_indicators.json``,
        une heuristique légère et documentée est utilisée en complément.

        Args:
            text: Texte dans lequel chercher.

        Returns:
            L'année scolaire trouvée (ex: ``"2023-2024"``), ou ``None``.
        """
        match = self._SCHOOL_YEAR_PATTERN.search(text)
        if not match:
            return None
        return f"{match.group(1)}-{match.group(2)}"
