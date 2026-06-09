# TalentAlign — Deployment Runbook

End-to-end guide for taking `TalentAlign_v2_Final_PreDeployment.zip` from
local-verified to production-running. Covers a recommended path
(Render for backend, Vercel for frontend) plus tested fallback options.

> Pre-flight checklist: all 22 audit findings closed, 551 unit tests
> passing, Phase 27 SBERT 54/54, Gemini integration verified live. See
> `TalentAlign_Pre-Structure_Audit_Report.md` for the full record.

---

## 1. Architecture recap

```
[Browser]
   │
   ▼
[Vercel — Next.js dashboard]   NEXT_PUBLIC_API_BASE_URL → backend origin
   │ HTTPS POST /analyze (multipart)
   ▼
[Backend host — FastAPI + uvicorn]   Gemini 2.5 Flash via httpx
   │       │
   │       ▼ (optional)
   │   [Google Generative Language API]
   ▼
[SBERT (all-MiniLM-L6-v2) — bundled in container]
```

Two services, one external dependency (Gemini). The backend container ships
with the SBERT model pre-warmed (via `scripts/prewarm_sbert.py` run at build
time in the `Dockerfile`).

---

## 2. Prerequisites

| | What you need | Why |
|---|---|---|
| **Accounts** | Gemini API key (paid tier strongly recommended) | Free tier hits 429 on a 54-pair sweep — see §9 |
| | Vercel account | Frontend hosting |
| | Backend host account (Render / Fly.io / Railway / Cloud Run) | FastAPI hosting — pick one |
| | GitHub or GitLab repo (optional but recommended) | Push the unzipped contents for git-driven deploys |
| **Local CLIs** | `docker` (for local container test) | Build + run the backend image to confirm before push |
| | `vercel` CLI (optional) | One-command frontend deploy |
| | `gh` or `git` | Repo push |

Minimum container requirements for the backend:
- **CPU:** 1 vCPU minimum, 2 recommended (SBERT encoding is the bottleneck)
- **RAM:** 1 GB minimum, 2 GB recommended (SBERT model ≈ 90 MB, spaCy ≈ 50 MB, Python runtime + safety margin)
- **Disk:** 1 GB (image + caches)
- **Egress:** outbound HTTPS to `generativelanguage.googleapis.com`

---

## 3. Backend — recommended: Render with Docker

Render auto-detects the `Dockerfile`, builds, runs.

### 3.1 Push to git
```bash
unzip TalentAlign_v2_Final_PreDeployment.zip
cd Main/backend
git init && git add . && git commit -m "TalentAlign backend v2"
git remote add origin <your-repo-url>
git push -u origin main
```

### 3.2 Create the Render service
1. Render Dashboard → **New** → **Web Service**
2. Connect the repo, point at `Main/backend/`
3. **Environment:** Docker
4. **Dockerfile path:** `Dockerfile` (repo root if Main/backend was pushed alone, else `Main/backend/Dockerfile`)
5. **Plan:** Starter ($7/mo, 512 MB) is borderline — Standard ($25/mo, 2 GB) recommended
6. **Health check path:** `/health`
7. **Environment variables:**

   | Key | Value | Notes |
   |---|---|---|
   | `GEMINI_API_KEY` | `AIza…` (your key) | **Secret** — Render UI marks it as such |
   | `LLM_BACKEND` | `gemini` | Or `none` to deploy SBERT-only first |
   | `TALENTALIGN_CORS_ORIGINS` | `https://<your-vercel-app>.vercel.app` | Comma-separate multiple — add `https://*.vercel.app` for preview deploys |
   | `TALENTALIGN_LLM_CACHE_DIR` | `/var/cache/talentalign-llm` | Already set in Dockerfile; keep |
   | `PORT` | `8000` | Render auto-binds this — Dockerfile listens on 8000 |

8. **Persistent disk** (recommended): 1 GB at `/var/cache/talentalign-llm` so the Gemini response cache survives deploys.

### 3.3 First deploy
- Initial build is ~5 min (SBERT pre-warm + spaCy model download)
- `/health` returns `{"status":"ok","llm_backend":"gemini"}` once ready
- Subsequent deploys are ~1-2 min (Docker layer cache)

### 3.4 Alternative: Fly.io
```bash
cd Main/backend
fly launch --dockerfile Dockerfile --name talentalign-backend
fly secrets set GEMINI_API_KEY=... TALENTALIGN_CORS_ORIGINS=https://your-app.vercel.app
fly deploy
```
Pre-built `fly.toml` not included — Fly's interactive `launch` generates it.

