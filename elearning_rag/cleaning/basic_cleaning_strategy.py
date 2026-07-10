"""Stratégie de nettoyage basique du texte OCR."""

from __future__ import annotations

import re

from core.interfaces import ICleaningStrategy


class BasicCleaningStrategy(ICleaningStrategy):
    """Stratégie de nettoyage V1 : corrections génériques, indépendantes de l'OCR.

    Applique des règles simples et robustes, sans dépendre du moteur OCR
    utilisé en amont : normalisation des espaces, suppression des
    caractères parasites récurrents en sortie d'OCR, normalisation des
    retours à la ligne.

    L'architecture permet d'ajouter d'autres stratégies (ex: nettoyage
    spécifique aux mathématiques) en implémentant :class:`ICleaningStrategy`,
    sans modifier ``core/cleaning_service.py``.
    """

    _MULTIPLE_SPACES = re.compile(r"[ \t]+")
    _MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
    _PARASITE_CHARS = re.compile(r"[|_~`^]+")

    @property
    def strategy_name(self) -> str:
        """Nom de la stratégie de nettoyage."""
        return "basic_cleaning"

    def clean(self, raw_text: str) -> str:
        """Nettoie un texte brut issu de l'OCR.

        Args:
            raw_text: Texte brut à nettoyer.

        Returns:
            Le texte nettoyé : espaces normalisés, caractères parasites
            supprimés, retours à la ligne normalisés, texte "strippé".
        """
        text = self._PARASITE_CHARS.sub(" ", raw_text)
        text = self._MULTIPLE_SPACES.sub(" ", text)
        text = self._MULTIPLE_NEWLINES.sub("\n\n", text)
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)
        return text.strip()
