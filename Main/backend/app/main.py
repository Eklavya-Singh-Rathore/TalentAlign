"""TalentAlign HTTP API (FastAPI).

Thin layer over the deterministic analysis pipeline:
  GET  /health    service + backend status
  POST /analyze   multipart resume (.pdf/.docx) + jd_text  ->  full payload

Input is validated at the boundary (backend-audit findings F1/F2): unreadable or
empty uploads return 4xx; a JD with no extractable requirements is flagged via a
``warnings`` field on the result. LLM enrichment is off by default (deterministic
byte-identical output); the heavy ``debug.full_debug_log`` is omitted unless
``include_debug=true``.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.services.analysis import analyze_resume_jd
from app.utils.embeddings import EmbeddingProvider, get_embedding_provider
from app.utils.llm import LLMProvider, get_llm_provider
from app.utils.file_handling import extract_text_from_docx, extract_text_from_pdf

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

app = FastAPI(title="TalentAlign API", version="1.0.0")

# CORS for the Next.js frontend (comma-separated origins; defaults to dev).
_origins = os.environ.get("TALENTALIGN_CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()] or ["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _get_provider() -> EmbeddingProvider:
    """Embedding provider for a request. An explicit backend can be forced via
    ``TALENTALIGN_EMBEDDING_BACKEND`` (e.g. ``tfidf`` for fast/deterministic
    tests); otherwise auto-select (SBERT → TF-IDF → token)."""
    backend = os.environ.get("TALENTALIGN_EMBEDDING_BACKEND", "").strip().lower()
    if backend:
        return EmbeddingProvider(backend=backend)
    return get_embedding_provider()


def _get_llm_provider() -> LLMProvider:
    return get_llm_provider()


def _read_upload_text(path: str, ext: str) -> str:
    return extract_text_from_pdf(path) if ext == ".pdf" else extract_text_from_docx(path)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "talentalign-api",
        "version": app.version,
        "embedding_backend": _get_provider().backend,
        "llm_backend": _get_llm_provider().backend,
    }


@app.post("/analyze")
async def analyze(
    resume: UploadFile = File(...),
    jd_text: str = Form(...),
    include_debug: bool = False,
) -> dict:
    # ── Validate JD ──────────────────────────────────────────────────────────
    if not jd_text or not jd_text.strip():
        raise HTTPException(status_code=422, detail="jd_text must be a non-empty string.")

    # ── Validate upload (extension, non-empty, size) ─────────────────────────
    ext = Path(resume.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail=f"Unsupported file type '{ext}'. Use .pdf or .docx.")
    data = await resume.read()
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 10 MB).")

    # ── Persist to a temp path (the pipeline expects a file path) ────────────
    tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
    tmp.write(data)
    tmp.close()
    try:
        # F1: confirm the file is actually readable before analysis, so a corrupt
        # upload returns 400 instead of a misleading 0% result.
        try:
            text = _read_upload_text(tmp.name, ext)
        except Exception:
            raise HTTPException(status_code=400, detail="Could not read the resume file (corrupt or unsupported content).")
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the resume.")
        try:
            result = analyze_resume_jd(tmp.name, jd_text, provider=_get_provider(), llm_provider=_get_llm_provider())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    # Trim the heavy debug log unless explicitly requested.
    if not include_debug and isinstance(result.get("debug"), dict):
        result["debug"].pop("full_debug_log", None)

    # F2: flag low-signal inputs rather than presenting a bare number.
    warnings: list[str] = []
    if int(result.get("debug", {}).get("jd_skill_count", 0)) == 0:
        warnings.append(
            "No skill requirements could be extracted from the job description; "
            "the score reflects non-skill components only."
        )
    if not result.get("resume_extraction", {}).get("sections_present"):
        warnings.append(
            "No structured sections were detected in the resume; extraction may be incomplete."
        )
    result["warnings"] = warnings
    return result
