"""Manual-testing report harness (Phase-4 prep).

For each resume x JD pair, runs the full pipeline and prints the COMPLETE
structured output requested in the Phase-4 Testing Plan:

  1. Placement score + match level
  2. Domain & role detection
  3. Component breakdown (6 MW-ESE)
  4. Skills analysis
  5. Improvement suggestions
  6. Recommendations
  7. Resume extraction validation
  8. JD extraction validation
  9. Matching transparency (by match type)
  10. Debug / validation info
  11. Final output summary

Usage:
    python tests/manual_test_report.py                      # all pairs, deterministic
    python tests/manual_test_report.py --resume Ananya --jd JD-9
    LLM_BACKEND=ollama python tests/manual_test_report.py --llm --resume Eklavya --jd JD_1
    python tests/manual_test_report.py --json out.json      # also dump JSON
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.analysis import analyze_resume_jd
from app.utils.embeddings import get_embedding_provider
from app.utils.file_handling import extract_text_from_docx

FIXTURES = BACKEND_ROOT / "tests" / "fixtures"


def _discover():
    resumes = {}
    for f in sorted(glob.glob(str(FIXTURES / "*.pdf"))):
        name = os.path.basename(f).split("_Resume")[0].split(" ")[0].replace(".pdf", "")
        resumes[name] = f
    def jd_key(p):
        m = re.search(r"JD[_-](\d+)", os.path.basename(p))
        return int(m.group(1)) if m else 999
    jds = {}
    for f in sorted(glob.glob(str(FIXTURES / "JD*.docx")), key=jd_key):
        name = os.path.basename(f).replace(".docx", "").replace("_", "-")
        jds[name] = f
    return resumes, jds


def _h(title, ch="="):
    return f"\n{ch * 78}\n{title}\n{ch * 78}"


def _render(resume_name, jd_name, out) -> str:
    L = []
    L.append(_h(f"TEST CASE:  {resume_name}   x   {jd_name}"))

    # 1 — Placement score
    L.append(_h("1. PLACEMENT SCORE", "-"))
    L.append(f"  Placement Score : {out['placement_score']} %")
    L.append(f"  Match Level     : {out['match_level']}")

    # 2 — Domain & role
    L.append(_h("2. DOMAIN & ROLE DETECTION", "-"))
    L.append(f"  Domain          : {out['domain_detected']}")
    L.append(f"  Role (det)      : {out['role_title']}")
    L.append(f"  Role (LLM)      : {out.get('llm_role_summary')}")
    L.append(f"  Seniority       : {out['seniority_level']}  (LLM: {out.get('llm_seniority')})")

    # 3 — Component breakdown
    L.append(_h("3. COMPONENT BREAKDOWN (6 MW-ESE)", "-"))
    L.append(f"  Weight profile  : {out['weight_profile_used']}")
    L.append(f"  {'Component':<30}{'Weight':>8}{'Score':>8}{'Contrib%':>10}  Active")
    for c in out["component_breakdown"]:
        L.append(f"  {c['component']:<30}{c['weight']:>8.3f}{c['component_score']:>8.3f}"
                 f"{c['pct_contribution']:>10.2f}  {c['active']}")
    if out["excluded_components"]:
        L.append("  Excluded: " + ", ".join(
            f"{e['component']} ({e['reason']})" for e in out["excluded_components"]))

    # 4 — Skills analysis
    sa = out["skills_analysis"]
    L.append(_h("4. SKILLS ANALYSIS", "-"))
    L.append(f"  Total JD skills : {sa['total_jd_skills']}")
    L.append(f"  Matched         : {sa['matched_count']}")
    L.append(f"  Coverage        : {sa['skill_coverage_pct']} %")
    L.append(f"  Skill score S_sk: {sa['skills_score_S_sk']}")
    L.append(f"  Missing skills  : {sa['missing_skills']}")
    L.append("  Match details:")
    for m in sa["match_details"][:25]:
        L.append(f"    [{m['match_type']:<8}] {m['resume_phrase']!r} <-> {m['jd_phrase']!r} "
                 f"(sim={m.get('similarity')})")

    # 5 — Improvement suggestions
    L.append(_h("5. IMPROVEMENT SUGGESTIONS (ranked)", "-"))
    for s in out["improvement_suggestions"][:12]:
        L.append(f"  #{s['rank']:<2} {s['improvement']:<45} "
                 f"{s['current_score']}% -> {s['predicted_score']}%  (+{s['delta_gain']})")
    ci = out["combined_improvement"]
    L.append(f"  Combined potential: {ci.get('current_score')}% -> {ci.get('combined_new_score')}% "
             f"(delta +{ci.get('combined_delta')})")
    L.append(f"  Total recoverable : {out['gap_analysis']['total_recoverable_pct']}%")

    # 6 — Recommendations
    L.append(_h("6. RECOMMENDATIONS", "-"))
    for r in out["recommendations"]:
        L.append(f"  - {r}")
    if not out["recommendations"]:
        L.append("  (none)")

    # 7 — Resume extraction
    re_ = out["resume_extraction"]
    L.append(_h("7. RESUME EXTRACTION VALIDATION", "-"))
    L.append(f"  Sections present: {re_['sections_present']}")
    L.append(f"  Empty sections  : {re_['empty_sections']}")
    L.append(f"  Skills ({len(re_['skills'])}): {re_['skills']}")
    L.append(f"  Certifications ({len(re_['certifications'])}): {re_['certifications'][:6]}")
    L.append(f"  Projects ({len(re_['projects'])}): {[p[:50] for p in re_['projects'][:4]]}")
    L.append(f"  Internships ({len(re_['internships'])}): {[i[:50] for i in re_['internships'][:4]]}")
    L.append(f"  Work exp ({len(re_['work_experience'])}): {[w[:50] for w in re_['work_experience'][:4]]}")
    L.append(f"  Education ({len(re_['education'])}): {re_['education'][:4]}")

    # 8 — JD extraction
    je = out["jd_extraction"]
    L.append(_h("8. JD EXTRACTION VALIDATION", "-"))
    L.append(f"  Required ({len(je['required_skills'])}): {je['required_skills']}")
    L.append(f"  Preferred ({len(je['preferred_skills'])}): {je['preferred_skills']}")
    L.append(f"  Optional ({len(je['optional_skills'])}): {je['optional_skills']}")
    L.append(f"  Domain: {je['primary_domain']} (secondary: {je['secondary_domain']})")
    L.append(f"  Role: {je['role_title']}  | Exp years: {je['experience_years']}  | Edu: {je['education_level']}")
    L.append(f"  Rules: {je['rules']}")
    if je.get("llm_excluded_noise"):
        L.append(f"  LLM excluded noise: {je['llm_excluded_noise']}")

    # 9 — Matching transparency
    mt = out["matching_transparency"]
    L.append(_h("9. MATCHING TRANSPARENCY (by type)", "-"))
    for tier in ("exact", "alias", "synonym", "semantic", "partial", "cluster"):
        items = mt.get(tier, [])
        if items:
            L.append(f"  {tier.upper()} ({len(items)}):")
            for m in items[:12]:
                L.append(f"    {m['resume_phrase']!r} <-> {m['jd_phrase']!r}")

    # 10 — Debug
    d = out["debug"]
    L.append(_h("10. DEBUG / VALIDATION INFO", "-"))
    L.append(f"  Resume skill count : {d['resume_skill_count']}")
    L.append(f"  JD skill count     : {d['jd_skill_count']}")
    L.append(f"  Match type counts  : {d['match_type_counts']}")
    L.append(f"  Weighted JD coverage : {d['weighted_jd_coverage']}")
    L.append(f"  Avg match confidence : {d['avg_match_confidence']}")
    L.append(f"  Resume pool coverage : {d['resume_pool_coverage']}")
    L.append(f"  Final skill score    : {d['final_skill_score']}")
    L.append(f"  JD bucket counts     : {d['jd_bucket_counts']}")
    L.append(f"  Resume skill sources : {d['resume_skill_source_counts']}")
    L.append(f"  Embedding backend    : {d['embedding_backend']}")
    if d.get("llm_validation"):
        v = d["llm_validation"]
        L.append(f"  LLM gate: kept={len(v.get('kept', []))} rejected={len(v.get('rejected', []))} "
                 f"skipped={v.get('skipped_reason')}")
        for rej in v.get("rejected", [])[:8]:
            L.append(f"    REJECTED {rej['resume_phrase']!r}<->{rej['jd_phrase']!r}: {rej.get('reason','')[:60]}")

    # 11 — Final summary
    fs = out["final_summary"]
    L.append(_h("11. FINAL OUTPUT SUMMARY", "-"))
    L.append(f"  Overall: {fs['overall_assessment']}")
    L.append(f"  Candidate category: {fs['candidate_category']}")
    L.append(f"  Strengths: {fs['strengths']}")
    L.append(f"  Weaknesses: {fs['weaknesses']}")
    L.append(f"  Key missing: {fs['key_missing_requirements']}")
    L.append(f"  Next actions: {fs['recommended_next_actions']}")

    return "\n".join(L)


def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume", help="substring filter for resume name")
    ap.add_argument("--jd", help="exact JD name e.g. JD_1 or JD-9")
    ap.add_argument("--llm", action="store_true", help="enable LLM validation+enrichment")
    ap.add_argument("--json", type=Path, help="also dump full payloads to this JSON path")
    ap.add_argument("--out", type=Path, help="write the text report to this file too")
    args = ap.parse_args()

    resumes, jds = _discover()
    if args.resume:
        resumes = {k: v for k, v in resumes.items() if args.resume.lower() in k.lower()}
    if args.jd:
        key = args.jd.replace("_", "-")
        jds = {k: v for k, v in jds.items() if k == key}

    llm_provider = None
    if args.llm:
        from app.utils.llm import get_llm_provider
        llm_provider = get_llm_provider()

    provider = get_embedding_provider()
    print(f"[embedding backend: {provider.backend}]"
          f"{'  [LLM: ' + llm_provider.backend + ']' if llm_provider else '  [LLM: off]'}")

    all_text, all_json = [], {}
    for r_name, r_path in resumes.items():
        for j_name, j_path in jds.items():
            jd_text = extract_text_from_docx(j_path)
            out = analyze_resume_jd(r_path, jd_text, provider=provider,
                                    llm_provider=llm_provider, debug=True)
            block = _render(r_name, j_name, out)
            print(block)
            all_text.append(block)
            all_json[f"{r_name} x {j_name}"] = out

    if args.out:
        args.out.write_text("\n".join(all_text), encoding="utf-8")
        print(f"\n[text report written to {args.out}]")
    if args.json:
        args.json.write_text(json.dumps(all_json, indent=2, default=str), encoding="utf-8")
        print(f"[json payloads written to {args.json}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
