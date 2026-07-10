"""API FastAPI + interface de démonstration du pipeline.

Ce module ne contient aucune logique métier : il se contente d'exposer le
`PipelineV2` (construit via `main.build_pipeline_v2`) au travers de
routes HTTP, et de servir une petite page HTML/JS permettant de
l'utiliser sans terminal. Toute la logique reste dans `core/`.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from api.log_capture import capture_logs
from api.serializers import serialize_document
from config import load_config
from exceptions import PipelineError
from main import build_pipeline_v2
from utils import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Plateforme RAG e-learning - API V2")

_config = load_config()
_pipeline = build_pipeline_v2(_config)


@app.get("/health")
def health() -> dict[str, str]:
    """Vérifie que l'API est opérationnelle.

    Returns:
        Un dictionnaire indiquant le statut de l'API.
    """
    return {"status": "ok"}


@app.post("/process")
async def process_pdf(file: UploadFile = File(...)) -> dict[str, object]:
    """Traite un PDF scanné à travers le pipeline V2 complet.

    Args:
        file: Fichier PDF envoyé en upload.

    Returns:
        Le document traité, entièrement sérialisé (résumé, pages/OCR,
        matières, contexte académique, chapitres, éléments pédagogiques,
        paragraphes, chunks, métadonnées des embeddings), ainsi que les
        logs capturés pendant le traitement.

    Raises:
        HTTPException: Code 400 si le fichier est absent/vide, code 500 si
            le pipeline échoue.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Un fichier PDF est requis")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / file.filename
        with tmp_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            with capture_logs() as logs:
                document = _pipeline.run(tmp_path)
        except PipelineError as exc:
            logger.error("Echec du traitement de %s: %s", file.filename, exc)
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    result = serialize_document(document)
    result["logs"] = logs
    return result


@app.get("/", response_class=HTMLResponse)
def demo_ui() -> str:
    """Sert la page HTML de l'interface de démonstration.

    Returns:
        Le HTML complet de la page (CSS et JS intégrés, aucune dépendance
        externe autre que le navigateur).
    """
    return _DEMO_HTML


