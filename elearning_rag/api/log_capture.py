"""Capture des logs applicatifs pendant l'exécution du pipeline.

Utilisé uniquement par l'interface de démonstration (`api/app.py`) pour
afficher la zone de logs demandée par le cahier des charges. Ne contient
aucune logique métier : un simple handler de logging en mémoire.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager


class _InMemoryLogHandler(logging.Handler):
    """Handler de logging qui accumule les messages formatés en mémoire."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[str] = []
        self.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(self.format(record))


@contextmanager
def capture_logs(logger_name: str = "") -> Iterator[list[str]]:
    """Capture temporairement les logs émis pendant le bloc ``with``.

    Args:
        logger_name: Nom du logger racine à écouter (vide = tous les
            loggers du projet, ceux-ci n'ayant pas ``propagate=False``
            désactivé par erreur — voir ``utils.logger.get_logger``).

    Yields:
        La liste (mutable, remplie au fur et à mesure) des lignes de log
        capturées pendant l'exécution du bloc.
    """
    handler = _InMemoryLogHandler()
    handler.setLevel(logging.INFO)

    # Les loggers du projet sont créés avec `propagate = False` (voir
    # utils/logger.py) pour éviter les doublons sur la sortie standard.
    # On attache donc ce handler directement sur chaque logger du projet
    # actif, en parcourant le registre des loggers Python.
    target_loggers = [
        logging.getLogger(name)
        for name in logging.root.manager.loggerDict
        if name.startswith(("core.", "main", "api."))
    ]

    for logger in target_loggers:
        logger.addHandler(handler)

    try:
        yield handler.records
    finally:
        for logger in target_loggers:
            logger.removeHandler(handler)
