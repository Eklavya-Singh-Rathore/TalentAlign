"""Phase 27 — End-to-end 54-pair validation in both LLM modes.

Runs the full ``analyze_resume_jd`` pipeline for all 6 resumes x 9 JDs in
two modes:

  1. SBERT fallback  (LLM_BACKEND=none) — deterministic, no Gemini calls
  2. Gemini primary  (LLM_BACKEND=gemini) — full LLM enrichment + validation gate

For each pair captures placement_score, match_level, component scores,
matched/missing skills, recommendations, and (Gemini mode only) narrative
quality metrics (overall_assessment length, strengths/gaps populated,
explainability polishing flag). Per-pair errors are caught so one failure
doesn't kill the run.

Outputs:
  tests/reports/phase27_sbert_results.json
  tests/reports/phase27_gemini_results.json
  tests/reports/phase27_comparison_report.md

Usage:
  # SBERT only (fast, deterministic)
  python tests/phase27_validation.py --mode sbert

  # Both modes (Gemini requires GEMINI_API_KEY set)
  python tests/phase27_validation.py --mode both

  # Gemini only (assumes SBERT JSON already exists)
  python tests/phase27_validation.py --mode gemini
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.analysis import analyze_resume_jd
from app.utils.embeddings import EmbeddingProvider, get_embedding_provider
from app.utils.file_handling import extract_text_from_docx
from app.utils.llm import LLMProvider, get_llm_provider, reset_default_provider

REPORTS_DIR = BACKEND_ROOT / "tests" / "reports"
COMPONENT_KEYS = ["S_sk", "S_pr", "S_in", "S_we", "S_ac", "S_ah"]


def discover() -> Tuple[Dict[str, str], Dict[str, str]]:
    fx = BACKEND_ROOT / "tests" / "fixtures"
    resumes: Dict[str, str] = {}
    for f in sorted(glob.glob(str(fx / "*.pdf"))):
        base = os.path.basename(f).split("_Resume")[0]
        label = re.split(r"[ _]", base)[0]
        resumes[label] = f

    def jd_key(path: str) -> int:
        m = re.search(r"JD[_-](\d+)", os.path.basename(path))
        return int(m.group(1)) if m else 999

    jds: Dict[str, str] = {}
    for f in sorted(glob.glob(str(fx / "JD*.docx")), key=jd_key):
        name = os.path.basename(f).replace(".docx", "").replace("_", "-")
        jds[name] = f
    return resumes, jds


def capture_payload(out: Dict, mode: str) -> Dict:
    """Extract the per-pair fields we want to compare across modes."""
    skills = out.get("skills_analysis", {})
    summary = out.get("final_summary", {})
    explain = out.get("explainability", {})
    debug = out.get("debug", {})

    base = {
        "placement_score": out.get("placement_score"),
        "placement_score_raw_pct": out.get("placement_score_raw_pct"),
        "match_level": out.get("match_level"),
        "domain_detected": out.get("domain_detected"),
        "role_title": out.get("role_title"),
        "seniority_level": out.get("seniority_level"),
        "component_scores": {
            k: round(float(out.get("component_scores", {}).get(k, 0.0)), 4)
            for k in COMPONENT_KEYS
        },
        "effective_weights": {
            k: round(float(v), 4)
            for k, v in out.get("effective_weights", {}).items()
        },
        "matched_count": skills.get("matched_count"),
        "total_jd_skills": skills.get("total_jd_skills"),
        "skill_coverage_pct": skills.get("skill_coverage_pct"),
        "missing_skills_top10": (skills.get("missing_skills") or [])[:10],
        "match_type_counts": debug.get("match_type_counts", {}),
        "llm_backend": debug.get("llm_backend"),
        "embedding_backend": debug.get("embedding_backend"),
        "warnings_count": 0,  # API-level warnings — not produced by the orchestrator directly
    }

    if mode == "gemini":
        # Narrative quality metrics
        strengths = summary.get("strengths") or []
        weaknesses = summary.get("weaknesses") or []
        overall = summary.get("overall_assessment") or ""
        polish_summary = explain.get("overall_summary") or ""
        next_steps = explain.get("next_steps") or []
        validation = debug.get("llm_validation") or {}

        base.update({
            "narrative": {
                "overall_assessment_len": len(overall),
                "overall_assessment_nonempty": bool(overall.strip()),
                "strengths_count": len(strengths),
                "weaknesses_count": len(weaknesses),
                "explain_overall_summary_len": len(polish_summary),
                "explain_next_steps_count": len(next_steps),
                "llm_polishing_used": bool(explain.get("llm_polishing_used")),
                "experience_rationale_present": bool(explain.get("experience_rationale")),
                "candidate_type_llm": explain.get("candidate_type_llm"),
                "leadership_signals_count": len(explain.get("leadership_signals") or []),
                "impact_metrics_count": len(explain.get("impact_metrics") or []),
            },
            "validation_gate": {
                "candidate_count": validation.get("candidate_count", 0),
                "kept": validation.get("matches_validated_kept", validation.get("kept", 0)),
                "rejected": validation.get("matches_validated_rejected", validation.get("rejected", 0)),
                "skipped_reason": validation.get("validation_skipped_reason") or validation.get("skipped_reason"),
            },
        })

    return base


def run_pair(resume_path: str, jd_text: str, mode: str,
             provider: EmbeddingProvider, llm: Optional[LLMProvider]) -> Tuple[Optional[Dict], Optional[str], float]:
    """Run analyze_resume_jd, returning (captured_payload, error_message, seconds)."""
    t0 = time.monotonic()
    try:
        out = analyze_resume_jd(resume_path, jd_text, provider=provider, llm_provider=llm)
        elapsed = time.monotonic() - t0
        return capture_payload(out, mode), None, elapsed
    except Exception as exc:  # capture so one failure doesn't abort the whole sweep
        elapsed = time.monotonic() - t0
        return None, f"{type(exc).__name__}: {exc}", elapsed


def run_mode(mode: str, resumes: Dict[str, str], jds: Dict[str, str],
             jd_text: Dict[str, str], provider: EmbeddingProvider,
             llm: Optional[LLMProvider]) -> Dict:
    results: Dict[str, Dict] = {}
    failures: List[Dict] = []
    print(f"\n=== Phase 27 — {mode.upper()} mode ===")
    print(f"  embedding={provider.backend}  llm={(llm.backend if llm else 'none')}")
    total = len(resumes) * len(jds)
    done = 0
    t_start = time.monotonic()
    for rn, rp in resumes.items():
        for jn, jt in jd_text.items():
            done += 1
            pair_key = f"{rn}|{jn}"
            payload, err, secs = run_pair(rp, jt, mode, provider, llm)
            tag = "OK " if err is None else "FAIL"
            score = payload["placement_score"] if payload else "—"
            print(f"  [{done:2d}/{total}] {tag} {pair_key:<22} {secs:5.2f}s  score={score}")
            if err is not None:
                failures.append({"pair": pair_key, "error": err, "seconds": round(secs, 2)})
            else:
                payload["pair_seconds"] = round(secs, 2)
                results[pair_key] = payload
    total_seconds = time.monotonic() - t_start
    print(f"  done in {total_seconds:.1f}s — {len(results)} ok, {len(failures)} failures")
    return {
        "meta": {
            "generated": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "embedding_backend": provider.backend,
            "llm_backend": (llm.backend if llm else "none"),
            "resumes": list(resumes),
            "jds": list(jds),
            "pairs": len(resumes) * len(jds),
            "successful_pairs": len(results),
            "failed_pairs": len(failures),
            "total_seconds": round(total_seconds, 2),
        },
        "results": results,
        "failures": failures,
    }


def build_comparison(sbert: Dict, gemini: Optional[Dict]) -> str:
    md: List[str] = []
    md.append("# Phase 27 — 54-Pair End-to-End Validation Report\n")
    md.append(f"- Generated: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"- Resumes: {len(sbert['meta']['resumes'])}  |  JDs: {len(sbert['meta']['jds'])}  |  Pairs: {sbert['meta']['pairs']}")
    md.append(f"- SBERT mode: {sbert['meta']['successful_pairs']} ok / {sbert['meta']['failed_pairs']} failed ({sbert['meta']['total_seconds']}s)")
    if gemini:
        md.append(f"- Gemini mode: {gemini['meta']['successful_pairs']} ok / {gemini['meta']['failed_pairs']} failed ({gemini['meta']['total_seconds']}s)")
    md.append("")

    # ── 1. SBERT score matrix ────────────────────────────────────────────────
    md.append("## 1. SBERT mode — placement score matrix (display 0–100)\n```")
    md.append(_score_matrix(sbert))
    md.append("```\n")

    if gemini:
        md.append("## 2. Gemini mode — placement score matrix (display 0–100)\n```")
        md.append(_score_matrix(gemini))
        md.append("```\n")

        # ── 3. Per-pair deltas ───────────────────────────────────────────────
        md.append("## 3. Per-pair deltas (Gemini − SBERT)\n")
        md.append("Negative deltas are expected: the Gemini validation gate rejects ~84% of borderline false positives in the matcher (see plan §9), lowering matched_count and placement_score.\n```")
        md.append(_delta_matrix(sbert, gemini))
        md.append("```\n")

        # Statistics
        deltas: List[float] = []
        for k, s in sbert["results"].items():
            g = gemini["results"].get(k)
            if g is None:
                continue
            deltas.append(g["placement_score"] - s["placement_score"])
        if deltas:
            md.append(f"- Mean delta: **{sum(deltas)/len(deltas):+.2f}**  |  median: **{sorted(deltas)[len(deltas)//2]:+.2f}**  |  min: **{min(deltas):+.2f}**  |  max: **{max(deltas):+.2f}**")
            within_2pct = sum(1 for d in deltas if abs(d) <= 2.0)
            md.append(f"- Pairs within ±2.0 display points: **{within_2pct} / {len(deltas)}**\n")

        # ── 4. Narrative quality ──────────────────────────────────────────────
        md.append("## 4. Narrative quality (Gemini mode)\n")
        narrative_stats = _narrative_stats(gemini)
        md.append("| Metric | Coverage | Mean |")
        md.append("|---|---|---|")
        for label, (coverage, mean) in narrative_stats.items():
            md.append(f"| {label} | {coverage} | {mean} |")
        md.append("")

        # ── 5. Validation gate activity ───────────────────────────────────────
        md.append("## 5. Validation-gate activity (Gemini mode)\n```")
        md.append(_validation_table(gemini))
        md.append("```\n")

        # ── 6. Sample narrative output ────────────────────────────────────────
        md.append("## 6. Sample narratives (first 3 pairs)\n")
        for pair_key in list(gemini["results"].keys())[:3]:
            p = gemini["results"][pair_key]
            md.append(f"### {pair_key}")
            md.append(f"- score: {p['placement_score']} ({p['match_level']})")
            md.append(f"- domain: {p['domain_detected']}  |  role: {p['role_title']}")
            n = p.get("narrative", {})
            md.append(f"- overall_assessment_len: {n.get('overall_assessment_len')}")
            md.append(f"- strengths: {n.get('strengths_count')}  |  gaps: {n.get('weaknesses_count')}  |  next_steps: {n.get('explain_next_steps_count')}")
            md.append("")

    # ── Failures ────────────────────────────────────────────────────────────
    md.append("## Failures\n")
    md.append(f"### SBERT mode: {len(sbert['failures'])}")
    for f in sbert["failures"]:
        md.append(f"- `{f['pair']}` — {f['error']}")
    if gemini:
        md.append(f"\n### Gemini mode: {len(gemini['failures'])}")
        for f in gemini["failures"]:
            md.append(f"- `{f['pair']}` — {f['error']}")
    md.append("")

    # ── SBERT determinism ──────────────────────────────────────────────────
    md.append("## Determinism (SBERT mode)\n")
    md.append("Re-runs of SBERT-only mode against identical inputs produce byte-identical payloads (verified during the pre-structure audit). All `llm_*` narrative fields are `None`/empty by design.\n")

    return "\n".join(md)


def _score_matrix(blob: Dict) -> str:
    resumes = blob["meta"]["resumes"]
    jds = blob["meta"]["jds"]
    hdr = f"{'Resume':<12}" + "".join(f"{j:>9}" for j in jds)
    rows = [hdr, "-" * len(hdr)]
    for rn in resumes:
        cells = ""
        for jn in jds:
            p = blob["results"].get(f"{rn}|{jn}")
            cells += f"{(p['placement_score'] if p else 0.0):>9.1f}" if p else f"{'FAIL':>9}"
        rows.append(f"{rn:<12}{cells}")
    return "\n".join(rows)


def _delta_matrix(sbert: Dict, gemini: Dict) -> str:
    resumes = sbert["meta"]["resumes"]
    jds = sbert["meta"]["jds"]
    hdr = f"{'Resume':<12}" + "".join(f"{j:>9}" for j in jds)
    rows = [hdr, "-" * len(hdr)]
    for rn in resumes:
        cells = ""
        for jn in jds:
            s = sbert["results"].get(f"{rn}|{jn}")
            g = gemini["results"].get(f"{rn}|{jn}")
            if s and g:
                cells += f"{(g['placement_score'] - s['placement_score']):>+9.2f}"
            else:
                cells += f"{'—':>9}"
        rows.append(f"{rn:<12}{cells}")
    return "\n".join(rows)


def _narrative_stats(blob: Dict) -> Dict[str, Tuple[str, str]]:
    results = list(blob["results"].values())
    total = len(results)
    if not total:
        return {}
    coverage = {}
    means = {}

    def _cov(predicate) -> str:
        n = sum(1 for r in results if predicate(r.get("narrative", {})))
        return f"{n}/{total} ({n/total*100:.0f}%)"

    def _mean(getter) -> str:
        vals = [getter(r.get("narrative", {})) for r in results]
        vals = [v for v in vals if isinstance(v, (int, float))]
        return f"{sum(vals)/len(vals):.1f}" if vals else "—"

    return {
        "overall_assessment populated": (_cov(lambda n: n.get("overall_assessment_nonempty")),
                                          _mean(lambda n: n.get("overall_assessment_len", 0))),
        "strengths populated":          (_cov(lambda n: (n.get("strengths_count") or 0) > 0),
                                          _mean(lambda n: n.get("strengths_count", 0))),
        "gaps (weaknesses) populated":  (_cov(lambda n: (n.get("weaknesses_count") or 0) > 0),
                                          _mean(lambda n: n.get("weaknesses_count", 0))),
        "explain.overall_summary":      (_cov(lambda n: (n.get("explain_overall_summary_len") or 0) > 0),
                                          _mean(lambda n: n.get("explain_overall_summary_len", 0))),
        "explain.next_steps":           (_cov(lambda n: (n.get("explain_next_steps_count") or 0) > 0),
                                          _mean(lambda n: n.get("explain_next_steps_count", 0))),
        "llm_polishing_used":           (_cov(lambda n: bool(n.get("llm_polishing_used"))),
                                          "—"),
        "experience_rationale":         (_cov(lambda n: bool(n.get("experience_rationale_present"))),
                                          "—"),
    }


def _validation_table(blob: Dict) -> str:
    rows = [f"{'pair':<22} {'cand':>5} {'kept':>5} {'rej':>5}  skipped_reason"]
    rows.append("-" * 60)
    for pair_key, p in blob["results"].items():
        v = p.get("validation_gate", {})
        rows.append(f"{pair_key:<22} {(v.get('candidate_count') or 0):>5} {(v.get('kept') or 0):>5} {(v.get('rejected') or 0):>5}  {(v.get('skipped_reason') or '')}")
    return "\n".join(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 27 — 54-pair end-to-end validation")
    parser.add_argument("--mode", choices=["sbert", "gemini", "both"], default="both",
                        help="Which mode(s) to run")
    args = parser.parse_args()

    resumes, jds = discover()
    jd_text = {n: extract_text_from_docx(p) for n, p in jds.items()}
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    sbert_path = REPORTS_DIR / "phase27_sbert_results.json"
    gemini_path = REPORTS_DIR / "phase27_gemini_results.json"
    report_path = REPORTS_DIR / "phase27_comparison_report.md"

    # ── SBERT mode ────────────────────────────────────────────────────────
    if args.mode in ("sbert", "both"):
        provider = get_embedding_provider()  # honors TALENTALIGN_EMBEDDING_BACKEND
        sbert_blob = run_mode("sbert", resumes, jds, jd_text, provider, llm=None)
        sbert_path.write_text(json.dumps(sbert_blob, indent=2), encoding="utf-8")
        print(f"  wrote {sbert_path}")
    else:
        if not sbert_path.exists():
            print(f"  --mode gemini requires {sbert_path} to exist", file=sys.stderr)
            return 1
        sbert_blob = json.loads(sbert_path.read_text(encoding="utf-8"))

    # ── Gemini mode ───────────────────────────────────────────────────────
    gemini_blob: Optional[Dict] = None
    if args.mode in ("gemini", "both"):
        reset_default_provider()  # ensure fresh LLMProvider after env changes
        provider = get_embedding_provider()
        # Force a fresh LLM provider so backend resolution sees the current env
        llm = LLMProvider(backend="gemini")
        if llm.backend != "gemini":
            print(f"  Gemini backend unavailable (resolved: {llm.backend}). Check GEMINI_API_KEY.", file=sys.stderr)
            return 1
        gemini_blob = run_mode("gemini", resumes, jds, jd_text, provider, llm=llm)
        gemini_path.write_text(json.dumps(gemini_blob, indent=2), encoding="utf-8")
        print(f"  wrote {gemini_path}")

    # ── Comparison report ─────────────────────────────────────────────────
    report = build_comparison(sbert_blob, gemini_blob)
    report_path.write_text(report, encoding="utf-8")
    print(f"  wrote {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
