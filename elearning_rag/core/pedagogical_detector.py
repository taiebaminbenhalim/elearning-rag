"""Service PedagogicalDetector : détection des éléments pédagogiques."""

from __future__ import annotations

import re
from typing import Any

from exceptions import PedagogicalDetectionError
from models import Chapter, Document, PedagogicalElement, PedagogicalType, Status, Subject
from utils import get_logger

logger = get_logger(__name__)


class PedagogicalDetector:
    """Détecte les éléments pédagogiques (Cours, Exercice, Activité, Examen, Correction).

    Conformément au cahier des charges de la V2, seuls ces 5 types sont
    détectés, sans granularité fine (pas de "Exercice 1", "Question 2"...).
    Chaque élément est rattaché à un chapitre lorsqu'il en existe un pour
    sa page, sinon directement à la matière de sa page.

    Attributes:
        type_rules: Association entre chaque :class:`PedagogicalType` et
            les patterns pondérés correspondants de ``structure_indicators.json``.
    """

    # Association entre les sections du dictionnaire de structure et les
    # types pédagogiques de la V2 (un seul type peut être alimenté par
    # plusieurs sections du dictionnaire, ex: "exercise" et "exercise_set").
    _SECTION_TO_TYPE: dict[str, PedagogicalType] = {
        "course_content": PedagogicalType.COURS,
        "exercise": PedagogicalType.EXERCICE,
        "solved_exercise": PedagogicalType.EXERCICE,
        "exercise_set": PedagogicalType.EXERCICE,
        "activity": PedagogicalType.ACTIVITE,
        "experiment": PedagogicalType.ACTIVITE,
        "exam": PedagogicalType.EXAMEN,
        "evaluation": PedagogicalType.EXAMEN,
        "correction": PedagogicalType.CORRECTION,
    }

    def __init__(self, structure_dictionary: dict[str, Any]) -> None:
        """Initialise le détecteur d'éléments pédagogiques.

        Args:
            structure_dictionary: Contenu déjà chargé de ``structure_indicators.json``.

        Raises:
            PedagogicalDetectionError: Si aucune des sections attendues
                n'est présente dans le dictionnaire de structure.
        """
        indicators = structure_dictionary.get("structure_indicators", structure_dictionary)

        self._type_rules: dict[PedagogicalType, list[tuple[re.Pattern[str], float]]] = {}
        for section_name, pedagogical_type in self._SECTION_TO_TYPE.items():
            section = indicators.get(section_name)
            if not section:
                continue
            patterns = [
                (re.compile(entry["pattern"]), float(entry.get("weight", 1.0)))
                for entry in section.get("patterns", [])
            ]
            self._type_rules.setdefault(pedagogical_type, []).extend(patterns)

        if not self._type_rules:
            raise PedagogicalDetectionError(
                "Dictionnaire de structure invalide : aucune section pédagogique trouvée",
                details={"expected_sections": sorted(self._SECTION_TO_TYPE)},
            )

    def detect(self, document: Document) -> Document:
        """Détecte les éléments pédagogiques du document.

        Args:
            document: Document dont les pages, chapitres et matières ont
                déjà été détectés par les services précédents.

        Returns:
            Le même Document, avec ``pedagogical_elements`` rempli (liste
            vide si aucun élément détecté).
        """
        elements: list[PedagogicalElement] = []

        for page in sorted(document.pages, key=lambda p: p.page_number):
            if page.cleaning_data is None:
                continue

            detected_types = self._detect_types_on_page(page.cleaning_data.cleaned_text)
            chapter = self._find_chapter_for_page(page.page_number, document.chapters)
            subject = self._find_subject_for_page(page.page_number, document.subjects)

            for pedagogical_type, confidence in detected_types.items():
                elements.append(
                    PedagogicalElement(
                        pedagogical_type=pedagogical_type,
                        page_numbers=[page.page_number],
                        chapter_id=chapter.chapter_id if chapter else None,
                        subject_id=None if chapter else (subject.subject_id if subject else None),
                        confidence=confidence,
                    )
                )

        document.pedagogical_elements = elements
        document.logical_structure.pedagogical_element_ids = [e.element_id for e in elements]
        document.pipeline_info.current_step = "pedagogical_detection"
        document.pipeline_info.status = Status.PEDAGOGY_DETECTED
        document.status = Status.PEDAGOGY_DETECTED

        logger.info(
            "%d élément(s) pédagogique(s) détecté(s) (document %s)",
            len(elements),
            document.document_id,
        )
        return document

    def _detect_types_on_page(self, text: str) -> dict[PedagogicalType, float]:
        """Détecte les types pédagogiques présents sur une page.

        Args:
            text: Texte nettoyé de la page.

        Returns:
            Association ``{type_pédagogique: confiance}`` pour chaque type
            détecté (une page peut contenir plusieurs types, ex: un cours
            suivi d'exercices).
        """
        results: dict[PedagogicalType, float] = {}
        for pedagogical_type, patterns in self._type_rules.items():
            best_weight = 0.0
            for pattern, weight in patterns:
                if pattern.search(text) and weight > best_weight:
                    best_weight = weight
            if best_weight > 0:
                results[pedagogical_type] = min(best_weight / 1.5, 1.0)
        return results

    def _find_chapter_for_page(self, page_number: int, chapters: list[Chapter]) -> Chapter | None:
        """Retourne le chapitre couvrant la page donnée, s'il existe.

        Args:
            page_number: Numéro de page recherché.
            chapters: Chapitres détectés par :class:`~core.chapter_detector.ChapterDetector`.

        Returns:
            Le chapitre correspondant, ou ``None`` si le document n'a pas
            de chapitre couvrant cette page (cas normal, ex: recueil d'examens).
        """
        return next((c for c in chapters if page_number in c.page_numbers), None)

    def _find_subject_for_page(self, page_number: int, subjects: list[Subject]) -> Subject | None:
        """Retourne la matière couvrant la page donnée, si elle existe.

        Args:
            page_number: Numéro de page recherché.
            subjects: Matières détectées par :class:`~core.subject_detector.SubjectDetector`.

        Returns:
            La matière correspondante, ou ``None``.
        """
        return next((s for s in subjects if page_number in s.page_numbers), None)