### 3.5 Alternative: Google Cloud Run
```bash
gcloud builds submit --tag gcr.io/<project>/talentalign-backend Main/backend
gcloud run deploy talentalign-backend \
  --image gcr.io/<project>/talentalign-backend \
  --set-env-vars LLM_BACKEND=gemini,TALENTALIGN_CORS_ORIGINS=https://your-app.vercel.app \
  --set-secrets GEMINI_API_KEY=projects/<project>/secrets/gemini-key:latest \
  --memory 2Gi --cpu 2 --port 8000 --allow-unauthenticated
```

---

## 4. Frontend — Vercel

### 4.1 With the Vercel CLI
```bash
cd Main/frontend
npm install
vercel link        # connect to Vercel project (or vercel deploy --prod for first-time)
vercel env add NEXT_PUBLIC_API_BASE_URL production
# Paste: https://<your-render-app>.onrender.com
vercel --prod
```

### 4.2 With the Vercel dashboard (no CLI)
1. **Import Project** → connect git repo
2. **Root directory:** `Main/frontend`
3. **Framework preset:** Next.js (auto-detected, `vercel.json` is included)
4. **Environment variables:**

   | Key | Value | Environment |
   |---|---|---|
   | `NEXT_PUBLIC_API_BASE_URL` | `https://<backend-origin>` | Production (+ Preview if you want) |

5. **Deploy** → Vercel builds, gives you `https://<app-name>.vercel.app`

### 4.3 Loop back to backend
Once you know the Vercel URL, update the backend's `TALENTALIGN_CORS_ORIGINS` to include it and redeploy. **Without this the dashboard's analyze button will fail with CORS errors.**

---

## 5. Environment variable cross-reference

| Variable | Backend | Frontend | Vercel | Render |
|---|---|---|---|---|
| `GEMINI_API_KEY` | ✅ required | — | — | Set as secret |
| `LLM_BACKEND` | ✅ recommended | — | — | `gemini` / `none` |
| `TALENTALIGN_CORS_ORIGINS` | ✅ required | — | — | Include Vercel domain |
| `TALENTALIGN_LLM_CACHE_DIR` | optional | — | — | `/var/cache/talentalign-llm` |
| `TALENTALIGN_EMBEDDING_BACKEND` | optional | — | — | leave unset (default cascade) |
| `NEXT_PUBLIC_API_BASE_URL` | — | ✅ required | Set in Project settings | — |
| `TALENTALIGN_LLM_COST_CAP` | optional | — | — | default `0.10` |
| `TALENTALIGN_LLM_TIMEOUT` | optional | — | — | default `15` |

The complete env reference is in `Main/backend/.env.example`.

---

## 6. Post-deployment smoke test

After both services are live, run:
```bash
BACKEND=https://<backend>.onrender.com \
FRONTEND=https://<app>.vercel.app \
bash Main/backend/scripts/smoke_test.sh
```

The script:
1. Hits `/health` — expects `{"status":"ok", "llm_backend":"gemini"}`
2. Hits `/analyze` with a small fixture (Eklavya × JD-1) — expects 200, 29 payload keys, score 60-75
3. Confirms the frontend root returns 200 + the expected title
4. Verifies CORS by simulating a preflight from the frontend origin

Exit code 0 → green; non-zero → see stderr output.

---

## 7. Common issues

| Symptom | Likely cause | Fix |
|---|---|---|
| Frontend `/analyze` → CORS error in browser console | `TALENTALIGN_CORS_ORIGINS` doesn't include the Vercel domain | Add it on the backend, redeploy |
| Frontend `/analyze` → 502/timeout | Backend cold start (Render free tier sleeps) | Upgrade plan, or accept the first-call latency |
| `/analyze` → 400 "Could not read the resume file" | Upload format not PDF/DOCX or corrupt | Check extension + content |
| `/analyze` → 413 "File too large" | Upload > 10 MB | Compress, or raise `MAX_UPLOAD_BYTES` in `app/main.py:29` + CDN limits |
| `/health` shows `llm_backend: "none"` | `GEMINI_API_KEY` not set in runtime env | Set the secret and redeploy |
| Backend logs flooded with `Gemini 4xx: 429` | Free-tier rate limit | Upgrade Gemini tier — see §9 |
| Backend logs `Gemini 4xx: 401` | Invalid / revoked API key | Rotate the key, set the new one as a secret |
| Backend logs `SKIP_SCHEMA_FAILURE` repeatedly | Model returned non-conforming JSON twice in a row | Usually transient; investigate by enabling debug log with `?include_debug=true` |
| Vercel build fails | Wrong root dir (must be `Main/frontend`) | Reconfigure Project Root in Vercel UI |
| `tsc --noEmit` errors in CI | Stale `next-env.d.ts` | Delete and let `next build` regenerate it |

