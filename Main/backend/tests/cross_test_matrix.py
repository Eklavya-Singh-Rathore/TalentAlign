"""Cross-test harness: every resume × every JD.

Runs the full upgraded pipeline (parse → JD intelligence → experience →
projects → skill matching) for each resume/JD combination and prints:
  1. Skill-Match Score matrix (the authoritative resume↔JD metric).
  2. Auxiliary signals per cell (matched/JD-phrase counts, experience
     category, top-project relevance).
  3. Per-JD parsing summary (role/domain/seniority/skill counts), to make
     anomalies visible.

Deterministic TF-IDF embedding backend (no SBERT required).

Run:  python tests/cross_test_matrix.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.resume_parser import parse_resume
from app.services.jd_parser import parse_jd
from app.services.jd_intelligence import analyze_jd
from app.services.experience_intelligence import analyze_experience
from app.services.project_intelligence import analyze_projects
from app.services.skill_matcher import run_skill_extraction_pipeline
from app.utils.file_handling import extract_text_from_docx
from app.utils.embeddings import EmbeddingProvider, BACKEND_TFIDF, get_embedding_provider

FIXTURES = HERE / "fixtures"
RESUMES = {
    "Eklavya": FIXTURES / "Eklavya_Singh_Rathore_Resume.pdf",
    "Vignesh": FIXTURES / "VIGNESH B_Resume.pdf",
}
JDS = {f"JD_{i}": FIXTURES / f"JD_{i}.docx" for i in range(1, 6)}


def main() -> None:
    # Use the production (auto-selected) backend: SBERT when installed,
    # else TF-IDF, else token. Reflects real deployment behavior.
    provider = get_embedding_provider()
    print(f"[embedding backend: {provider.backend}]\n")

    # Parse everything once
    parsed_resumes = {name: parse_resume(str(p)) for name, p in RESUMES.items()}
    jd_texts = {name: extract_text_from_docx(str(p)) for name, p in JDS.items()}
    jd_parsed = {name: parse_jd(text) for name, text in jd_texts.items()}
    jd_intel = {name: analyze_jd(text) for name, text in jd_texts.items()}

    # ── Per-JD parsing summary ───────────────────────────────────────────────
    print("=" * 78)
    print("JD PARSING SUMMARY")
    print("=" * 78)
    print(f"{'JD':<6} {'role':<28} {'domain':<14} {'senior':<8} {'req':<4} {'pref':<5} {'opt':<4}")
    print("-" * 78)
    for name in JDS:
        ji = jd_intel[name]
        role = (ji.role_title or "")[:26]
        print(f"{name:<6} {role:<28} {ji.primary_domain:<14} {ji.seniority_level:<8} "
              f"{len(jd_parsed[name]['required_skills']):<4} "
              f"{len(jd_parsed[name]['preferred_skills']):<5} "
              f"{len(jd_parsed[name].get('optional_skills', [])):<4}")
    print()

    # ── Compute the full grid ────────────────────────────────────────────────
    grid = {}  # (resume, jd) -> dict of signals
    for r_name, parsed in parsed_resumes.items():
        for j_name in JDS:
            skill_res = run_skill_extraction_pipeline(
                parsed, jd_parsed[j_name], kw=None, provider=provider
            )
            exp = analyze_experience(parsed, jd_intel[j_name].to_dict())
            proj = analyze_projects(parsed["projects"], jd_intel[j_name].to_dict(), provider)
            grid[(r_name, j_name)] = {
                "skill_score": skill_res["summary"]["skills_score_S_sk"],
                "matched": skill_res["summary"]["total_matched"],
                "jd_phrases": skill_res["summary"]["total_jd_phrases"],
                "exp_cat": exp.candidate_category,
                "proj_best": proj.best_score,
            }

    # ── Matrix 1: Skill-Match Score ──────────────────────────────────────────
    print("=" * 78)
    print("SKILL-MATCH SCORE  (rows = resumes, cols = JDs)  [0.0–1.0]")
    print("=" * 78)
    header = f"{'Resume':<10}" + "".join(f"{j:>10}" for j in JDS)
    print(header)
    print("-" * len(header))
    for r_name in RESUMES:
        row = f"{r_name:<10}" + "".join(
            f"{grid[(r_name, j)]['skill_score']:>10.3f}" for j in JDS
        )
        print(row)
    print()

    # ── Matrix 2: matched / jd_phrases ───────────────────────────────────────
    print("=" * 78)
    print("MATCHED / JD-PHRASE COUNT  (rows = resumes, cols = JDs)")
    print("=" * 78)
    print(header)
    print("-" * len(header))
    for r_name in RESUMES:
        row = f"{r_name:<10}" + "".join(
            f"{str(grid[(r_name, j)]['matched']) + '/' + str(grid[(r_name, j)]['jd_phrases']):>10}"
            for j in JDS
        )
        print(row)
    print()

    # ── Matrix 3: top-project relevance ──────────────────────────────────────
    print("=" * 78)
    print("TOP-PROJECT RELEVANCE (best_score)  (rows = resumes, cols = JDs)")
    print("=" * 78)
    print(header)
    print("-" * len(header))
    for r_name in RESUMES:
        row = f"{r_name:<10}" + "".join(
            f"{grid[(r_name, j)]['proj_best']:>10.3f}" for j in JDS
        )
        print(row)
    print()

    # ── Experience category (resume-level, JD-independent for category) ──────
    print("=" * 78)
    print("EXPERIENCE CATEGORY  (rows = resumes, cols = JDs)")
    print("=" * 78)
    print(header)
    print("-" * len(header))
    for r_name in RESUMES:
        row = f"{r_name:<10}" + "".join(
            f"{grid[(r_name, j)]['exp_cat'][:9]:>10}" for j in JDS
        )
        print(row)
    print()


if __name__ == "__main__":
    main()
