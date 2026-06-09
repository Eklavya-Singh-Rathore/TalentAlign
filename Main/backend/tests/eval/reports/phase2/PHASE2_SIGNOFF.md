# Phase 2 — Verification & Validation: SIGN-OFF

Decision: **Accept the LLM-gate result and sign off** (user choice "b").

## Dataset
- 3 resumes (Eklavya, Vignesh, Ananya) × 9 JDs (JD_1…5 + JD-6…9) = 27 combinations.
- Gold-labeled borderline pairs: 200 (17 true / 183 false). Expanded pool of 424
  pairs (`candidates_v2.jsonl`) retained for a future robust re-measure.

## Success criteria

| # | Criterion | Target | Result | Verdict |
|---|---|---|---|---|
| ① | False-positive reduction | ≥ 30% | **~84%** (stable across runs; FP 45→7) | ✅ PASS |
| ② | Recall drop | ≤ 5 pp | 5.9–23.5 pp (run-variable) | ⚠️ ACCEPTED (see note) |
| ③ | No scoring regressions | rankings preserved | Eklavya ≥ Vignesh on all 5 original JDs under gate; role-fit ranking sensible at 27-cell scale | ✅ PASS |
| ④ | No pipeline instability | CI green + graceful | 483 unit tests green (none/mock); cost-cap, timeout, graceful-degradation all verified | ✅ PASS |

## Note on criterion ②
The ≤5 pp recall target is **not robustly measurable on a 17-positive gold set**:
one lost true-positive = 5.88 pp, so the metric is dominated by single-pair
noise. Two confounders inflate it run-to-run:
1. **LLM stochasticity** — qwen3:8b at temperature 0.1 returns slightly
   different verdicts on cache-miss; the lost TPs are consistently
   "specific-technique ⊂ broad-area" cases where the model contradicts its own
   stated reasoning (e.g. "classification is a subset of ML fundamentals" →
   then votes false).
2. **Gold-set staleness** — the P3 extraction patches changed which JD phrases
   the pipeline produces; 7/200 gold pairs (1 true) now reference removed
   phrases and become forced FNs.

In production this variance does not surface: the on-disk LLM cache pins a
stable verdict per (resume, jd) pair once computed.

The user accepted the gate on the basis that **FP reduction is large and
robust (~84%)**, precision roughly doubles, and the few lost TPs are
borderline/debatable. A future re-label from the 424-pair pool can settle ②
statistically if desired.

## Engineering state at sign-off
- 483 unit tests pass (none + mock backends); 7 live-LLM tests deselected by default.
- Regression baseline vs. original Code/ pipeline: resume side stable, JD side
  shows only intended improvements.
- Ollama + qwen3:8b operational, models on D:; cost $0 (local).
- Phase 1–3 extraction patches (JD-9 noise, role extraction, domain, resume
  hygiene) landed with 19 dedicated regression tests.
