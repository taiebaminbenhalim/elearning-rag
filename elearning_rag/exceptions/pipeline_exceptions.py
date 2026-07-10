"""Exceptions métier du pipeline RAG.

Ce module centralise toutes les exceptions personnalisées utilisées par le
projet. Chaque étape du pipeline (PDF, OCR, nettoyage, analyse de structure,
chunking, embedding, vector store, validation) possède sa propre exception
dédiée, toutes héritant de :class:`PipelineError`.

Les services du dossier ``core`` doivent systématiquement lever l'exception
métier la plus spécifique possible plutôt qu'une exception Python générique
(``ValueError``, ``RuntimeError``, etc.).
"""

from __future__ import annotations

from typing import Any


class PipelineError(Exception):
    """Exception racine de toutes les erreurs métier du pipeline.

    Toutes les exceptions spécifiques du projet héritent de cette classe.
    Elle permet, si besoin, d'intercepter n'importe quelle erreur métier du
    pipeline avec un seul ``except PipelineError``, tout en conservant des
    types précis pour un traitement fin lorsque nécessaire.

    Attributes:
        message: Description humaine de l'erreur.
        details: Informations contextuelles optionnelles (ex: identifiant
            de document, numéro de page, nom de fichier) utiles pour le
            logging et le diagnostic.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialise l'exception.

        Args:
            message: Description humaine de l'erreur.
            details: Dictionnaire optionnel de contexte additionnel.
        """
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}

    def __str__(self) -> str:
        """Retourne une représentation lisible incluant le contexte éventuel."""
        if not self.details:
            return self.message
        details_str = ", ".join(f"{key}={value!r}" for key, value in self.details.items())
        return f"{self.message} ({details_str})"


class PDFLoadError(PipelineError):
    """Levée lorsque le chargement ou la lecture d'un PDF échoue.

    Cas typiques : fichier introuvable, fichier corrompu, format non
    supporté, PDF illisible par PyMuPDF, conversion page → image impossible.
    """


class OCRError(PipelineError):
    """Levée lorsque l'extraction de texte par OCR échoue.

    Cas typiques : moteur OCR indisponible, langue non installée, image
    illisible, échec du moteur Tesseract sur une page donnée.
    """


class CleaningError(PipelineError):
    """Levée lorsque le nettoyage du texte OCR échoue.

    Cas typiques : donnée OCR absente ou invalide en entrée du nettoyage,
    stratégie de nettoyage mal configurée.
    """


class StructureAnalysisError(PipelineError):
    """Levée lorsque l'analyse de la structure logique échoue.

    Cas typiques : impossible de détecter le moindre paragraphe, données
    nettoyées absentes ou vides.
    """


class ChunkingError(PipelineError):
    """Levée lorsque la construction des chunks sémantiques échoue.

    Cas typiques : paragraphe vide, échec du SemanticChunker, absence de
    paragraphes en entrée.
    """


class EmbeddingError(PipelineError):
    """Levée lorsque la génération des embeddings échoue.

    Cas typiques : modèle d'embedding non chargé, chunk vide, dimension de
    vecteur inattendue.
    """


class VectorStoreError(PipelineError):
    """Levée lorsqu'une opération sur la base vectorielle échoue.

    Cas typiques : collection ChromaDB non initialisable, écriture
    impossible, incohérence entre embeddings et métadonnées.
    """


class ValidationError(PipelineError):
    """Levée lorsque le :class:`~core.validator.Validator` détecte une
    incohérence dans le document en cours de traitement.

    Cas typiques : aucune page, OCR absent, chunk vide, embedding invalide.
    """


class SubjectDetectionError(PipelineError):
    """Levée lorsque la détection des matières échoue.

    Cas typiques : dictionnaire de matières absent ou invalide, aucun
    texte nettoyé disponible pour l'analyse.
    """


class LevelDetectionError(PipelineError):
    """Levée lorsque la détection du niveau scolaire échoue.

    Cas typiques : dictionnaire de niveaux absent ou invalide.
    """


class ChapterDetectionError(PipelineError):
    """Levée lorsque la détection des chapitres échoue.

    Cas typiques : dictionnaire de structure absent ou invalide.
    """


class PedagogicalDetectionError(PipelineError):
    """Levée lorsque la détection des éléments pédagogiques échoue.

    Cas typiques : dictionnaire de structure absent ou invalide.
    """


class StructureBuildError(PipelineError):
    """Levée lorsque l'assemblage de la structure logique échoue.

    Cas typiques : échec de l'un des détecteurs orchestrés par
    :class:`~core.structure_builder.StructureBuilder`.
    """


class DictionaryLoadError(PipelineError):
    """Levée lorsqu'un dictionnaire JSON de référence ne peut pas être chargé.

    Cas typiques : fichier introuvable (`subject_detection.json`,
    `level_indicators.json`, `structure_indicators.json`), JSON malformé.
    """
