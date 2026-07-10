# Plateforme RAG e-learning — Version 2

Transforme un PDF scolaire **scanné** en embeddings indexés dans ChromaDB,
en comprenant sa **structure pédagogique** (matières, niveau scolaire,
chapitres, éléments pédagogiques).

## Pipeline V2

```
PDF → PDFLoader → OCR (Tesseract) → Nettoyage
    → Détection des matières (SubjectDetector)
    → Détection du niveau scolaire (LevelDetector)
    → StructureBuilder :
          → Détection des chapitres (ChapterDetector)
          → Détection des éléments pédagogiques (PedagogicalDetector)
          → Détection des paragraphes (ParagraphDetector, logique V1 inchangée)
    → ChunkBuilder (SemanticChunker) → EmbeddingService (BAAI/bge-m3)
    → VectorStoreService (ChromaDB)
```

L'ancien pipeline V1 (`core/pipeline.py`, `core/structure_analyzer.py`)
reste disponible et testé tel quel (`python main.py --pdf ... --v1`),
pour comparaison ou diagnostic. Le pipeline V2 est un **superset** de la
V1 : il ne modifie aucun comportement existant, il ajoute la
compréhension de la structure pédagogique.

## Architecture

```
models/        Objets métier purs (dataclasses), aucune logique
                + V2 : Subject, AcademicContext, PedagogicalType, PedagogicalElement
core/          Services d'orchestration + interfaces (DIP)
                + V2 : SubjectDetector, LevelDetector, ChapterDetector,
                       PedagogicalDetector, ParagraphDetector, StructureBuilder,
                       PipelineV2
pdf/           Lecture PDF et conversion page → image (PyMuPDF, Pillow)
ocr/           Moteurs OCR (Tesseract en V1/V2)
cleaning/      Stratégies de nettoyage du texte OCR
chunking/      Stratégies de chunking (SemanticChunker en V1/V2)
embedding/     Modèles d'embedding (BAAI/bge-m3 en V1/V2)
vector_store/  Bases vectorielles (ChromaDB en V1/V2)
data/dictionaries/  Dictionnaires JSON de référence (V2) :
                     subject_detection.json, level_indicators.json,
                     structure_indicators.json
utils/         Logger, génération d'ID, chemins, texte, chargement JSON
exceptions/    Exceptions métier, une par étape du pipeline
api/           API FastAPI + interface de démonstration (V2), sans logique métier
tests/         Tests unitaires (models, core) et d'intégration (V1 et V2)
```

Les services de `core/` ne dépendent jamais d'une implémentation
technique concrète : ils dépendent des interfaces définies dans
`core/interfaces.py`, injectées au moment de la construction (voir
`main.build_pipeline` / `main.build_pipeline_v2`). Les nouveaux
détecteurs V2 sont pilotés par des dictionnaires JSON injectés (jamais de
chemin de fichier codé en dur dans un service), ce qui permet d'ajuster
la détection sans modifier le code.

**Règles métier V2 clés** :
- Une page appartient à une seule matière ; les pages consécutives de
  même matière sont regroupées en un seul `Subject`.
- `AcademicContext` (niveau, section, trimestre, année) est un objet
  séparé de `Metadata`.
- Un chapitre appartient toujours à une seule matière.
- Les chapitres ne sont détectés que lorsqu'ils existent : un document
  sans chapitre (ex: recueil d'examens) continue le pipeline normalement.
- Seuls 5 types d'éléments pédagogiques sont détectés (Cours, Exercice,
  Activité, Examen, Correction), sans granularité fine.
- Un élément pédagogique est rattaché à un chapitre, ou à défaut
  directement à une matière.

## Installation

### Windows

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

1. Installer Tesseract via l'installeur Windows : https://github.com/UB-Mannheim/tesseract/wiki
   (cocher le pack de langue **French** pendant l'installation).
2. Copier `.env.example` en `.env`, puis décommenter et adapter la ligne
   `TESSERACT_CMD` avec le chemin d'installation, ex :
   ```
   TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
   ```
   (nécessaire car Tesseract n'est pas automatiquement dans le PATH sous Windows)

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Installer Tesseract via le gestionnaire de paquets système
(`apt install tesseract-ocr tesseract-ocr-fra` sous Debian/Ubuntu,
`brew install tesseract tesseract-lang` sous macOS). Pas besoin de
`TESSERACT_CMD` si `tesseract` est déjà dans le PATH.

Copier `.env.example` en `.env` pour personnaliser la configuration
(langue OCR, modèle d'embedding, chemin de persistance ChromaDB,
chemins des dictionnaires V2, etc.).

## Utilisation en ligne de commande

```bash
python main.py --pdf chemin/vers/livre_scanne.pdf          # Pipeline V2 (par défaut)
python main.py --pdf chemin/vers/livre_scanne.pdf --v1     # Ancien pipeline V1
```

## Utilisation via l'API et l'interface de démonstration

```bash
uvicorn api.app:app --reload
```

Ouvrir `http://localhost:8000/` dans un navigateur pour l'interface de
démonstration (upload PDF, bouton de lancement, logs, onglets de
résultats : OCR, Matières, Niveau, Chapitres, Éléments pédagogiques,
Paragraphes, Chunks, Embeddings — vecteurs jamais affichés).

Ou directement via l'API :

```powershell
curl.exe -X POST http://localhost:8000/process -F "file=@livre_scanne.pdf"
```
```bash
curl -X POST http://localhost:8000/process -F "file=@livre_scanne.pdf"
```

## Tests

```bash
pytest -q
```

50 tests (unitaires V1/V2 sur `models/` et `core/`, intégration V1 et V2
bout en bout). Les tests utilisent des implémentations factices des
interfaces techniques (`tests/conftest.py`) mais les **vrais**
dictionnaires JSON de référence, et ne nécessitent donc pas Tesseract, le
modèle BGE-M3 ni ChromaDB pour s'exécuter.

## Hors périmètre de la V2

Dictionnaires spécialisés par matière (vocabulaire disciplinaire
approfondi), granularité fine des éléments pédagogiques (Exercice 1,
Question 2...), recherche hybride, génération via LLM, résumés,
flashcards, quiz, knowledge graph. Réservés aux versions ultérieures.
