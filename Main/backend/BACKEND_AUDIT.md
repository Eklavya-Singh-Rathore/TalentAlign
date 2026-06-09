# TalentAlign — Final Backend Audit (pre-UI)

Audit of the deterministic backend before the UI phase. Scope: the
`analyze_resume_jd` payload contract, determinism, error/edge-case handling, and
a known-limitations register. **543 tests passing** (`pytest tests/ -q`,
`LLM_BACKEND=none`).

---

## 1. Payload contract (`analyze_resume_jd`)

The orchestrator `analyze_resume_jd()` returns a dict with **28 top-level
keys**. The FastAPI `/analyze` route adds a 29th key (`warnings`) for low-
signal-input flagging, for a **29-key total over the wire**. Types verified
by audit probe (Eklavya × JD_1, TF-IDF provider).

### Scores & headline
| Key | Type | Notes |
|---|---|---|
| `placement_score` | float | **Normalized display score 0–100** (UI headline) |
| `placement_score_raw_pct` | float | Raw composite × 100 (transparency) |
| `placement_score_fraction` | float | Raw composite 0–1 (source of truth) |
| `match_level` | str | EXCELLENT/GOOD/MODERATE/BELOW AVERAGE/POOR (display-scale bands) |
| `domain_detected`, `role_title`, `seniority_level` | str | role context |

### Components
| Key | Type | Notes |
|---|---|---|
| `component_breakdown` | list[6] of dict | `{component, weight, component_score, score_achieved, pct_contribution, active}` — the 6 MW-ESE components |
| `excluded_components` | list of dict | JD-gated / empty components + reason |
| `weights`, `effective_weights` | dict[6] | raw vs redistributed weights |
| `component_scores` | dict[6] | `S_sk, S_pr, S_in, S_we, S_ac, S_ah` |

### Analysis sections
`skills_analysis` (total_jd_skills, matched_count, missing_skills, skill_coverage_pct, match_details, skills_score_S_sk) · `improvement_suggestions` · `combined_improvement` · `gap_analysis` (ranked_gaps, total_recoverable_pct) · `recommendations` · `resume_extraction` (10 keys) · `jd_extraction` (12 keys) · `matching_transparency` (by match type) · `debug` (13 keys, incl. `full_debug_log`) · `final_summary` (6 keys) · `experience_intelligence` (20 keys) · `project_intelligence` (11 keys) · `explainability` (26 keys).

### Deterministic vs LLM-only fields ⚠️ (UI contract)
With `llm_provider=None` (default, deterministic), these are **`None`/empty by design**:
- `llm_role_summary`, `llm_seniority`
- `explainability.overall_summary`, `.next_steps`, `.top_strengths`, `.top_gaps`, `.experience_rationale`, all `.*_llm` fields
- `experience_intelligence.llm_*`, `project_intelligence.llm_top_strengths/gaps`
- `final_summary.strengths` / `.weaknesses` (sourced from explainability → empty without LLM)

**UI implication:** every LLM-derived panel needs a non-LLM fallback or empty
state. Component scores, breakdowns, gaps, missing-skills, recommendations,
experience/project intelligence are all **fully populated deterministically**.

---

## 2. Determinism — ✅ confirmed
Two runs on identical inputs (TF-IDF) produced **identical** `placement_score`,
`component_breakdown`, and `missing_skills`. The default run makes zero LLM
calls; SBERT is deterministic for fixed inputs.

---

## 3. Error / edge-case handling

| Scenario | Behavior | Verdict |
|---|---|---|
| Unsupported extension (`.txt`) | raises `ValueError` | ✅ correct |
| Empty JD `""` / whitespace | raises `ValueError("JD text must be a non-empty string")` | ✅ correct |
| `None` resume path | returns valid payload, score 0.0 / POOR | ✅ graceful |
| **Nonexistent `.pdf`** | prints `"PDF extraction error: ..."` to stdout, returns empty resume → **score 0.0 / POOR** | ⚠️ **silent** — see Finding #1 |
| JD with no extractable skills (gibberish) | returns valid payload, **score 36.67** (driven by resume project/internship components) | ⚠️ see Finding #2 |

No crashes on any malformed input. Degradation is graceful but in two cases
*misleadingly graceful*.

---

## 4. Findings & recommendations (prioritized)

**F1 — Unreadable/bad file returns a misleading 0% instead of an error.**
`parse_resume` swallows the PDF read error (prints to stdout, returns
`empty_output`), so a corrupt/missing upload yields a confident "0% POOR" result.
→ **Fix in the FastAPI layer (UI phase):** validate the upload (exists + parses +
non-empty text) and return a 4xx with a clear message; distinguish "unreadable
file" from "empty resume." Also replace the `print(...)` with proper logging.

**F2 — A JD with no extractable skills still scores ~37.** Resume
project/internship components score against the (skill-less) JD text, so the
composite isn't 0. → **API should surface a warning when `debug.jd_skill_count == 0`**
("couldn't extract requirements from this JD") rather than present a number.

**F3 — Narrative fields empty in deterministic mode (by design).** See §1. →
UI must render component-derived strengths/gaps or empty states; don't block on
`llm_*`.

**F4 — Cosmetic:** recommendations say "aligned with `not_specified`" when the
role is unknown; `improvement_suggestions` can be long (14 items). → UI should
substitute "the target role" and cap/paginate.

None of F1–F4 are correctness bugs in scoring; they're robustness/UX items for
the API+UI layer.

---

## 5. Known-limitations register

Carried forward from the scoring/cleanup work (all deliberate, documented):

- **Display normalization anchors** are calibrated to the 54-pair sample; revisit if the score distribution shifts materially.
- **`count_roles`** floors at 1 for internships with no machine-detectable dates (undated multi-internship lists undercount).
- **Per-role reclassification** is date-anchor heuristic; resumes with unparseable dates fall back to single-block all-or-nothing.
- **Residual JD noise:** a few quirky artifacts survive the aggressive filter — `cards pl`, `melbourne to vancouver`, `aws. docker`, `key skills python`, `practical ai`. Not systematic prose; can be swept with targeted rules.
- **EXCELLENT (display ≥85)** requires raw ≥~0.60 — reached only by the single strongest fit in the current set.
- **LLM gate path** (`llm_provider` set) re-matches on collapsed entries; the derived-flag collapse is applied in the deterministic pipeline — verify parity when the LLM gate is re-validated (Phase 5/6).

---

## 6. Verdict
The deterministic backend is **accurate, calibrated, denoised, deterministic, and
robust to malformed input (no crashes)**. It is ready for the UI phase, with F1/F2
to be handled in the FastAPI layer and F3/F4 in the frontend. Recommended API
shape: `POST /analyze` (multipart resume + JD text) → the payload above;
`GET /health`. Validate inputs at the boundary (F1/F2).
