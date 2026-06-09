"""Compare embedding backends (TF-IDF vs SBERT) across the benchmark grid.

Runs the skill-match and project-relevance pipelines for every resume × JD
under both backends and prints side-by-side scores, so we can quantify how
much SBERT lifts the semantic + project axes.

Run:  python tests/compare_backends.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from app.services.resume_parser import parse_resume
from app.services.jd_parser import parse_jd
from app.services.jd_intelligence import analyze_jd
from app.services.project_intelligence import analyze_projects
from app.services.skill_matcher import run_skill_extraction_pipeline
from app.utils.file_handling import extract_text_from_docx
from app.utils.embeddings import EmbeddingProvider, BACKEND_TFIDF, BACKEND_SBERT

FIXTURES = HERE / "fixtures"
RESUMES = {
    "Eklavya": FIXTURES / "Eklavya_Singh_Rathore_Resume.pdf",
    "Vignesh": FIXTURES / "VIGNESH B_Resume.pdf",
}
JDS = {f"JD_{i}": FIXTURES / f"JD_{i}.docx" for i in range(1, 6)}


def build_providers():
    providers = {"tfidf": EmbeddingProvider(backend=BACKEND_TFIDF)}
    try:
        sbert = EmbeddingProvider(backend=BACKEND_SBERT)
        _ = sbert.backend  # force load
        providers["sbert"] = sbert
        print("SBERT backend available — comparing TF-IDF vs SBERT.\n")
    except Exception as exc:
        print(f"SBERT NOT available ({exc}); showing TF-IDF only.\n")
    return providers


def main() -> None:
    providers = build_providers()
    parsed_resumes = {n: parse_resume(str(p)) for n, p in RESUMES.items()}
    jd_parsed = {n: parse_jd(extract_text_from_docx(str(p))) for n, p in JDS.items()}
    jd_intel = {n: analyze_jd(extract_text_from_docx(str(p))) for n, p in JDS.items()}

    for label, prov in providers.items():
        print("=" * 78)
        print(f"SKILL-MATCH SCORE — backend = {label}")
        print("=" * 78)
        header = f"{'Resume':<10}" + "".join(f"{j:>10}" for j in JDS)
        print(header); print("-" * len(header))
        for r_name, parsed in parsed_resumes.items():
            cells = []
            for j_name in JDS:
                res = run_skill_extraction_pipeline(parsed, jd_parsed[j_name], kw=None, provider=prov)
                cells.append(f"{res['summary']['skills_score_S_sk']:>10.3f}")
            print(f"{r_name:<10}" + "".join(cells))
        print()

        print("=" * 78)
        print(f"TOP-PROJECT RELEVANCE — backend = {label}")
        print("=" * 78)
        print(header); print("-" * len(header))
        for r_name, parsed in parsed_resumes.items():
            cells = []
            for j_name in JDS:
                proj = analyze_projects(parsed["projects"], jd_intel[j_name].to_dict(), prov)
                cells.append(f"{proj.best_score:>10.3f}")
            print(f"{r_name:<10}" + "".join(cells))
        print()


if __name__ == "__main__":
    main()
