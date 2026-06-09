"""54-pair deterministic evaluation matrix (6 resumes x 9 JDs).

Runs the full ``analyze_resume_jd`` pipeline (deterministic, no LLM) for every
resume x JD pair and emits the calibration baseline:
  - composite (placement) score matrix + match-level matrix
  - per-component score breakdowns (by JD)
  - ranking analysis (per JD; per-resume best/worst)
  - recommendation outputs
  - missing-skill outputs
  - matching statistics (matched/total, coverage, match-type counts)

Outputs:
  tests/reports/eval_matrix_54.json   (full structured data)
  tests/reports/eval_matrix_54.md     (readable report)

Usage:  python tests/eval_matrix_54.py
"""

from __future__ import annotations

import glob
import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.analysis import analyze_resume_jd
from app.utils.embeddings import get_embedding_provider
from app.utils.file_handling import extract_text_from_docx

COMPONENT_KEYS = [("S_sk", "Skills"), ("S_pr", "Proj"), ("S_in", "Intern"),
                  ("S_we", "Work"), ("S_ac", "Acad"), ("S_ah", "Ach")]


def discover():
    fx = BACKEND_ROOT / "tests" / "fixtures"
    resumes = {}
    for f in sorted(glob.glob(str(fx / "*.pdf"))):
        base = os.path.basename(f).split("_Resume")[0]
        label = re.split(r"[ _]", base)[0]
        resumes[label] = f

    def jd_key(path):
        m = re.search(r"JD[_-](\d+)", os.path.basename(path))
        return int(m.group(1)) if m else 999

    jds = {}
    for f in sorted(glob.glob(str(fx / "JD*.docx")), key=jd_key):
        name = os.path.basename(f).replace(".docx", "").replace("_", "-")
        jds[name] = f
    return resumes, jds


def run():
    resumes, jds = discover()
    prov = get_embedding_provider()
    jd_text = {n: extract_text_from_docx(p) for n, p in jds.items()}
    results = {}
    for rn, rp in resumes.items():
        for jn, jt in jd_text.items():
            out = analyze_resume_jd(rp, jt, provider=prov, llm_provider=None)
            results[f"{rn}|{jn}"] = {
                "resume": rn, "jd": jn,
                "placement_score": out["placement_score"],
                "placement_raw": out.get("placement_score_raw_pct", out["placement_score"]),
                "match_level": out["match_level"],
                "domain": out["domain_detected"],
                "role": out["role_title"],
                "components": {k: round(float(out["component_scores"].get(k, 0.0)), 3)
                               for k, _ in COMPONENT_KEYS},
                "effective_weights": {k: round(float(v), 3)
                                      for k, v in out["effective_weights"].items()},
                "excluded": [e["component"] for e in out["excluded_components"]],
                "recommendations": out["recommendations"],
                "missing_skills": out["skills_analysis"]["missing_skills"][:10],
                "matched_count": out["skills_analysis"]["matched_count"],
                "total_jd_skills": out["skills_analysis"]["total_jd_skills"],
                "skill_coverage_pct": out["skills_analysis"]["skill_coverage_pct"],
                "match_type_counts": out["debug"]["match_type_counts"],
            }
    return resumes, jds, prov, results


def _matrix(resumes, jds, results, getter, width=8, fmt="{:>8.1f}"):
    hdr = f"{'Resume':<12}" + "".join(f"{j:>{width}}" for j in jds)
    rows = [hdr, "-" * len(hdr)]
    for rn in resumes:
        cells = "".join(fmt.format(getter(results[f"{rn}|{jn}"])) for jn in jds)
        rows.append(f"{rn:<12}{cells}")
    return "\n".join(rows)


