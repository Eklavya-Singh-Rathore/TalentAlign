# TalentAlign — AI-Powered Career Intelligence System (Backend)

TalentAlign analyzes a candidate's resume against a job description and
produces a structured, explainable fit assessment: skill matching, gap
analysis, experience and project intelligence, and LLM-validated
recommendations.

> Formerly **CPPS (Campus Placement Prediction System)** — renamed to
> **TalentAlign: AI-Powered Career Intelligence System**.

## Architecture

```
Resume / JD
  → Parsing & extraction        (app/services/resume_parser, jd_parser/)
  → JD Intelligence             (app/services/jd_intelligence)
  → Experience Intelligence     (app/services/experience_intelligence)
  → Project Intelligence        (app/services/project_intelligence)
  → SBERT skill matching        (app/services/skill_matcher + app/utils/embeddings)
  → LLM validation + enrichment (app/utils/llm — Gemini 2.5 Flash primary, SBERT fallback)
  → Explainability              (app/services/explainability)
  → Analysis orchestrator       (app/services/analysis → 29-key payload)
```

The deterministic pipeline (SBERT + scoring) is the primary engine; the LLM
acts as a validation + narrative-enrichment layer and never writes skills
back into the matcher. When the LLM is unavailable the system degrades
gracefully — every `llm_*` field becomes `None` and scores remain identical
to the baseline.

## Layout

| Path | Purpose |
|------|---------|
| `app/main.py` | FastAPI HTTP entry (`/health`, `/analyze`) |
| `app/services/` | Pipeline stages (parsing, intelligence engines, matcher, explainability) |
| `app/utils/` | Shared primitives: embeddings, LLM provider, skill normalization, text/file handling |
| `app/core/` | Config loading (`weight_config.json`) |
| `tests/` | Unit tests, fixtures, evaluation + regression harnesses |

## Environment variables

A complete template is available in [`.env.example`](.env.example). Highlights:

| Variable | Purpose |
|----------|---------|
| `LLM_BACKEND` | `gemini` (default when key set) · `mock` · `none` |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Gemini auth — required when `LLM_BACKEND=gemini` |
| `TALENTALIGN_LLM_MODEL` | Override (default `gemini-2.5-flash`) |
| `TALENTALIGN_LLM_CACHE_DIR` | On-disk LLM response cache (default `.cache/talentalign-llm/`) |
| `TALENTALIGN_LLM_TIMEOUT`, `TALENTALIGN_LLM_COST_CAP` | Per-call timeout / per-analysis cost cap |
| `TALENTALIGN_LLM_VALIDATE_LOW/HIGH/TIERS` | Match-validation gate tuning |
| `TALENTALIGN_EMBEDDING_BACKEND` | Force `sbert` / `tfidf` / `token` (default: auto cascade) |
| `TALENTALIGN_CORS_ORIGINS` | Comma-separated allowed origins (default `http://localhost:3000`) |
| `TALENTALIGN_WEIGHT_CONFIG_PATH` | Override weight-config path |
| `GROQ_API_KEY` | Optional Groq backend (`LLM_BACKEND=groq`) |

## Running locally

```bash
# Install deps
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Tests (deterministic; LLM=none, embeddings=tfidf for speed)
LLM_BACKEND=none TALENTALIGN_EMBEDDING_BACKEND=tfidf pytest tests/ -q

# Live LLM tests (requires GEMINI_API_KEY)
LLM_BACKEND=gemini pytest tests/ -m live_llm

# Regression baseline
python tests/regression_baseline.py

# 54-pair eval matrix
python tests/eval_matrix_54.py
```

## API

```bash
# Health
curl http://localhost:8000/health

# Analyze (multipart resume + JD text)
curl -X POST http://localhost:8000/analyze \
  -F "resume=@path/to/resume.pdf" \
  -F "jd_text=<path/to/jd.txt"
```

The response is a 29-key analysis payload; see `BACKEND_AUDIT.md` for the
field contract.

## Deployment

The backend is a FastAPI app served by Uvicorn. Required production config:

| Setting | Value |
|---------|-------|
| Process | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| `GEMINI_API_KEY` | Set in the runtime env, never in code |
| `TALENTALIGN_CORS_ORIGINS` | Comma-separated production frontend origins |
| `TALENTALIGN_LLM_CACHE_DIR` | Writable persistent path (or scratch — degrades to in-process LRU) |
| File upload limit | 10 MB enforced in [`main.py:29`](app/main.py) — also confirm at any CDN/proxy in front |

### Docker

A [`Dockerfile`](Dockerfile) is included. It pre-warms the SBERT model
(`all-MiniLM-L6-v2`) at build time via
[`scripts/prewarm_sbert.py`](scripts/prewarm_sbert.py) so the first user
request does not pay the ~30–60s download cold start.

```bash
docker build -t talentalign-backend .
docker run --rm -p 8000:8000 \
  -e GEMINI_API_KEY=... \
  -e TALENTALIGN_CORS_ORIGINS=https://your-frontend.example.com \
  talentalign-backend
```

### Pre-warming without Docker

If you're deploying via a managed platform without build-time control,
run `python scripts/prewarm_sbert.py` once after `pip install` and the
weights will be cached under `HF_HOME` / `SENTENCE_TRANSFORMERS_HOME`.
Mount that directory on a persistent volume so it survives restarts.

## Models
- **LLM (primary):** Gemini 2.5 Flash via the Generative Language REST API.
- **LLM (fallback):** none — pipeline degrades to deterministic SBERT-only.
- **Embeddings:** SBERT (`all-MiniLM-L6-v2`) → TF-IDF → token fallback.
