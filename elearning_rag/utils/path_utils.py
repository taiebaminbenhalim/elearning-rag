"""Fonctions utilitaires de gestion des chemins de fichiers."""

from __future__ import annotations

from pathlib import Path

from exceptions import PDFLoadError


def ensure_directory(path: Path) -> Path:
    """Crée un répertoire (et ses parents) s'il n'existe pas déjà.

    Args:
        path: Chemin du répertoire à garantir.

    Returns:
        Le même chemin, sous forme de :class:`~pathlib.Path`, une fois créé.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_file_exists(path: Path) -> Path:
    """Vérifie qu'un fichier existe, lève une exception métier sinon.

    Args:
        path: Chemin du fichier à vérifier.

    Returns:
        Le même chemin si le fichier existe.

    Raises:
        PDFLoadError: Si le fichier n'existe pas ou n'est pas un fichier
            régulier.
    """
    if not path.exists() or not path.is_file():
        raise PDFLoadError("Le fichier PDF est introuvable", details={"path": str(path)})
    return path


def build_page_image_filename(document_id: str, page_number: int, extension: str = "png") -> str:
    """Construit un nom de fichier normalisé pour l'image d'une page.

    Args:
        document_id: Identifiant du document parent.
        page_number: Numéro de la page.
        extension: Extension du fichier image (sans le point).

    Returns:
        Un nom de fichier normalisé, ex: ``"<document_id>_page_0001.png"``.
    """
    return f"{document_id}_page_{page_number:04d}.{extension}"
