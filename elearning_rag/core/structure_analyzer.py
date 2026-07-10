"""Service StructureAnalyzer : détection des chapitres et paragraphes."""

from __future__ import annotations

import re

from exceptions import StructureAnalysisError
from models import Chapter, Document, LogicalStructure, Paragraph, Status
from utils import get_logger

logger = get_logger(__name__)


class StructureAnalyzer:
    """Analyse le texte nettoyé et construit la structure logique du document.

    Conformément au cahier des charges, la V1 se limite à :
        * la détection des paragraphes (toujours effectuée) ;
        * la détection des chapitres "lorsqu'ils existent" (best-effort,
          basée sur des motifs de titres usuels).

    Aucune détection de matière, aucun dictionnaire spécialisé et aucun
    élément pédagogique ne sont traités ici : ces fonctionnalités sont
    explicitement réservées aux futures versions.

    Un chapitre est détecté lorsqu'une ligne correspond à un motif de
    titre usuel (ex: "Chapitre 3", "CHAPITRE III"). Si aucun motif n'est
    trouvé dans le document, un unique chapitre "générique" regroupe tous
    les paragraphes, afin que chaque paragraphe reste rattaché à un
    ``chapter_id`` cohérent.
    """

    _CHAPTER_PATTERN = re.compile(
        r"^\s*(chapitre|chapter)\s+([ivxlcdm0-9]+)\b(.*)$",
        re.IGNORECASE,
    )

    def analyze(self, document: Document) -> Document:
        """Détecte les paragraphes et les chapitres du document.

        Args:
            document: Document dont les pages possèdent déjà un ``cleaning_data``
                (produit par :class:`~core.cleaning_service.CleaningService`).

        Returns:
            Le même Document, enrichi de ``chapters``, ``paragraphs`` et
            ``logical_structure``.

        Raises:
            StructureAnalysisError: Si aucun texte nettoyé n'est disponible,
                ou si aucun paragraphe n'a pu être détecté.
        """
        lines_with_page = self._collect_lines(document)
        if not lines_with_page:
            raise StructureAnalysisError(
                "Aucun texte nettoyé disponible pour l'analyse de structure",
                details={"document_id": document.document_id},
            )

        chapters, paragraphs = self._build_chapters_and_paragraphs(lines_with_page)

        if not paragraphs:
            raise StructureAnalysisError(
                "Aucun paragraphe détecté dans le document",
                details={"document_id": document.document_id},
            )

        document.chapters = chapters
        document.paragraphs = paragraphs
        document.logical_structure = LogicalStructure(
            chapter_ids=[chapter.chapter_id for chapter in chapters],
            paragraph_ids=[paragraph.paragraph_id for paragraph in paragraphs],
        )
        document.pipeline_info.current_step = "structure_analysis"
        document.pipeline_info.status = Status.STRUCTURED
        document.status = Status.STRUCTURED

        logger.info(
            "Structure détectée: %d chapitre(s), %d paragraphe(s) (document %s)",
            len(chapters),
            len(paragraphs),
            document.document_id,
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

    def _build_chapters_and_paragraphs(
        self, lines_with_page: list[tuple[str, int]]
    ) -> tuple[list[Chapter], list[Paragraph]]:
        """Construit les chapitres et paragraphes à partir des lignes du document.

        Args:
            lines_with_page: Lignes ordonnées avec leur page d'origine.

        Returns:
            Un tuple ``(chapters, paragraphs)``.
        """
        chapters: list[Chapter] = []
        paragraphs: list[Paragraph] = []

        current_chapter: Chapter | None = None
        current_paragraph_lines: list[str] = []
        current_paragraph_pages: set[int] = set()
        chapter_number = 0

        def flush_paragraph() -> None:
            nonlocal current_paragraph_lines, current_paragraph_pages
            text = " ".join(line.strip() for line in current_paragraph_lines if line.strip())
            if text:
                paragraph = Paragraph(
                    text=text,
                    chapter_id=current_chapter.chapter_id if current_chapter else None,
                    page_numbers=sorted(current_paragraph_pages),
                )
                paragraphs.append(paragraph)
                if current_chapter:
                    current_chapter.paragraph_ids.append(paragraph.paragraph_id)
            current_paragraph_lines = []
            current_paragraph_pages = set()

        for line, page_number in lines_with_page:
            stripped = line.strip()
            chapter_match = self._CHAPTER_PATTERN.match(stripped) if stripped else None

            if chapter_match:
                flush_paragraph()
                chapter_number += 1
                current_chapter = Chapter(
                    title=stripped,
                    number=chapter_number,
                    page_numbers=[page_number],
                )
                chapters.append(current_chapter)
                continue

            if not stripped:
                flush_paragraph()
                continue

            current_paragraph_lines.append(stripped)
            current_paragraph_pages.add(page_number)
            if current_chapter and page_number not in current_chapter.page_numbers:
                current_chapter.page_numbers.append(page_number)

        flush_paragraph()

        if not chapters and paragraphs:
            fallback_chapter = Chapter(
                title="Document sans chapitres détectés",
                number=1,
                page_numbers=sorted({page for p in paragraphs for page in p.page_numbers}),
                paragraph_ids=[p.paragraph_id for p in paragraphs],
            )
            for paragraph in paragraphs:
                paragraph.chapter_id = fallback_chapter.chapter_id
            chapters.append(fallback_chapter)

        return chapters, paragraphs
