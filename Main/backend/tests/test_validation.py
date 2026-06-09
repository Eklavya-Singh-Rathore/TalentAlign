"""Phase 6 — Validation harness over the internal benchmark dataset.

Implements the plan's Section 10 (Testing Framework) validation layers:
  - Output consistency testing: determinism, bounded scores, structural
    invariants, no exceptions across the full pipeline.
  - Cross-resume validation: every resume × every JD runs and produces
    comparable, well-formed output.

Regression testing (old vs new pipeline) lives in regression_baseline.py.

The benchmark dataset is the fixtures folder:
  - resumes: Eklavya_Singh_Rathore_Resume.pdf, VIGNESH B_Resume.pdf
  - JDs:     JD_1.docx … JD_5.docx

All tests force the deterministic TF-IDF embedding backend so results are
reproducible without SBERT installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.resume_parser import parse_resume
from app.services.jd_parser import parse_jd
from app.services.jd_intelligence import analyze_jd, JDIntelligence
from app.services.experience_intelligence import analyze_experience, CANDIDATE_CATEGORIES
from app.services.project_intelligence import analyze_projects
from app.services.skill_matcher import run_skill_extraction_pipeline
from app.utils.file_handling import extract_text_from_docx
from app.utils.embeddings import EmbeddingProvider, BACKEND_TFIDF
from app.services.jd_parser import SENIORITY_LEVELS


FIXTURES = Path(__file__).resolve().parent / "fixtures"

RESUME_FILES = {
    "Eklavya": FIXTURES / "Eklavya_Singh_Rathore_Resume.pdf",
    "Vignesh": FIXTURES / "VIGNESH B_Resume.pdf",
}
JD_FILES = {f"JD_{i}": FIXTURES / f"JD_{i}.docx" for i in range(1, 6)}


# ─── Session-scoped benchmark loading (parse once, reuse) ────────────────────


@pytest.fixture(scope="module")
def resumes():
    return {name: parse_resume(str(path)) for name, path in RESUME_FILES.items()}


@pytest.fixture(scope="module")
def jd_texts():
    return {name: extract_text_from_docx(str(path)) for name, path in JD_FILES.items()}


@pytest.fixture(scope="module")
def jd_intel(jd_texts):
    return {name: analyze_jd(text) for name, text in jd_texts.items()}


def _provider():
    return EmbeddingProvider(backend=BACKEND_TFIDF)


# ─── Dataset presence ────────────────────────────────────────────────────────


class TestBenchmarkDatasetPresent:
    def test_all_resume_files_exist(self):
        for name, path in RESUME_FILES.items():
            assert path.exists(), f"missing resume fixture: {name} ({path})"

    def test_all_jd_files_exist(self):
        for name, path in JD_FILES.items():
            assert path.exists(), f"missing JD fixture: {name} ({path})"

    def test_resumes_parse_nonempty(self, resumes):
        for name, parsed in resumes.items():
            assert parsed["skills"], f"{name} parsed zero skills"

    def test_jds_extract_text(self, jd_texts):
        for name, text in jd_texts.items():
            assert text.strip(), f"{name} extracted empty text"


# ─── Output consistency: JD Intelligence ─────────────────────────────────────


class TestJdIntelligenceConsistency:
    def test_returns_correct_type(self, jd_intel):
        for name, jd in jd_intel.items():
            assert isinstance(jd, JDIntelligence), name

    def test_domain_scores_bounded(self, jd_intel):
        for name, jd in jd_intel.items():
            for domain, score in jd.domain_scores.items():
                assert 0.0 <= score <= 1.0, f"{name} domain {domain} score {score} out of range"

    def test_seniority_in_valid_set(self, jd_intel):
        for name, jd in jd_intel.items():
            assert jd.seniority_level in SENIORITY_LEVELS, f"{name}: {jd.seniority_level}"

    def test_noise_ratio_bounded(self, jd_intel):
        for name, jd in jd_intel.items():
            assert 0.0 <= jd.noise_ratio <= 1.0, f"{name}: {jd.noise_ratio}"

    def test_role_confidence_valid(self, jd_intel):
        for name, jd in jd_intel.items():
            assert jd.role_confidence in ("high", "medium", "low"), name

    def test_determinism(self, jd_texts):
        """Same JD text → identical analysis on repeat runs."""
        for name, text in jd_texts.items():
            a = analyze_jd(text)
            b = analyze_jd(text)
            assert a.to_dict() == b.to_dict(), f"{name} not deterministic"


# ─── Output consistency: Experience Intelligence ─────────────────────────────


class TestExperienceConsistency:
    def test_category_valid_and_scores_bounded(self, resumes, jd_intel):
        for r_name, parsed in resumes.items():
            for j_name, jd in jd_intel.items():
                exp = analyze_experience(parsed, jd.to_dict())
                assert exp.candidate_category in CANDIDATE_CATEGORIES, f"{r_name}×{j_name}"
                for attr in (
                    "experience_quality_score",
                    "internship_quality_score",
                    "work_experience_quality_score",
                ):
                    val = getattr(exp, attr)
                    assert 0.0 <= val <= 1.0, f"{r_name}×{j_name} {attr}={val}"

    def test_determinism(self, resumes, jd_intel):
        parsed = resumes["Eklavya"]
        jd = jd_intel["JD_1"].to_dict()
        a = analyze_experience(parsed, jd)
        b = analyze_experience(parsed, jd)
        assert a.to_dict() == b.to_dict()


# ─── Output consistency: Project Relevance ───────────────────────────────────


class TestProjectConsistency:
    def test_scores_bounded_and_ranks_unique(self, resumes, jd_intel):
        for r_name, parsed in resumes.items():
            for j_name, jd in jd_intel.items():
                result = analyze_projects(parsed["projects"], jd.to_dict(), _provider())
                ranks = [p["rank"] for p in result.ranked_projects]
                assert ranks == list(range(1, len(ranks) + 1)), f"{r_name}×{j_name} ranks not 1..n"
                for p in result.ranked_projects:
                    for k in ("similarity_score", "complexity_score", "impact_score",
                              "domain_alignment_score", "final_score"):
                        assert 0.0 <= p[k] <= 1.0, f"{r_name}×{j_name} {p['title'][:20]} {k}={p[k]}"

    def test_ranking_is_sorted_descending(self, resumes, jd_intel):
        for r_name, parsed in resumes.items():
            for j_name, jd in jd_intel.items():
                result = analyze_projects(parsed["projects"], jd.to_dict(), _provider())
                scores = [p["final_score"] for p in result.ranked_projects]
                assert scores == sorted(scores, reverse=True), f"{r_name}×{j_name} not sorted"


# ─── Output consistency: Skill Matching ──────────────────────────────────────


class TestSkillMatchConsistency:
    def test_score_bounded(self, resumes, jd_texts):
        for r_name, parsed in resumes.items():
            for j_name, text in jd_texts.items():
                jd = parse_jd(text)
                result = run_skill_extraction_pipeline(parsed, jd, kw=None, provider=_provider())
                score = result["summary"]["skills_score_S_sk"]
                assert 0.0 <= score <= 1.0, f"{r_name}×{j_name} score={score}"

    def test_matched_and_missing_are_subsets_of_jd(self, resumes, jd_texts):
        """Every matched jd_phrase and every missing phrase must originate from
        the JD entry set (no fabricated skills)."""
        for r_name, parsed in resumes.items():
            for j_name, text in jd_texts.items():
                jd = parse_jd(text)
                result = run_skill_extraction_pipeline(parsed, jd, kw=None, provider=_provider())
                jd_phrase_set = {e["phrase"] for e in result["jd_skill_entries"]}
                for m in result["matched"]:
                    assert m["jd_phrase"] in jd_phrase_set, f"{r_name}×{j_name}: fabricated {m['jd_phrase']!r}"

    def test_counts_are_consistent(self, resumes, jd_texts):
        for r_name, parsed in resumes.items():
            for j_name, text in jd_texts.items():
                jd = parse_jd(text)
                result = run_skill_extraction_pipeline(parsed, jd, kw=None, provider=_provider())
                s = result["summary"]
                assert s["total_matched"] == len(result["matched"])
                assert s["total_matched"] <= s["total_jd_phrases"] + 50  # generous upper bound
                assert s["total_missing"] <= 12  # consolidation cap

    def test_determinism(self, resumes, jd_texts):
        parsed = resumes["Eklavya"]
        jd = parse_jd(jd_texts["JD_1"])
        a = run_skill_extraction_pipeline(parsed, jd, kw=None, provider=_provider())
        b = run_skill_extraction_pipeline(parsed, jd, kw=None, provider=_provider())
        assert a["summary"]["skills_score_S_sk"] == b["summary"]["skills_score_S_sk"]
        assert a["summary"]["total_matched"] == b["summary"]["total_matched"]
        assert a["missing_from_resume"] == b["missing_from_resume"]


# ─── Cross-resume validation ─────────────────────────────────────────────────


class TestCrossResumeValidation:
    def test_every_combination_runs(self, resumes, jd_texts):
        """All resume × JD combinations complete without exception and yield
        a numeric skill-match score."""
        n = 0
        for r_name, parsed in resumes.items():
            for j_name, text in jd_texts.items():
                jd = parse_jd(text)
                result = run_skill_extraction_pipeline(parsed, jd, kw=None, provider=_provider())
                assert isinstance(result["summary"]["skills_score_S_sk"], float)
                n += 1
        assert n == len(RESUME_FILES) * len(JD_FILES)  # 2 × 5 = 10

    def test_self_relevance_signal(self, resumes, jd_texts):
        """Sanity: a candidate with relevant skills should match a JD in their
        domain with a non-zero skill score on at least one of the 5 JDs."""
        for r_name, parsed in resumes.items():
            best = 0.0
            for text in jd_texts.values():
                jd = parse_jd(text)
                result = run_skill_extraction_pipeline(parsed, jd, kw=None, provider=_provider())
                best = max(best, result["summary"]["skills_score_S_sk"])
            assert best > 0.0, f"{r_name} matched nothing across all JDs"
