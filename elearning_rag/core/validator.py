"""Service Validator : contrôle de cohérence du document à chaque étape."""

from __future__ import annotations

from exceptions import ValidationError
from models import Document
from utils import get_logger

logger = get_logger(__name__)


class Validator:
    """Vérifie la cohérence du document avant/après chaque étape du pipeline.

    Ce service est appelé par le :class:`~core.pipeline.Pipeline` entre
    chaque service afin de détecter au plus tôt une incohérence (aucune
    page, OCR absent, chunk vide, embedding invalide...).
    """

    def validate_loaded(self, document: Document) -> None:
        """Valide le document juste après le chargement du PDF.

        Args:
            document: Document à valider.

        Raises:
            ValidationError: Si le document ne possède aucune page.
        """
        if not document.pages:
            raise ValidationError("Le document ne contient aucune page", details={"document_id": document.document_id})

    def validate_ocr(self, document: Document) -> None:
        """Valide le document après l'étape OCR.

        Args:
            document: Document à valider.

        Raises:
            ValidationError: Si une page n'a pas de données OCR.
        """
        missing = [page.page_number for page in document.pages if page.ocr_data is None]
        if missing:
            raise ValidationError(
                "Des pages n'ont pas de données OCR",
                details={"document_id": document.document_id, "pages": missing},
            )

    def validate_cleaning(self, document: Document) -> None:
        """Valide le document après l'étape de nettoyage.

        Args:
            document: Document à valider.

        Raises:
            ValidationError: Si une page n'a pas de données de nettoyage.
        """
        missing = [page.page_number for page in document.pages if page.cleaning_data is None]
        if missing:
            raise ValidationError(
                "Des pages n'ont pas de données de nettoyage",
                details={"document_id": document.document_id, "pages": missing},
            )

    def validate_structure(self, document: Document) -> None:
        """Valide le document après l'analyse de structure.

        Args:
            document: Document à valider.

        Raises:
            ValidationError: Si aucun paragraphe n'a été détecté.
        """
        if not document.paragraphs:
            raise ValidationError(
                "Aucun paragraphe détecté", details={"document_id": document.document_id}
            )

    def validate_chunks(self, document: Document) -> None:
        """Valide le document après le chunking.

        Args:
            document: Document à valider.

        Raises:
            ValidationError: Si aucun chunk n'a été produit, ou si un chunk
                est vide.
        """
        if not document.chunks:
            raise ValidationError("Aucun chunk produit", details={"document_id": document.document_id})

        empty_chunks = [chunk.chunk_id for chunk in document.chunks if not chunk.text.strip()]
        if empty_chunks:
            raise ValidationError(
                "Des chunks vides ont été détectés",
                details={"document_id": document.document_id, "chunk_ids": empty_chunks},
            )

    def validate_embeddings(self, document: Document) -> None:
        """Valide le document après la génération des embeddings.

        Args:
            document: Document à valider.

        Raises:
            ValidationError: Si le nombre d'embeddings ne correspond pas au
                nombre de chunks, ou si un vecteur est invalide (vide).
        """
        if len(document.embeddings) != len(document.chunks):
            raise ValidationError(
                "Le nombre d'embeddings ne correspond pas au nombre de chunks",
                details={
                    "document_id": document.document_id,
                    "chunks": len(document.chunks),
                    "embeddings": len(document.embeddings),
                },
            )

        invalid = [e.embedding_id for e in document.embeddings if not e.vector]
        if invalid:
            raise ValidationError(
                "Des embeddings invalides ont été détectés",
                details={"document_id": document.document_id, "embedding_ids": invalid},
            )

    def validate_subjects(self, document: Document) -> None:
        """Valide le document après la détection des matières (V2).

        Args:
            document: Document à valider.

        Raises:
            ValidationError: Si aucune matière n'a été détectée, ou si des
                pages du document ne sont couvertes par aucune matière.
        """
        if not document.subjects:
            raise ValidationError(
                "Aucune matière détectée", details={"document_id": document.document_id}
            )

        covered_pages = {page for subject in document.subjects for page in subject.page_numbers}
        all_pages = {page.page_number for page in document.pages}
        missing = all_pages - covered_pages
        if missing:
            raise ValidationError(
                "Des pages ne sont couvertes par aucune matière détectée",
                details={"document_id": document.document_id, "pages": sorted(missing)},
            )

    def validate_academic_context(self, document: Document) -> None:
        """Valide le document après la détection du niveau scolaire (V2).

        La détection du niveau est best-effort (un document peut ne
        contenir aucun indice de niveau) : cette validation ne lève donc
        jamais d'exception, elle se contente de journaliser un
        avertissement pour faciliter le diagnostic.

        Args:
            document: Document à valider.
        """
        if document.academic_context.confidence == 0.0:
            logger.warning(
                "Aucun contexte académique détecté (document %s)", document.document_id
            )

    def validate_structure_v2(self, document: Document) -> None:
        """Valide le document après la construction de la structure logique (V2).

        Args:
            document: Document à valider.

        Raises:
            ValidationError: Si aucun paragraphe n'a été détecté. L'absence
                de chapitres ou d'éléments pédagogiques n'est jamais une
                erreur (cas normal pour certains documents).
        """
        if not document.paragraphs:
            raise ValidationError(
                "Aucun paragraphe détecté", details={"document_id": document.document_id}
            )
