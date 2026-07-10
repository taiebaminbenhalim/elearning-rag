"""Fonctions utilitaires communes de manipulation de texte."""

from __future__ import annotations


def count_words(text: str) -> int:
    """Compte le nombre de mots d'un texte (séparation par espaces).

    Args:
        text: Texte à analyser.

    Returns:
        Nombre de mots.
    """
    return len(text.split())


def count_chars(text: str) -> int:
    """Compte le nombre de caractères d'un texte.

    Args:
        text: Texte à analyser.

    Returns:
        Nombre de caractères.
    """
    return len(text)
