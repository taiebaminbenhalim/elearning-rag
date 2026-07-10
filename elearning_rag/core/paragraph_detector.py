"""Service ParagraphDetector : détection des paragraphes (logique V1 inchangée)."""

from __future__ import annotations

from exceptions import StructureAnalysisError
from models import Chapter, Document, Paragraph
from utils import get_logger

logger = get_logger(__name__)


class ParagraphDetector:
    """Détecte les paragraphes du document.

    Extrait de :class:`~core.structure_analyzer.StructureAnalyzer` (V1)
    afin de respecter le principe de responsabilité unique en V2 : la
    détection des chapitres est désormais assurée séparément par
    :class:`~core.chapter_detector.ChapterDetector`, piloté par
    ``structure_indicators.json``.

    Conformément au cahier des charges de la V2, la logique de découpage
    des paragraphes reste **exactement identique** à la V1 (groupement des
    lignes non vides séparées par des lignes blanches). Seul le
    rattachement du paragraphe à son chapitre change : au lieu de détecter
    le chapitre au passage, ce service reçoit les chapitres déjà détectés
    et rattache chaque paragraphe au chapitre couvrant sa page.
    """

    def detect(self, document: Document) -> Document:
        """Détecte les paragraphes du document.

        Args:
            document: Document dont les pages possèdent déjà un
                ``cleaning_data``, et dont les chapitres ont déjà été
                détectés par :class:`~core.chapter_detector.ChapterDetector`
                (peut être une liste vide : cas normal).

        Returns:
            Le même Document, avec ``paragraphs`` rempli.

        Raises:
            StructureAnalysisError: Si aucun texte nettoyé n'est disponible,
                ou si aucun paragraphe n'a pu être détecté.
        """
        lines_with_page = self._collect_lines(document)
        if not lines_with_page:
            raise StructureAnalysisError(
                "Aucun texte nettoyé disponible pour la détection des paragraphes",
                details={"document_id": document.document_id},
            )

        paragraphs = self._build_paragraphs(lines_with_page, document.chapters)

        if not paragraphs:
            raise StructureAnalysisError(
                "Aucun paragraphe détecté dans le document",
                details={"document_id": document.document_id},
            )

        for chapter in document.chapters:
            chapter.paragraph_ids = [
                p.paragraph_id for p in paragraphs if p.chapter_id == chapter.chapter_id
            ]

        document.paragraphs = paragraphs
        document.logical_structure.paragraph_ids = [p.paragraph_id for p in paragraphs]

        logger.info(
            "%d paragraphe(s) détecté(s) (document %s)", len(paragraphs), document.document_id
        )
        return document

    def _collect_lines(self, document: Document) -> list[tuple[str, int]]:
        """Reconstitue la liste ordonnée des lignes non vides avec leur page d'origine.

        Args:
            document: Document dont les pages possèdent un ``cleaning_data``.

        Returns:
            Liste de tuples ``(ligne, numero_de_page)``.
        """
        lines_with_page: list[tuple[str, int]] = []
        for page in sorted(document.pages, key=lambda p: p.page_number):
            if page.cleaning_data is None:
                continue
            for line in page.cleaning_data.cleaned_text.split("\n"):
                lines_with_page.append((line, page.page_number))
        return lines_with_page

    def _find_chapter_for_page(self, page_number: int, chapters: list[Chapter]) -> Chapter | None:
        """Retourne le chapitre couvrant la page donnée, s'il existe.

        Args:
            page_number: Numéro de page recherché.
            chapters: Chapitres déjà détectés.

        Returns:
            Le chapitre correspondant, ou ``None``.
        """
        return next((c for c in chapters if page_number in c.page_numbers), None)

    def _build_paragraphs(
        self, lines_with_page: list[tuple[str, int]], chapters: list[Chapter]
    ) -> list[Paragraph]:
        """Construit les paragraphes à partir des lignes du document.

        Identique à la logique de regroupement de la V1 : les lignes non
        vides consécutives forment un paragraphe, une ligne vide marque
        une frontière entre deux paragraphes.

        Args:
            lines_with_page: Lignes ordonnées avec leur page d'origine.
            chapters: Chapitres déjà détectés, pour rattacher chaque
                paragraphe à son chapitre le cas échéant.

        Returns:
            Liste des paragraphes construits.
        """
        paragraphs: list[Paragraph] = []
        current_lines: list[str] = []
        current_pages: set[int] = set()

        def flush() -> None:
            nonlocal current_lines, current_pages
            text = " ".join(line.strip() for line in current_lines if line.strip())
            if text:
                pages = sorted(current_pages)
                chapter = self._find_chapter_for_page(pages[0], chapters) if pages else None
                paragraphs.append(
                    Paragraph(
                        text=text,
                        chapter_id=chapter.chapter_id if chapter else None,
                        page_numbers=pages,
                    )
                )
            current_lines = []
            current_pages = set()

        for line, page_number in lines_with_page:
            stripped = line.strip()
            if not stripped:
                flush()
                continue
            current_lines.append(stripped)
            current_pages.add(page_number)

        flush()
        return paragraphs
