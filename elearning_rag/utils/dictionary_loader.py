"""Chargement des dictionnaires JSON de référence (matières, niveaux, structure).

Centralise la lecture des ressources JSON utilisées par les détecteurs de
la V2 (`SubjectDetector`, `LevelDetector`, `ChapterDetector`,
`PedagogicalDetector`), afin qu'aucun service ne lise un fichier
directement ni ne code un chemin en dur.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exceptions import DictionaryLoadError
from utils.logger import get_logger

logger = get_logger(__name__)


def load_json_dictionary(path: Path) -> dict[str, Any]:
    """Charge un fichier JSON de référence et retourne son contenu.

    Args:
        path: Chemin du fichier JSON à charger.

    Returns:
        Le contenu du fichier JSON, sous forme de dictionnaire.

    Raises:
        DictionaryLoadError: Si le fichier est introuvable ou n'est pas un
            JSON valide.
    """
    if not path.exists() or not path.is_file():
        raise DictionaryLoadError(
            "Dictionnaire de référence introuvable", details={"path": str(path)}
        )

    try:
        with path.open(encoding="utf-8") as file:
            data: dict[str, Any] = json.load(file)
    except json.JSONDecodeError as exc:
        raise DictionaryLoadError(
            "Dictionnaire de référence invalide (JSON malformé)",
            details={"path": str(path), "cause": str(exc)},
        ) from exc

    logger.debug("Dictionnaire chargé: %s", path)
    return data
