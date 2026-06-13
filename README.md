# TalentAlign

> AI-powered career-intelligence platform that analyzes a candidate resume
> against a job description and produces an explainable, multi-component
> fit assessment.

[![tests](https://img.shields.io/badge/tests-551%20passing-success)](Main/backend/tests/)
[![python](https://img.shields.io/badge/python-3.11-blue)](Main/backend/requirements.txt)
[![next.js](https://img.shields.io/badge/next.js-14.2-black)](Main/frontend/package.json)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Two services:

- **Backend** — FastAPI + Uvicorn + SBERT + (optional) Gemini 2.5 Flash
- **Frontend** — Next.js 14 (App Router) + Tailwind + Recharts dashboard

The deterministic SBERT pipeline is the primary scoring engine; Gemini
acts as a validation + narrative-enrichment layer and never writes skills
back into the matcher. When Gemini is unavailable the system degrades
gracefully — every `llm_*` field returns `None` and scores remain
identical to the baseline.

---

## Quick architecture

```
[Browser]
   │  HTTPS POST /analyze (multipart resume + JD text)
   ▼
[Frontend — Next.js dashboard]   ← Vercel
   │  fetch ${NEXT_PUBLIC_API_BASE_URL}/analyze
   ▼
[Backend — FastAPI]              ← Render / Fly.io / Cloud Run
   │
   ├─→ Resume parser → JD intelligence → Experience intel → Project intel
   ├─→ 6-layer skill matcher  (SBERT embeddings, all-MiniLM-L6-v2)
   ├─→ MW-ESE 6-component scoring  (9 domain weight profiles)
   └─→ (optional) Gemini enrichment + validation gate
           └─→ Candidate Assessment narrative, Strengths, Gaps, Hiring rec
```

**29-key analysis payload** delivered to the dashboard. Six screens:
Upload & Match · Match Overview · Component Alignment · Gap Analysis ·
Recommendations · Report & Export.

---

## Quick start (local dev)

### Backend

```bash
cd Main/backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cp .env.example .env       # then set GEMINI_API_KEY (optional)
uvicorn app.main:app --port 8000
```

Visit http://localhost:8000/health → expect `{"status":"ok", …}`.

### Frontend

```bash
cd Main/frontend
npm install
cp .env.example .env.local # NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Visit http://localhost:3000.

### Tests

```bash
cd Main/backend
LLM_BACKEND=none TALENTALIGN_EMBEDDING_BACKEND=tfidf pytest tests/ -q
# → 551 passed, 7 deselected (live Gemini), 0 warnings
```

---

## Repository layout

```
.
├── Main/
│   ├── backend/                  FastAPI service
│   │   ├── app/                  Source (services, utils, core, main.py)
│   │   ├── tests/                551 tests + fixtures + eval harness + reports
│   │   ├── scripts/              prewarm_sbert.py + smoke_test.sh
│   │   ├── Dockerfile            Production image (pre-warms SBERT at build)
│   │   ├── requirements.txt
│   │   ├── README.md             Backend deep-dive
│   │   └── BACKEND_AUDIT.md      Pre-UI payload contract audit
│   └── frontend/                 Next.js dashboard
│       ├── src/                  Source (app, components, hooks, lib, stores)
│       ├── package.json
│       ├── vercel.json
│       └── README.md             Frontend deep-dive
├── .github/workflows/ci.yml      Backend test suite on push + PR
├── DEPLOYMENT.md                 Production deployment runbook
├── README.md                     ← you are here
└── LICENSE                       MIT
```

Local-only (gitignored, not in the GitHub mirror): `Archive/`,
`node-portable/`, `.env`, build caches.

---

## Key features

- **Multi-source skill extraction** — explicit Skills section + certification
  inference + project mining + work-experience mining + full-text fallback
- **JD intelligence** — boilerplate filter, multi-domain detection,
  seniority detection, prioritized required/preferred/optional buckets
- **6-layer matching** — exact / alias / synonym / semantic / partial /
  cluster, with an optional LLM validation gate
- **MW-ESE 6-component scoring** — Skills, Projects, Internships, Work
  Experience, Academics, Achievements/Certifications, with JD-gating and
  proportional weight redistribution
- **Display normalization** — calibrated 0-100 curve across 54-pair baseline
- **Improvement simulation** — what-if uplift per missing skill + combined top-3
- **Explainability** — full transparency on match types, validation-gate
  decisions, gap impacts
- **Graceful LLM fallback** — full pipeline works without any LLM

---

## Deployment

The recommended path is **Render** (backend) + **Vercel** (frontend).

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for:
- Backend on Render with Docker (alternatives: Fly.io, Cloud Run)
- Frontend on Vercel (one-command CLI deploy)
- Environment variable cross-reference
- Post-deploy smoke test (`Main/backend/scripts/smoke_test.sh`)
- Common issues, rollback, Gemini tier sizing, key rotation
- Production-readiness checklist

---

## Configuration

### Backend env

| Variable | Default | Purpose |
|---|---|---|
| `LLM_BACKEND` | `gemini` if key set, else `none` | Backend selection |
| `GEMINI_API_KEY` or `GOOGLE_API_KEY` | — | Required for Gemini path |
| `TALENTALIGN_LLM_MODEL` | `gemini-2.5-flash` | Model override |
| `TALENTALIGN_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `TALENTALIGN_EMBEDDING_BACKEND` | auto cascade | Force `sbert` / `tfidf` / `token` |
| `TALENTALIGN_LLM_CACHE_DIR` | `.cache/talentalign-llm/` | LLM response disk cache |

Full reference in [`Main/backend/.env.example`](Main/backend/.env.example).

### Frontend env

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Backend origin |

See [`Main/frontend/.env.example`](Main/frontend/.env.example).

---

## License

[MIT](LICENSE) © 2026 Eklavya Singh Rathore

---

## Acknowledgments

- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`
- LLM: Google Gemini 2.5 Flash
- PDF/DOCX: PyMuPDF, python-docx
- NLP: spaCy
- Frontend: Next.js, Tailwind, Recharts, Framer Motion, Lucide
