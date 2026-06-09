# TalentAlign backend — production image
#
# Build:  docker build -t talentalign-backend .
# Run:    docker run --rm -p 8000:8000 \
#           -e GEMINI_API_KEY=... \
#           -e TALENTALIGN_CORS_ORIGINS=https://your-frontend.example.com \
#           talentalign-backend
#
# The SBERT model (all-MiniLM-L6-v2) is downloaded at build time via
# scripts/prewarm_sbert.py so cold-start does not stall the first request.

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf-cache \
    TRANSFORMERS_CACHE=/opt/hf-cache \
    SENTENCE_TRANSFORMERS_HOME=/opt/hf-cache \
    TALENTALIGN_LLM_CACHE_DIR=/var/cache/talentalign-llm

WORKDIR /app

# System deps (PyMuPDF needs libstdc++; spaCy model download needs ca-certificates)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# ── Python deps (separate layer for cache reuse) ─────────────────────────────
COPY requirements.txt ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    python -m spacy download en_core_web_sm

# ── Application source ──────────────────────────────────────────────────────
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY conftest.py pytest.ini ./

# ── Pre-warm SBERT model into HF_HOME ───────────────────────────────────────
# Bakes the all-MiniLM-L6-v2 weights into the image so first-request latency
# is ~50-200ms instead of 30-60s. Failure here aborts the build.
RUN python scripts/prewarm_sbert.py

# ── Runtime config ──────────────────────────────────────────────────────────
RUN mkdir -p "$TALENTALIGN_LLM_CACHE_DIR" && \
    chmod 755 "$TALENTALIGN_LLM_CACHE_DIR"

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