_DEMO_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Plateforme RAG e-learning - Demo</title>
<style>
  body { font-family: system-ui, sans-serif; margin: 0; background: #f5f6f8; color: #1c1e21; }
  header { background: #1c1e21; color: white; padding: 1rem 2rem; }
  header h1 { margin: 0; font-size: 1.25rem; }
  main { max-width: 1000px; margin: 2rem auto; padding: 0 1rem; }
  .panel { background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }
  .row { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
  input[type=file] { flex: 1; }
  button { background: #2563eb; color: white; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; cursor: pointer; font-size: 0.95rem; }
  button:disabled { background: #9ca3af; cursor: not-allowed; }
  #status { font-size: 0.9rem; color: #555; margin-top: 0.5rem; }
  .spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #ccc; border-top-color: #2563eb; border-radius: 50%; animation: spin 0.8s linear infinite; vertical-align: middle; margin-right: 6px; }
  @keyframes spin { to { transform: rotate(360deg); } }
  #logs { background: #0f172a; color: #cbd5e1; font-family: monospace; font-size: 0.8rem; padding: 1rem; border-radius: 6px; max-height: 200px; overflow-y: auto; white-space: pre-wrap; }
  .tabs { display: flex; gap: 0.25rem; flex-wrap: wrap; border-bottom: 1px solid #e5e7eb; margin-bottom: 1rem; }
  .tab { padding: 0.5rem 0.9rem; cursor: pointer; border-radius: 6px 6px 0 0; font-size: 0.9rem; color: #555; }
  .tab.active { background: #2563eb; color: white; }
  .tab-content { display: none; }
  .tab-content.active { display: block; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th, td { text-align: left; padding: 0.4rem 0.5rem; border-bottom: 1px solid #eee; vertical-align: top; }
  .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; }
  .stat { background: #f1f5f9; border-radius: 6px; padding: 0.75rem; }
  .stat .value { font-size: 1.4rem; font-weight: 700; }
  .stat .label { font-size: 0.75rem; color: #64748b; }
  .badge { display: inline-block; background: #e0e7ff; color: #3730a3; border-radius: 4px; padding: 0.1rem 0.4rem; font-size: 0.75rem; margin-right: 0.25rem; }
  .empty { color: #888; font-style: italic; }
</style>
</head>
<body>
<header><h1>Plateforme RAG e-learning - Interface de demonstration (V2)</h1></header>
<main>
  <div class="panel">
    <div class="row">
      <input type="file" id="pdfInput" accept="application/pdf">
      <button id="runButton" onclick="runPipeline()">Lancer le traitement</button>
    </div>
    <div id="status"></div>
    <div id="logs" style="margin-top:1rem; display:none;"></div>
  </div>

  <div class="panel" id="resultsPanel" style="display:none;">
    <div class="tabs" id="tabs"></div>
    <div id="tabContents"></div>
  </div>
</main>

<script>
const TABS = [
  {id: "summary", label: "Resume"},
  {id: "pages", label: "OCR"},
  {id: "subjects", label: "Matieres"},
  {id: "academic_context", label: "Niveau"},
  {id: "chapters", label: "Chapitres"},
  {id: "pedagogical_elements", label: "Elements pedagogiques"},
  {id: "paragraphs", label: "Paragraphes"},
  {id: "chunks", label: "Chunks"},
  {id: "embeddings", label: "Embeddings"},
];

function setStatus(html) {
  document.getElementById("status").innerHTML = html;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

async function runPipeline() {
  const input = document.getElementById("pdfInput");
  const button = document.getElementById("runButton");
  const logsDiv = document.getElementById("logs");

  if (!input.files.length) {
    setStatus('<span style="color:#b91c1c;">Choisissez un fichier PDF avant de lancer le traitement.</span>');
    return;
  }

  button.disabled = true;
  logsDiv.style.display = "none";
  document.getElementById("resultsPanel").style.display = "none";
  setStatus('<span class="spinner"></span> Traitement en cours (OCR, detection de structure, embeddings)... cela peut prendre un moment.');

  const formData = new FormData();
  formData.append("file", input.files[0]);

  try {
    const response = await fetch("/process", { method: "POST", body: formData });
    const data = await response.json();

    if (!response.ok) {
      setStatus('<span style="color:#b91c1c;">Erreur : ' + escapeHtml(data.detail || "traitement echoue") + '</span>');
      return;
    }

    setStatus('<span style="color:#15803d;">Traitement termine en ' + (data.summary.duration_seconds || 0).toFixed(2) + 's.</span>');

    if (data.logs && data.logs.length) {
      logsDiv.textContent = data.logs.join("\\n");
      logsDiv.style.display = "block";
    }

    renderResults(data);
  } catch (err) {
    setStatus('<span style="color:#b91c1c;">Erreur reseau : ' + escapeHtml(err.message) + '</span>');
  } finally {
    button.disabled = false;
  }
}

function renderResults(data) {
  const tabsEl = document.getElementById("tabs");
  const contentsEl = document.getElementById("tabContents");
  tabsEl.innerHTML = "";
  contentsEl.innerHTML = "";

  TABS.forEach((tab, index) => {
    const tabButton = document.createElement("div");
    tabButton.className = "tab" + (index === 0 ? " active" : "");
    tabButton.textContent = tab.label;
    tabButton.onclick = () => selectTab(tab.id);
    tabButton.id = "tabbtn-" + tab.id;
    tabsEl.appendChild(tabButton);

    const content = document.createElement("div");
    content.className = "tab-content" + (index === 0 ? " active" : "");
    content.id = "tabcontent-" + tab.id;
    content.innerHTML = renderTab(tab.id, data);
    contentsEl.appendChild(content);
  });

  document.getElementById("resultsPanel").style.display = "block";
}

function selectTab(tabId) {
  TABS.forEach(tab => {
    document.getElementById("tabbtn-" + tab.id).classList.toggle("active", tab.id === tabId);
    document.getElementById("tabcontent-" + tab.id).classList.toggle("active", tab.id === tabId);
  });
}

function renderTab(tabId, data) {
  switch (tabId) {
    case "summary": return renderSummary(data.summary);
    case "pages": return renderPages(data.pages);
    case "subjects": return renderSubjects(data.subjects);
    case "academic_context": return renderAcademicContext(data.academic_context);
    case "chapters": return renderChapters(data.chapters);
    case "pedagogical_elements": return renderPedagogicalElements(data.pedagogical_elements);
    case "paragraphs": return renderParagraphs(data.paragraphs);
    case "chunks": return renderChunks(data.chunks);
    case "embeddings": return renderEmbeddings(data.embeddings);
    default: return "";
  }
}

function renderSummary(summary) {
  const stats = [
    ["Document", summary.filename],
    ["Pages", summary.page_count],
    ["Matieres", summary.subject_count],
    ["Chapitres", summary.chapter_count],
    ["Elements pedagogiques", summary.pedagogical_element_count],
    ["Paragraphes", summary.paragraph_count],
    ["Chunks", summary.chunk_count],
    ["Embeddings", summary.embedding_count],
    ["Duree (s)", summary.duration_seconds ? summary.duration_seconds.toFixed(2) : "-"],
    ["Statut", summary.status],
  ];
  return '<div class="summary-grid">' + stats.map(([label, value]) =>
    '<div class="stat"><div class="value">' + escapeHtml(String(value)) + '</div><div class="label">' + escapeHtml(label) + '</div></div>'
  ).join("") + '</div>';
}

function renderPages(pages) {
  if (!pages.length) return '<p class="empty">Aucune page.</p>';
  return pages.map(p =>
    '<h4>Page ' + p.page_number + ' (confiance OCR: ' + (p.mean_confidence !== null ? p.mean_confidence.toFixed(1) : "-") + ')</h4>' +
    '<pre style="white-space:pre-wrap;background:#f8fafc;padding:0.75rem;border-radius:6px;">' + escapeHtml(p.raw_text) + '</pre>'
  ).join("");
}

function renderSubjects(subjects) {
  if (!subjects.length) return '<p class="empty">Aucune matiere detectee.</p>';
  return '<table><tr><th>Matiere</th><th>Pages</th><th>Confiance</th></tr>' +
    subjects.map(s => '<tr><td>' + escapeHtml(s.name) + '</td><td>' + s.page_numbers.join(", ") + '</td><td>' + s.confidence + '</td></tr>').join("") +
    '</table>';
}

function renderAcademicContext(ctx) {
  const rows = [["Niveau", ctx.level], ["Section", ctx.section], ["Trimestre", ctx.trimester], ["Annee scolaire", ctx.school_year], ["Confiance", ctx.confidence]];
  return '<table>' + rows.map(([label, value]) =>
    '<tr><th>' + label + '</th><td>' + (value !== null && value !== undefined ? escapeHtml(String(value)) : '<span class="empty">non detecte</span>') + '</td></tr>'
  ).join("") + '</table>';
}

function renderChapters(chapters) {
  if (!chapters.length) return '<p class="empty">Aucun chapitre detecte (document sans chapitres, ex: recueil d\\'examens).</p>';
  return '<table><tr><th>#</th><th>Titre</th><th>Pages</th><th>Paragraphes</th></tr>' +
    chapters.map(c => '<tr><td>' + c.number + '</td><td>' + escapeHtml(c.title) + '</td><td>' + c.page_numbers.join(", ") + '</td><td>' + c.paragraph_count + '</td></tr>').join("") +
    '</table>';
}

function renderPedagogicalElements(elements) {
  if (!elements.length) return '<p class="empty">Aucun element pedagogique detecte.</p>';
  return '<table><tr><th>Type</th><th>Pages</th><th>Rattachement</th><th>Confiance</th></tr>' +
    elements.map(e => '<tr><td><span class="badge">' + e.type + '</span></td><td>' + e.page_numbers.join(", ") +
      '</td><td>' + (e.chapter_id ? "chapitre" : (e.subject_id ? "matiere" : "-")) + '</td><td>' + e.confidence + '</td></tr>').join("") +
    '</table>';
}

function renderParagraphs(paragraphs) {
  if (!paragraphs.length) return '<p class="empty">Aucun paragraphe detecte.</p>';
  return paragraphs.map(p =>
    '<div style="margin-bottom:0.75rem;padding:0.5rem;background:#f8fafc;border-radius:6px;"><small>pages ' + p.page_numbers.join(", ") + '</small><p style="margin:0.25rem 0 0;">' + escapeHtml(p.text) + '</p></div>'
  ).join("");
}

function renderChunks(chunks) {
  if (!chunks.length) return '<p class="empty">Aucun chunk genere.</p>';
  return chunks.map(c =>
    '<div style="margin-bottom:0.75rem;padding:0.5rem;background:#f8fafc;border-radius:6px;">' +
    '<small>chunk #' + c.chunk_index + ' - ' + c.word_count + ' mots - pages ' + c.page_numbers.join(", ") + ' - methode: ' + c.creation_method + '</small>' +
    '<p style="margin:0.25rem 0 0;">' + escapeHtml(c.text) + '</p></div>'
  ).join("");
}

function renderEmbeddings(embeddings) {
  if (!embeddings.length) return '<p class="empty">Aucun embedding genere.</p>';
  return '<table><tr><th>Chunk</th><th>Modele</th><th>Dimension</th><th>Normalise</th><th>Cree le</th></tr>' +
    embeddings.map(e => '<tr><td>' + e.chunk_id.slice(0, 8) + '...</td><td>' + escapeHtml(e.model_name) + '</td><td>' + e.dimension + '</td><td>' + (e.normalized ? "oui" : "non") + '</td><td>' + escapeHtml(e.created_at) + '</td></tr>').join("") +
    '</table><p style="color:#888;font-size:0.8rem;">Les vecteurs (1024 valeurs par embedding) ne sont volontairement pas affiches.</p>';
}
</script>
</body>
</html>
"""
