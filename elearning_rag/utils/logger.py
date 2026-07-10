"""Configuration centralisée du logging du projet."""

from __future__ import annotations

import logging
import sys


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Crée ou récupère un logger configuré de manière homogène.

    Tous les services du projet doivent obtenir leur logger via cette
    fonction plutôt que d'appeler ``logging.getLogger`` directement, afin
    de garantir un format de log cohérent dans tout le pipeline.

    Args:
        name: Nom du logger, généralement ``__name__`` du module appelant.
        level: Niveau de log (``logging.INFO`` par défaut).

    Returns:
        Une instance de :class:`logging.Logger` configurée.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.propagate = False

    return logger
