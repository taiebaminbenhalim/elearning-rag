"""Point d'entrée principal de l'application.

Ce module ne contient aucune logique métier. Son unique rôle est
d'assembler les dépendances concrètes (injection de dépendances) et de
démarrer le traitement d'un PDF via le :class:`~core.pipeline.Pipeline`.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chunking import SemanticChunkerStrategy
from cleaning import BasicCleaningStrategy
from config import Config, load_config
from core import (
    ChapterDetector,
    ChunkBuilder,
    CleaningService,
    EmbeddingService,
    LevelDetector,
    OCRService,
    PDFLoader,
    ParagraphDetector,
    PedagogicalDetector,
    Pipeline,
    PipelineV2,
    StructureAnalyzer,
    StructureBuilder,
    SubjectDetector,
    Validator,
    VectorStoreService,
)
from embedding import BgeM3Model
from exceptions import PipelineError
from ocr import TesseractEngine
from pdf import ImageConverter, PDFReader
from utils import get_logger, load_json_dictionary
from vector_store import ChromaStore

logger = get_logger(__name__)


def _build_common_components(config: Config) -> dict[str, object]:
    """Construit les composants techniques partagés entre la V1 et la V2.

    Centralise l'instanciation des implémentations concrètes communes aux
    deux pipelines (lecture PDF, OCR, nettoyage, chunking, embedding,
    vector store), afin d'éviter toute duplication entre
    :func:`build_pipeline` (V1) et :func:`build_pipeline_v2` (V2).

    Args:
        config: Configuration globale du projet.

    Returns:
        Dictionnaire des composants construits, prêts à être injectés.
    """
    pdf_reader = PDFReader()
    image_converter = ImageConverter(
        output_dir=config.pdf.image_output_dir,
        zoom_factor=config.pdf.zoom_factor,
        image_format=config.pdf.image_format,
    )
    ocr_engine = TesseractEngine(
        apply_preprocessing=config.ocr.apply_preprocessing,
        tesseract_cmd=config.ocr.tesseract_cmd,
    )
    # Le modèle d'embedding est chargé une seule fois ici, puis partagé
    # entre EmbeddingService et la stratégie de chunking sémantique.
    embedding_model = BgeM3Model(
        device=config.embedding.device,
        normalize=config.embedding.normalize_embeddings,
        batch_size=config.embedding.batch_size,
    )
    chunker = SemanticChunkerStrategy(
        embedding_model=embedding_model,
        breakpoint_threshold_type=config.chunking.breakpoint_threshold_type,
        breakpoint_threshold_amount=config.chunking.breakpoint_threshold_amount,
    )
    vector_store = ChromaStore(persist_directory=config.vector_store.persist_directory)

    pdf_loader = PDFLoader(
        pdf_reader=pdf_reader,
        image_converter=image_converter,
        ocr_engine_name=ocr_engine.engine_name,
        embedding_model_name=embedding_model.model_name,
        chunking_strategy_name=chunker.strategy_name,
        pipeline_version=config.pipeline_version,
        default_language=config.ocr.language,
    )

    return {
        "pdf_loader": pdf_loader,
        "ocr_service": OCRService(ocr_engine=ocr_engine, language=config.ocr.language),
        "cleaning_service": CleaningService(cleaning_strategy=BasicCleaningStrategy()),
        "chunk_builder": ChunkBuilder(chunker=chunker, language=config.ocr.language),
        "embedding_service": EmbeddingService(embedding_model=embedding_model),
        "vector_store_service": VectorStoreService(
            vector_store=vector_store, collection_name=config.vector_store.collection_name
        ),
        "validator": Validator(),
    }


def build_pipeline(config: Config) -> Pipeline:
    """Construit le Pipeline complet V1 en injectant les implémentations concrètes.

    Conservé tel quel depuis la Version 1, pour garantir la
    rétrocompatibilité : ce pipeline ne comprend pas la structure
    pédagogique (matières, niveau, éléments pédagogiques), ajoutée en V2.

    Args:
        config: Configuration globale du projet.

    Returns:
        Une instance de :class:`~core.pipeline.Pipeline` (V1) prête à
        traiter un PDF.
    """
    components = _build_common_components(config)
    structure_analyzer = StructureAnalyzer()

    return Pipeline(
        pdf_loader=components["pdf_loader"],
        ocr_service=components["ocr_service"],
        cleaning_service=components["cleaning_service"],
        structure_analyzer=structure_analyzer,
        chunk_builder=components["chunk_builder"],
        embedding_service=components["embedding_service"],
        vector_store_service=components["vector_store_service"],
        validator=components["validator"],
    )


def build_pipeline_v2(config: Config) -> PipelineV2:
    """Construit le PipelineV2 complet en injectant toutes les implémentations concrètes.

    Ajoute, par rapport à :func:`build_pipeline` (V1), les nouveaux
    détecteurs de structure pédagogique (matières, niveau scolaire,
    chapitres pilotés par dictionnaire, éléments pédagogiques), pilotés
    par les dictionnaires JSON de référence chargés via
    ``config.dictionaries``.

    Args:
        config: Configuration globale du projet.

    Returns:
        Une instance de :class:`~core.pipeline_v2.PipelineV2` prête à
        traiter un PDF.
    """
    components = _build_common_components(config)

    subject_dictionary = load_json_dictionary(config.dictionaries.subject_detection_path)
    level_dictionary = load_json_dictionary(config.dictionaries.level_indicators_path)
    structure_dictionary = load_json_dictionary(config.dictionaries.structure_indicators_path)

    subject_detector = SubjectDetector(subject_dictionary=subject_dictionary)
    level_detector = LevelDetector(level_dictionary=level_dictionary)
    structure_builder = StructureBuilder(
        chapter_detector=ChapterDetector(structure_dictionary=structure_dictionary),
        pedagogical_detector=PedagogicalDetector(structure_dictionary=structure_dictionary),
        paragraph_detector=ParagraphDetector(),
    )

    return PipelineV2(
        pdf_loader=components["pdf_loader"],
        ocr_service=components["ocr_service"],
        cleaning_service=components["cleaning_service"],
        subject_detector=subject_detector,
        level_detector=level_detector,
        structure_builder=structure_builder,
        chunk_builder=components["chunk_builder"],
        embedding_service=components["embedding_service"],
        vector_store_service=components["vector_store_service"],
        validator=components["validator"],
    )


def main() -> int:
    """Analyse les arguments en ligne de commande et démarre le pipeline.

    Utilise le pipeline V2 (structure pédagogique) par défaut. L'option
    ``--v1`` permet d'exécuter l'ancien pipeline V1 pour comparaison ou
    diagnostic.

    Returns:
        Code de sortie du processus (0 en cas de succès, 1 en cas d'erreur).
    """
    parser = argparse.ArgumentParser(
        description="Transforme un PDF scolaire scanné en embeddings indexés dans ChromaDB."
    )
    parser.add_argument("--pdf", required=True, type=Path, help="Chemin du fichier PDF scanné à traiter.")
    parser.add_argument(
        "--v1",
        action="store_true",
        help="Utilise l'ancien pipeline V1 (sans détection de structure pédagogique).",
    )
    args = parser.parse_args()

    config = load_config()

    try:
        if args.v1:
            pipeline = build_pipeline(config)
        else:
            pipeline = build_pipeline_v2(config)
        document = pipeline.run(args.pdf)
    except PipelineError as exc:
        logger.error("Le traitement a échoué: %s", exc)
        return 1

    logger.info(
        "Traitement terminé avec succès. document_id=%s, pages=%d, matieres=%d, chapitres=%d, "
        "elements_pedagogiques=%d, paragraphes=%d, chunks=%d, embeddings=%d",
        document.document_id,
        len(document.pages),
        len(document.subjects),
        len(document.chapters),
        len(document.pedagogical_elements),
        len(document.paragraphs),
        len(document.chunks),
        len(document.embeddings),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
