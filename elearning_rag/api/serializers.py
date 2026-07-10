"""Sérialisation du Document en dictionnaires JSON-compatibles.

Ce module ne contient aucune logique métier : il se contente de convertir
les objets métier (`models`) en structures simples, pour l'API et
l'interface de démonstration. Conformément au cahier des charges de
l'interface de démonstration, les vecteurs d'embeddings (1024 valeurs)
ne sont jamais sérialisés : seules leurs métadonnées le sont.
"""

from __future__ import annotations

from typing import Any

from models import Document


def serialize_page(document: Document) -> list[dict[str, Any]]:
    """Sérialise les pages du document, y compris le texte OCR brut.

    Args:
        document: Document dont les pages sont à sérialiser.

    Returns:
        Liste de dictionnaires, un par page.
    """
    return [
        {
            "page_number": page.page_number,
            "raw_text": page.ocr_data.raw_text if page.ocr_data else None,
            "mean_confidence": page.ocr_data.mean_confidence if page.ocr_data else None,
            "cleaned_text": page.cleaning_data.cleaned_text if page.cleaning_data else None,
        }
        for page in sorted(document.pages, key=lambda p: p.page_number)
    ]


def serialize_subjects(document: Document) -> list[dict[str, Any]]:
    """Sérialise les matières détectées.

    Args:
        document: Document dont les matières sont à sérialiser.

    Returns:
        Liste de dictionnaires, un par matière détectée.
    """
    return [
        {
            "subject_id": subject.subject_id,
            "subject_code": subject.subject_code,
            "name": subject.name,
            "page_numbers": subject.page_numbers,
            "confidence": round(subject.confidence, 3),
        }
        for subject in document.subjects
    ]


def serialize_academic_context(document: Document) -> dict[str, Any]:
    """Sérialise le contexte académique détecté.

    Args:
        document: Document dont le contexte académique est à sérialiser.

    Returns:
        Dictionnaire du contexte académique.
    """
    context = document.academic_context
    return {
        "level": context.level,
        "section": context.section,
        "trimester": context.trimester,
        "school_year": context.school_year,
        "confidence": round(context.confidence, 3),
    }


def serialize_chapters(document: Document) -> list[dict[str, Any]]:
    """Sérialise les chapitres détectés.

    Args:
        document: Document dont les chapitres sont à sérialiser.

    Returns:
        Liste de dictionnaires, un par chapitre.
    """
    return [
        {
            "chapter_id": chapter.chapter_id,
            "number": chapter.number,
            "title": chapter.title,
            "page_numbers": chapter.page_numbers,
            "subject_id": chapter.subject_id,
            "paragraph_count": len(chapter.paragraph_ids),
        }
        for chapter in document.chapters
    ]


def serialize_pedagogical_elements(document: Document) -> list[dict[str, Any]]:
    """Sérialise les éléments pédagogiques détectés.

    Args:
        document: Document dont les éléments pédagogiques sont à sérialiser.

    Returns:
        Liste de dictionnaires, un par élément pédagogique.
    """
    return [
        {
            "element_id": element.element_id,
            "type": element.pedagogical_type.value,
            "page_numbers": element.page_numbers,
            "chapter_id": element.chapter_id,
            "subject_id": element.subject_id,
            "confidence": round(element.confidence, 3),
        }
        for element in document.pedagogical_elements
    ]


def serialize_paragraphs(document: Document) -> list[dict[str, Any]]:
    """Sérialise les paragraphes détectés.

    Args:
        document: Document dont les paragraphes sont à sérialiser.

    Returns:
        Liste de dictionnaires, un par paragraphe.
    """
    return [
        {
            "paragraph_id": paragraph.paragraph_id,
            "text": paragraph.text,
            "chapter_id": paragraph.chapter_id,
            "page_numbers": paragraph.page_numbers,
        }
        for paragraph in document.paragraphs
    ]


def serialize_chunks(document: Document) -> list[dict[str, Any]]:
    """Sérialise les chunks générés, avec leurs métadonnées.

    Args:
        document: Document dont les chunks sont à sérialiser.

    Returns:
        Liste de dictionnaires, un par chunk.
    """
    return [
        {
            "chunk_id": chunk.chunk_id,
            "text": chunk.text,
            "page_numbers": chunk.page_numbers,
            "paragraph_ids": chunk.paragraph_ids,
            "chunk_index": chunk.metadata.chunk_index,
            "word_count": chunk.metadata.word_count,
            "char_count": chunk.metadata.char_count,
            "creation_method": chunk.metadata.creation_method,
            "context": chunk.context,
        }
        for chunk in document.chunks
    ]


def serialize_embeddings(document: Document) -> list[dict[str, Any]]:
    """Sérialise les métadonnées des embeddings, **sans** les vecteurs.

    Conformément au cahier des charges de l'interface de démonstration,
    les 1024 valeurs de chaque vecteur ne sont jamais exposées.

    Args:
        document: Document dont les embeddings sont à sérialiser.

    Returns:
        Liste de dictionnaires, un par embedding (métadonnées uniquement).
    """
    return [
        {
            "embedding_id": embedding.embedding_id,
            "chunk_id": embedding.chunk_id,
            "model_name": embedding.model_name,
            "dimension": embedding.dimension,
            "normalized": embedding.normalized,
            "created_at": embedding.created_at.isoformat(),
        }
        for embedding in document.embeddings
    ]


def serialize_document(document: Document) -> dict[str, Any]:
    """Sérialise un Document complet, pour l'API et l'interface de démonstration.

    Args:
        document: Document à sérialiser.

    Returns:
        Dictionnaire JSON-compatible, structuré par onglet de résultat
        (résumé, pages/OCR, matières, contexte académique, chapitres,
        éléments pédagogiques, paragraphes, chunks, embeddings).
    """
    return {
        "summary": {
            "document_id": document.document_id,
            "filename": document.metadata.filename,
            "status": document.status.value,
            "page_count": len(document.pages),
            "subject_count": len(document.subjects),
            "chapter_count": len(document.chapters),
            "pedagogical_element_count": len(document.pedagogical_elements),
            "paragraph_count": len(document.paragraphs),
            "chunk_count": len(document.chunks),
            "embedding_count": len(document.embeddings),
            "duration_seconds": document.pipeline_info.duration_seconds,
        },
        "pages": serialize_page(document),
        "subjects": serialize_subjects(document),
        "academic_context": serialize_academic_context(document),
        "chapters": serialize_chapters(document),
        "pedagogical_elements": serialize_pedagogical_elements(document),
        "paragraphs": serialize_paragraphs(document),
        "chunks": serialize_chunks(document),
        "embeddings": serialize_embeddings(document),
    }