def build_report(resumes, jds, prov, results):
    md = []
    md.append("# TalentAlign — 54-Pair Deterministic Calibration Matrix\n")
    md.append(f"- Generated: {datetime.now(timezone.utc).isoformat()}")
    md.append(f"- Embedding backend: **{prov.backend}**  |  LLM: **none (deterministic)**")
    md.append(f"- Resumes: {len(resumes)}  |  JDs: {len(jds)}  |  Pairs: {len(results)}\n")

    md.append("## 1. Normalized display-score matrix (0-100)\n```")
    md.append(_matrix(resumes, jds, results, lambda d: d["placement_score"]))
    md.append("```\n### raw composite %\n```")
    md.append(_matrix(resumes, jds, results, lambda d: d["placement_raw"]))
    md.append("```\n")

    md.append("## 2. Match-level matrix\n```")
    md.append(_matrix(resumes, jds, results, lambda d: d["match_level"],
                      width=15, fmt="{:>15}"))
    md.append("```\n")

    md.append("## 3. Per-JD ranking (by composite)\n")
    for jn in jds:
        ranked = sorted(resumes, key=lambda rn: results[f"{rn}|{jn}"]["placement_score"],
                        reverse=True)
        parts = [f"{rn} {results[f'{rn}|{jn}']['placement_score']:.1f}" for rn in ranked]
        md.append(f"- **{jn}** ({results[ranked[0]+'|'+jn]['role']}): " + "  >  ".join(parts))
    md.append("")

    md.append("## 4. Per-resume summary\n")
    md.append(f"{'Resume':<12}{'avg':>7}{'min':>7}{'max':>7}  best/worst JD")
    for rn in resumes:
        vals = {jn: results[f"{rn}|{jn}"]["placement_score"] for jn in jds}
        avg = sum(vals.values()) / len(vals)
        best = max(vals, key=vals.get)
        worst = min(vals, key=vals.get)
        md.append(f"{rn:<12}{avg:>7.1f}{min(vals.values()):>7.1f}{max(vals.values()):>7.1f}"
                  f"  {best}({vals[best]:.0f}) / {worst}({vals[worst]:.0f})")
    md.append("")

    md.append("## 5. Component-score breakdown by JD\n")
    for jn in jds:
        md.append(f"### {jn}\n```")
        chead = f"{'Resume':<12}{'Compos':>8}" + "".join(f"{lbl:>8}" for _, lbl in COMPONENT_KEYS)
        md.append(chead)
        md.append("-" * len(chead))
        for rn in resumes:
            d = results[f"{rn}|{jn}"]
            comps = "".join(f"{d['components'][k]:>8.2f}" for k, _ in COMPONENT_KEYS)
            md.append(f"{rn:<12}{d['placement_score']:>8.1f}{comps}")
        excl = results[f"{resumes_first(resumes)}|{jn}"]["excluded"]
        md.append(f"(JD-gated excluded: {excl})")
        md.append("```\n")

    md.append("## 6. Matching statistics\n")
    md.append("### matched / total JD skills\n```")
    md.append(_matrix(resumes, jds, results,
                      lambda d: f"{d['matched_count']}/{d['total_jd_skills']}",
                      width=9, fmt="{:>9}"))
    md.append("```\n### skill coverage %\n```")
    md.append(_matrix(resumes, jds, results, lambda d: d["skill_coverage_pct"]))
    md.append("```\n")

    md.append("## 7. Recommendations & missing skills (per pair)\n")
    for jn in jds:
        md.append(f"### {jn}")
        for rn in resumes:
            d = results[f"{rn}|{jn}"]
            md.append(f"- **{rn}** ({d['placement_score']:.0f}, {d['match_level']}) — "
                      f"recs: {d['recommendations'] or '[]'}")
            md.append(f"    - missing: {d['missing_skills'] or '[]'}")
        md.append("")

    return "\n".join(md)


def resumes_first(resumes):
    return next(iter(resumes))


def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    resumes, jds, prov, results = run()

    reports = BACKEND_ROOT / "tests" / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "eval_matrix_54.json").write_text(
        json.dumps({
            "meta": {
                "generated": datetime.now(timezone.utc).isoformat(),
                "embedding_backend": prov.backend,
                "resumes": list(resumes), "jds": list(jds), "pairs": len(results),
            },
            "results": results,
        }, indent=2), encoding="utf-8")
    report_md = build_report(resumes, jds, prov, results)
    (reports / "eval_matrix_54.md").write_text(report_md, encoding="utf-8")

    # Concise stdout summary
    print(f"[embedding={prov.backend}] resumes={list(resumes)} jds={list(jds)}\n")
    print("NORMALIZED DISPLAY-SCORE MATRIX (0-100)")
    print(_matrix(resumes, jds, results, lambda d: d["placement_score"]))
    print("\nRAW COMPOSITE % MATRIX")
    print(_matrix(resumes, jds, results, lambda d: d["placement_raw"]))
    print("\nPer-resume avg / range (display):")
    for rn in resumes:
        vals = [results[f"{rn}|{jn}"]["placement_score"] for jn in jds]
        print(f"  {rn:<12} avg={sum(vals)/len(vals):5.1f}  min={min(vals):5.1f}  max={max(vals):5.1f}")
    lvls = {}
    for d in results.values():
        lvls[d["match_level"]] = lvls.get(d["match_level"], 0) + 1
    print(f"\nMatch-level distribution: {lvls}")
    print(f"\nSaved: {reports/'eval_matrix_54.json'}\n       {reports/'eval_matrix_54.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