---

## 8. Rollback

### Backend (Render)
- **Render Dashboard → Deploys → previous deploy → "Redeploy"**
- Or set image tag to the previous SHA if you tagged deploys

### Frontend (Vercel)
- **Vercel Dashboard → Deployments → previous deployment → "Promote to Production"**
- Instant — Vercel preserves all prior builds

### Combined rollback
- Roll the backend first, then the frontend — that way the frontend never points at an incompatible backend payload contract.

---

## 9. Gemini API tier sizing

| Free tier (`gemini-2.5-flash`) | Paid Tier 1 |
|---|---|
| ~10 RPM | 1,000 RPM |
| 1,500 RPD | unlimited (within billing cap) |
| Cost: $0 | $0.075 / 1 M input tokens, $0.30 / 1 M output tokens (as of 2026-06) |

**Per `/analyze` call cost** (typical Eklavya × JD-1): ~5,000 in + ~2,000 out tokens (rough — varies with JD length and project count) ≈ **$0.001** per analysis. 1,000 analyses ≈ $1.

**Phase 27 54-pair sweep:** ~540 API calls × ~0.001 = **~$0.50**. Practical on paid tier in ~3 minutes.

Cost cap is enforced in `LLMProvider` (`TALENTALIGN_LLM_COST_CAP`, default $0.10). Bump to $1+ for the Phase 27 sweep.

---

## 10. Key rotation

```bash
# 1. Generate a new key in Google AI Studio
# 2. Update the secret in your backend host:
#    Render → Environment → GEMINI_API_KEY → edit → save (auto-redeploys)
# 3. Old key continues to work until you delete it in Google AI Studio
# 4. Verify the new key is live: curl https://<backend>/health
# 5. Delete the old key in Google AI Studio
```

The LLM disk cache (under `TALENTALIGN_LLM_CACHE_DIR`) is keyed by
SHA-256(model, system, user, schema_name) — **not by API key**. Rotating the
key does not invalidate cached responses.

---

## 11. Production-readiness checklist

Run through before going live:

- [ ] Backend `/health` returns `llm_backend: "gemini"`
- [ ] Frontend loads at the Vercel domain, no console errors
- [ ] `/analyze` returns 200 + populated `final_summary.strengths` (proves Gemini path)
- [ ] CORS preflight from Vercel domain succeeds (smoke test verifies)
- [ ] Backend logs show no recurring 429/401/SCHEMA_FAILURE
- [ ] `TALENTALIGN_LLM_CACHE_DIR` is on a persistent disk (Render disk or equivalent)
- [ ] File-upload limit enforced (test with a 15 MB file → expect 413)
- [ ] Backend healthcheck wired to host's monitoring (Render does this automatically)
- [ ] Both API keys rotated since the dev key shared with Claude during this session

---

## 12. Operations

### Logs
- **Render:** Dashboard → Logs (real-time stream)
- **Vercel:** Dashboard → Deployments → Functions / Logs
- The backend logs `LLM transport error:` lines on retry; this is informational, not a failure unless `SKIP_*` counters in the `LLMUsage` start climbing.

### Cost monitoring
- Google AI Studio → Billing → set budget alerts at $5, $10, $25
- Render: Dashboard → Billing → set alerts

### Cache warming
- After deploy, hit `/analyze` once with Eklavya × JD-1 (or any pair) to populate the Gemini cache and SBERT model warmth.

---

## 13. What this runbook does NOT cover

- **Authentication / authorization:** the API is currently unauthenticated. For production, add API key auth or JWT — the FastAPI layer is the right place.
- **Rate limiting:** the backend itself has no rate limit. Render/Vercel give you basic IP throttling; consider a CDN/WAF (Cloudflare) for real protection.
- **Database:** there is no database. Analysis history lives in browser localStorage. Adding persistence is a separate feature.
- **Multi-tenancy:** all callers share the same Gemini quota and cache. Per-tenant isolation is a future feature.
- **Observability:** logs only. No Prometheus/OpenTelemetry. Add when traffic justifies it.

These are documented in the audit report's §11.5 as deferred items.
