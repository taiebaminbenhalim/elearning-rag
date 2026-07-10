"""Service ChapterDetector : détection des chapitres pilotée par dictionnaire."""

from __future__ import annotations

import re
from typing import Any

from exceptions import ChapterDetectionError
from models import Chapter, Document, Status, Subject
from utils import get_logger

logger = get_logger(__name__)


class ChapterDetector:
    """Détecte les chapitres du document à partir de ``structure_indicators.json``.

    Contrairement à la V1 (une seule regex "Chapitre X" en dur dans
    ``StructureAnalyzer``), la V2 pilote la détection par les patterns
    pondérés du dictionnaire de structure, ce qui permet d'ajuster la
    détection sans modifier le code.

    Conformément au cahier des charges :
        * les chapitres ne sont détectés que lorsqu'ils existent (un
          document sans aucun chapitre détecté continue le pipeline
          normalement, sans lever d'erreur) ;
        * chaque chapitre est rattaché à la matière (:class:`Subject`)
          couvrant ses pages.

    Attributes:
        chapter_patterns: Patterns pondérés (regex compilées, poids)
            issus de ``structure_indicators.json`` (clé ``chapter``).
    """

    def __init__(self, structure_dictionary: dict[str, Any]) -> None:
        """Initialise le détecteur de chapitres.

        Args:
            structure_dictionary: Contenu déjà chargé de ``structure_indicators.json``.

        Raises:
            ChapterDetectionError: Si la section ``chapter`` est absente du
                dictionnaire de structure.
        """
        indicators = structure_dictionary.get("structure_indicators", structure_dictionary)
        chapter_rules = indicators.get("chapter")
        if not chapter_rules:
            raise ChapterDetectionError(
                "Dictionnaire de structure invalide : section 'chapter' manquante"
            )

        self._patterns: list[tuple[re.Pattern[str], float]] = [
            (re.compile(entry["pattern"]), float(entry.get("weight", 1.0)))
            for entry in chapter_rules.get("patterns", [])
        ]

    def detect(self, document: Document) -> Document:
        """Détecte les chapitres du document et remplit ``document.chapters``.

        Args:
            document: Document dont les pages possèdent déjà un ``cleaning_data``.

        Returns:
            Le même Document, avec ``chapters`` rempli (liste vide si aucun
            chapitre détecté : c'est un cas normal, pas une erreur).
        """
        chapters: list[Chapter] = []
        chapter_number = 0

        for page in sorted(document.pages, key=lambda p: p.page_number):
            if page.cleaning_data is None:
                continue

            for line in page.cleaning_data.cleaned_text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue

                best_match = self._best_match(stripped)
                if best_match is None:
                    continue

                chapter_number += 1
                chapters.append(
                    Chapter(
                        title=stripped,
                        number=chapter_number,
                        page_numbers=[page.page_number],
                    )
                )

        self._extend_chapter_page_ranges(chapters, document)
        self._assign_subjects(chapters, document.subjects)

        document.chapters = chapters
        document.logical_structure.chapter_ids = [c.chapter_id for c in chapters]
        document.pipeline_info.current_step = "chapter_detection"
        document.pipeline_info.status = Status.CHAPTERS_DETECTED
        document.status = Status.CHAPTERS_DETECTED

        logger.info(
            "%d chapitre(s) détecté(s) (document %s)", len(chapters), document.document_id
        )
        return document

    def _best_match(self, line: str) -> float | None:
        """Retourne le meilleur poids de pattern correspondant à la ligne, si trouvé.

        Args:
            line: Ligne de texte à tester.

        Returns:
            Le poids du meilleur pattern trouvé, ou ``None`` si aucun ne correspond.
        """
        best_weight: float | None = None
        for pattern, weight in self._patterns:
            if pattern.search(line):
                if best_weight is None or weight > best_weight:
                    best_weight = weight
        return best_weight

    def _extend_chapter_page_ranges(self, chapters: list[Chapter], document: Document) -> None:
        """Étend chaque chapitre jusqu'à la page précédant le chapitre suivant.

        Args:
            chapters: Chapitres détectés, dans l'ordre d'apparition.
            document: Document source, pour connaître la dernière page.
        """
        if not chapters or not document.pages:
            return

        last_page_number = max(page.page_number for page in document.pages)
        for index, chapter in enumerate(chapters):
            start = chapter.page_numbers[0]
            end = (
                chapters[index + 1].page_numbers[0] - 1
                if index + 1 < len(chapters)
                else last_page_number
            )
            chapter.page_numbers = list(range(start, max(start, end) + 1))

    def _assign_subjects(self, chapters: list[Chapter], subjects: list[Subject]) -> None:
        """Rattache chaque chapitre à la matière couvrant la majorité de ses pages.

        Args:
            chapters: Chapitres détectés, dont les plages de pages sont déjà étendues.
            subjects: Matières détectées par :class:`~core.subject_detector.SubjectDetector`.
        """
        for chapter in chapters:
            chapter_pages = set(chapter.page_numbers)
            best_subject_id: str | None = None
            best_overlap = 0
            for subject in subjects:
                overlap = len(chapter_pages.intersection(subject.page_numbers))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_subject_id = subject.subject_id
            chapter.subject_id = best_subject_id
