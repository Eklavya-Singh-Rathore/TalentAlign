"""Comprehensive evaluation across ALL resumes x ALL JDs.

Discovers every resume (*.pdf) and JD (JD*.docx, both 'JD_N' and 'JD-N'
naming) under tests/fixtures/, then runs the full pipeline for each pair:
  - extraction (JD role/domain/seniority, resume sections)
  - matching (matched/missing, match types)
  - scoring (skill score deterministic; optionally LLM-gated)
  - optional LLM enrichment + gate

Usage:
  python tests/comprehensive_eval.py --mode deterministic
  LLM_BACKEND=ollama python tests/comprehensive_eval.py --mode gated
"""

from __future__ import annotations

import argparse
import glob
import io
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.jd_intelligence import analyze_jd
from app.services.jd_parser import parse_jd
from app.services.resume_parser import parse_resume
from app.services.skill_matcher import run_skill_extraction_pipeline, match_skills
from app.utils.embeddings import get_embedding_provider
from app.utils.file_handling import extract_text_from_docx
from app.utils.skill_normalization import compute_weighted_skill_score


def discover():
    fx = BACKEND_ROOT / "tests" / "fixtures"
    resumes = {}
    for f in sorted(glob.glob(str(fx / "*.pdf"))):
        name = os.path.basename(f).split("_Resume")[0].split(" ")[0].replace(".pdf", "")
        resumes[name] = f
    def jd_key(path):
        m = re.search(r"JD[_-](\d+)", os.path.basename(path))
        return int(m.group(1)) if m else 999
    jds = {}
    for f in sorted(glob.glob(str(fx / "JD*.docx")), key=jd_key):
        name = os.path.basename(f).replace(".docx", "").replace("_", "-")
        jds[name] = f
    return resumes, jds


def skill_score(base, matched):
    det = compute_weighted_skill_score(
        [{"phrase": e["phrase"], "bucket": e["bucket"]} for e in base["jd_skill_entries"]],
        matched, len(base["resume_skill_phrases"]),
    )
    return det["score"]


def main() -> int:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["deterministic", "gated"], default="deterministic")
    args = ap.parse_args()

    resumes, jds = discover()
    prov = get_embedding_provider()
    llm = None
    if args.mode == "gated":
        from app.utils.llm import get_llm_provider
        llm = get_llm_provider()
        print(f"[LLM backend: {llm.backend}]")
    print(f"[embedding backend: {prov.backend}]  resumes={list(resumes)}  jds={list(jds)}")
    print()

    # Parse once
    parsed_res = {n: parse_resume(p) for n, p in resumes.items()}
    parsed_jd = {n: parse_jd(extract_text_from_docx(p)) for n, p in jds.items()}

    # Score matrix
    scores = {}
    detail = {}
    for rn, r in parsed_res.items():
        for jn in jds:
            base = run_skill_extraction_pipeline(r, parsed_jd[jn], kw=None, provider=prov)
            if llm is not None:
                gated = match_skills(base["resume_skill_phrases"], base["jd_skill_entries"],
                                     provider=prov, llm_provider=llm)
                matched = gated["matched"]
                validation = gated.get("llm_validation", {})
            else:
                matched = base["matched"]
                validation = {}
            scores[(rn, jn)] = skill_score(base, matched)
            detail[(rn, jn)] = {
                "matched": len(matched),
                "missing": len(base["missing_from_resume"]),
                "jd_phrases": base["summary"]["total_jd_phrases"],
                "rejected": len(validation.get("rejected", [])),
            }

    # Print score matrix
    print("=" * (12 + 8 * len(jds)))
    print(f"SKILL-MATCH SCORE  ({args.mode})")
    print("=" * (12 + 8 * len(jds)))
    hdr = f"{'Resume':<12}" + "".join(f"{j:>8}" for j in jds)
    print(hdr); print("-" * len(hdr))
    for rn in resumes:
        print(f"{rn:<12}" + "".join(f"{scores[(rn, jn)]:>8.3f}" for jn in jds))
    print()

    # Matched/jd counts
    print(f"MATCHED / JD-PHRASES  ({args.mode})")
    print(hdr); print("-" * len(hdr))
    for rn in resumes:
        print(f"{rn:<12}" + "".join(
            f"{str(detail[(rn, jn)]['matched']) + '/' + str(detail[(rn, jn)]['jd_phrases']):>8}"
            for jn in jds))
    print()

    if llm is not None:
        print("LLM-REJECTED (gate) per cell")
        print(hdr); print("-" * len(hdr))
        for rn in resumes:
            print(f"{rn:<12}" + "".join(f"{detail[(rn, jn)]['rejected']:>8}" for jn in jds))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
