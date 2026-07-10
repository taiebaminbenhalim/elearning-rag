"""Service SubjectDetector : détection de la matière, page par page."""

from __future__ import annotations

import re
from typing import Any

from exceptions import SubjectDetectionError
from models import Document, Page, Status, Subject
from utils import get_logger

logger = get_logger(__name__)


class SubjectDetector:
    """Détecte la matière de chaque page, puis regroupe les pages consécutives.

    Conformément au cahier des charges de la V2 :
        * chaque page est analysée indépendamment et reçoit une matière
          détectée et un score de confiance ;
        * les pages consécutives appartenant à la même matière sont
          ensuite regroupées en un seul :class:`~models.subject.Subject` ;
        * un document peut contenir une ou plusieurs matières ;
        * une page n'appartient jamais qu'à une seule matière.

    Utilise exclusivement ``subject_detection.json`` (injecté sous forme
    de dictionnaire déjà chargé, jamais de chemin de fichier en dur), sans
    dictionnaire spécialisé par matière (réservés à la V3).

    Attributes:
        subject_rules: Contenu de ``subject_detection.json`` (clé ``subjects``).
    """

    _UNKNOWN_SUBJECT = "unknown"

    def __init__(self, subject_dictionary: dict[str, Any]) -> None:
        """Initialise le détecteur de matières.

        Args:
            subject_dictionary: Contenu déjà chargé de ``subject_detection.json``.

        Raises:
            SubjectDetectionError: Si le dictionnaire ne contient pas la clé
                ``subjects`` attendue.
        """
        if "subjects" not in subject_dictionary:
            raise SubjectDetectionError(
                "Dictionnaire de matières invalide : clé 'subjects' manquante"
            )
        self._subjects = subject_dictionary["subjects"]

    def detect(self, document: Document) -> Document:
        """Détecte les matières du document et remplit ``document.subjects``.

        Args:
            document: Document dont les pages possèdent déjà un ``cleaning_data``
                (produit par :class:`~core.cleaning_service.CleaningService`).

        Returns:
            Le même Document, avec ``subjects`` rempli.

        Raises:
            SubjectDetectionError: Si aucune page n'a de texte nettoyé disponible.
        """
        page_scores: list[tuple[Page, str, str, float]] = []

        for page in sorted(document.pages, key=lambda p: p.page_number):
            if page.cleaning_data is None:
                raise SubjectDetectionError(
                    "Aucun texte nettoyé disponible pour la détection de matière",
                    details={"page_number": page.page_number},
                )
            code, name, confidence = self._detect_page_subject(page.cleaning_data.cleaned_text)
            page_scores.append((page, code, name, confidence))

        document.subjects = self._group_consecutive_pages(page_scores)
        document.logical_structure.subject_ids = [s.subject_id for s in document.subjects]
        document.pipeline_info.current_step = "subject_detection"
        document.pipeline_info.status = Status.SUBJECTS_DETECTED
        document.status = Status.SUBJECTS_DETECTED

        logger.info(
            "%d groupe(s) de matière détecté(s) (document %s): %s",
            len(document.subjects),
            document.document_id,
            [s.name for s in document.subjects],
        )
        return document

    def _detect_page_subject(self, text: str) -> tuple[str, str, float]:
        """Détecte la matière la plus probable pour le texte d'une page.

        Args:
            text: Texte nettoyé de la page.

        Returns:
            Un tuple ``(code_matiere, nom_matiere, confiance)``. Si aucune
            matière ne dépasse son seuil ``min_matches``, retourne
            ``("unknown", "Indéterminée", 0.0)``.
        """
        lowered_text = text.lower()
        best_code = self._UNKNOWN_SUBJECT
        best_name = "Indéterminée"
        best_score = 0.0

        for code, subject in self._subjects.items():
            rules = subject.get("detection_rules", {})
            score, matches = self._score_subject(lowered_text, rules)

            if matches < rules.get("min_matches", 1):
                continue

            weighted_score = score * float(rules.get("weight", 1.0))
            if weighted_score > best_score:
                best_score = weighted_score
                best_code = code
                best_name = subject.get("name", code)

        confidence = min(best_score / 10.0, 1.0) if best_score > 0 else 0.0
        return best_code, best_name, confidence

    def _score_subject(self, lowered_text: str, rules: dict[str, Any]) -> tuple[float, int]:
        """Calcule le score brut et le nombre de correspondances pour une matière.

        Les mots-clés courts (ex: unités physiques comme ``"U"``, ``"I"``,
        ``"R"``) sont recherchés avec une frontière de mot (``\\b``) pour
        éviter les faux positifs d'une simple recherche de sous-chaîne
        (ex: la lettre ``"u"`` apparaissant dans n'importe quel mot).

        Args:
            lowered_text: Texte de la page en minuscules.
            rules: Règles de détection de la matière (``detection_rules``).

        Returns:
            Un tuple ``(score, nombre_de_correspondances)``.
        """
        excluded_terms = [term.lower() for term in rules.get("exclude", [])]
        if any(self._contains(lowered_text, term) for term in excluded_terms):
            return 0.0, 0

        score = 0.0
        matches = 0

        for keyword in rules.get("keywords", []):
            if self._contains(lowered_text, keyword.lower()):
                score += 1.0
                matches += 1

        for strong_keyword in rules.get("strong_keywords", []):
            if self._contains(lowered_text, strong_keyword.lower()):
                score += 2.0
                matches += 1

        return score, matches

    def _contains(self, lowered_text: str, term: str) -> bool:
        """Vérifie la présence d'un terme dans le texte.

        Les termes courts (2 caractères ou moins) sont recherchés avec une
        frontière de mot afin d'éviter les faux positifs (ex: la lettre
        ``"u"`` ne doit matcher que le mot ``"u"`` isolé, pas n'importe
        quel mot la contenant).

        Args:
            lowered_text: Texte en minuscules dans lequel chercher.
            term: Terme à rechercher (déjà en minuscules).

        Returns:
            ``True`` si le terme est présent selon la règle applicable.
        """
        if len(term) <= 2:
            return re.search(rf"\b{re.escape(term)}\b", lowered_text) is not None
        return term in lowered_text

    def _group_consecutive_pages(
        self, page_scores: list[tuple[Page, str, str, float]]
    ) -> list[Subject]:
        """Regroupe les pages consécutives partageant la même matière détectée.

        Args:
            page_scores: Liste ordonnée de ``(page, code, nom, confiance)``.

        Returns:
            Liste de :class:`~models.subject.Subject`, un par groupe de
            pages consécutives de même matière.
        """
        subjects: list[Subject] = []
        current_code: str | None = None
        current_name = ""
        current_pages: list[int] = []
        current_confidences: list[float] = []

        def flush() -> None:
            if current_pages:
                subjects.append(
                    Subject(
                        subject_code=current_code or self._UNKNOWN_SUBJECT,
                        name=current_name,
                        page_numbers=list(current_pages),
                        confidence=sum(current_confidences) / len(current_confidences),
                    )
                )

        for page, code, name, confidence in page_scores:
            if code != current_code:
                flush()
                current_code, current_name = code, name
                current_pages, current_confidences = [], []
            current_pages.append(page.page_number)
            current_confidences.append(confidence)

        flush()
        return subjects
