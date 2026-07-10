"""Génération centralisée d'identifiants uniques."""

from __future__ import annotations

from uuid import uuid4


def generate_id() -> str:
    """Génère un identifiant unique universel (UUID4) sous forme de chaîne.

    Centralise la génération d'ID afin de garder une stratégie unique et
    facilement remplaçable (ex: passage à des ULID dans une future version)
    sans avoir à modifier chaque modèle individuellement.

    Returns:
        Une chaîne UUID4 unique.
    """
    return str(uuid4())
