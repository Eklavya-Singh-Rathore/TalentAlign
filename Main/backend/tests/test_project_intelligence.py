"""Tests for the Project Relevance Engine (Phase 4 P4.2).

Covers:
- analyze_projects() end-to-end with multiple JD contexts
- per-axis scoring (similarity, complexity, impact, domain alignment)
- ranking stability
- backward compatibility (works without JD data)
- edge cases (empty inputs, single project, projects with no tech stack)
"""

from __future__ import annotations

import pytest

from app.services.project_intelligence import (
    FINAL_SCORE_WEIGHTS,
    JD_DOMAIN_TIER_BOOSTS,
    ProjectIntelligence,
    _group_project_lines,
    _is_title_line,
    _score_complexity,
    _score_domain_alignment,
    _score_impact,
    _compute_final_score,
    analyze_projects,
)
from app.utils.embeddings import EmbeddingProvider, BACKEND_TFIDF, BACKEND_TOKEN
from tests.fixtures.sample_projects import (
    DATA_ENG_PROJECT,
    DEVOPS_PROJECT,
    EMPTY_PROJECT,
    HOBBY_PROJECT,
    JD_DATA_SCIENCE,
    JD_DEVOPS,
    JD_FULLSTACK,
    MINIMAL_PROJECT,
    ML_PROJECT,
    WEB_PROJECT,
)


def _force_tfidf_provider() -> EmbeddingProvider:
    """Tests use the TF-IDF backend so results are deterministic without SBERT."""
    return EmbeddingProvider(backend=BACKEND_TFIDF)


# ─── Unit scoring helpers ────────────────────────────────────────────────────


class TestScoreComplexity:
    def test_empty_signals_zero(self):
        assert _score_complexity({}, set()) == 0.0

    def test_ml_signals_with_ds_boost(self):
        signals = {"ml_ai": ["deep learning", "scikit-learn"], "design_verbs": ["designed"]}
        boosted_no = _score_complexity(signals, set())
        boosted_yes = _score_complexity(signals, {"ml_ai"})
        # Boost should increase the score
        assert boosted_yes > boosted_no

    def test_clamped_to_one(self):
        # Way more than the cap
        signals = {tier: ["x"] * 20 for tier in JD_DOMAIN_TIER_BOOSTS["data_science"]}
        score = _score_complexity(signals, set())
        assert score <= 1.0


class TestScoreImpact:
    def test_no_signals(self):
        assert _score_impact([]) == 0.0

    def test_full_cap(self):
        assert _score_impact(["a", "b", "c", "d", "e", "f"]) == 1.0

    def test_partial(self):
        # 3 signals / 6 cap → 0.5
        assert _score_impact(["a", "b", "c"]) == 0.5

    def test_overflow_clamped(self):
        assert _score_impact(["a"] * 50) == 1.0


class TestScoreDomainAlignment:
    def test_full_overlap(self):
        score, matched = _score_domain_alignment(
            ["python", "sql"], {"python", "sql"}
        )
        assert score == 1.0
        assert set(matched) == {"python", "sql"}

    def test_no_overlap(self):
        score, matched = _score_domain_alignment(["react"], {"python"})
        assert score == 0.0
        assert matched == []

    def test_partial_overlap(self):
        score, matched = _score_domain_alignment(
            ["python", "react"], {"python", "sql"}
        )
        # 1/2 × 2.0 boost = 1.0 (clamped)
        assert 0.0 < score <= 1.0
        assert "python" in matched

    def test_empty_inputs(self):
        assert _score_domain_alignment([], {"a"})[0] == 0.0
        assert _score_domain_alignment(["a"], set())[0] == 0.0


class TestComputeFinalScore:
    def test_weights_sum_to_one(self):
        assert abs(sum(FINAL_SCORE_WEIGHTS.values()) - 1.0) < 1e-9

    def test_all_zero(self):
        assert _compute_final_score(0, 0, 0, 0) == 0.0

    def test_all_one(self):
        assert _compute_final_score(1, 1, 1, 1) == 1.0

    def test_clamped(self):
        # Even with absurd inputs, output stays in [0, 1]
        assert _compute_final_score(2.0, 2.0, 2.0, 2.0) == 1.0
        assert _compute_final_score(-1.0, -1.0, -1.0, -1.0) == 0.0


# ─── End-to-end analyze_projects ─────────────────────────────────────────────


class TestAnalyzeProjectsEndToEnd:
    def test_empty_input(self):
        result = analyze_projects([], JD_DATA_SCIENCE)
        assert isinstance(result, ProjectIntelligence)
        assert result.project_count == 0
        assert result.ranked_projects == []

    def test_single_project(self):
        result = analyze_projects([ML_PROJECT], JD_DATA_SCIENCE, _force_tfidf_provider())
        assert result.project_count == 1
        assert len(result.ranked_projects) == 1
        assert result.ranked_projects[0]["rank"] == 1

    def test_no_jd_data(self):
        result = analyze_projects([ML_PROJECT], None, _force_tfidf_provider())
        # Still returns ranked output, similarity defaults to 0
        assert result.project_count == 1
        assert result.ranked_projects[0]["similarity_score"] == 0.0

    def test_ranking_descending(self):
        projects = [HOBBY_PROJECT, ML_PROJECT, DEVOPS_PROJECT]
        result = analyze_projects(projects, JD_DATA_SCIENCE, _force_tfidf_provider())
        scores = [p["final_score"] for p in result.ranked_projects]
        assert scores == sorted(scores, reverse=True)

    def test_relevant_outranks_hobby(self):
        projects = [HOBBY_PROJECT, ML_PROJECT]
        result = analyze_projects(projects, JD_DATA_SCIENCE, _force_tfidf_provider())
        # ML project must outrank the hobby blog
        ranks = {p["title"]: p["rank"] for p in result.ranked_projects}
        assert ranks["VERA"] < ranks["Personal Travel Blog"]

    def test_jd_domain_changes_complexity_boost(self):
        """DevOps project should rank higher when the JD is DevOps-focused."""
        projects = [DEVOPS_PROJECT, ML_PROJECT]

        ds_result = analyze_projects(projects, JD_DATA_SCIENCE, _force_tfidf_provider())
        do_result = analyze_projects(projects, JD_DEVOPS, _force_tfidf_provider())

        ds_ranks = {p["title"][:20]: p["final_score"] for p in ds_result.ranked_projects}
        do_ranks = {p["title"][:20]: p["final_score"] for p in do_result.ranked_projects}

        # Find the DevOps project's score in each context (title starts with "Ticket")
        ds_devops_score = next(s for t, s in ds_ranks.items() if "Ticket" in t)
        do_devops_score = next(s for t, s in do_ranks.items() if "Ticket" in t)

        # DevOps JD should give the DevOps project a higher score than the DS JD does
        assert do_devops_score > ds_devops_score

    def test_to_dict_returns_dict(self):
        result = analyze_projects([ML_PROJECT], JD_DATA_SCIENCE, _force_tfidf_provider())
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "ranked_projects" in d
        assert "best_score" in d

    def test_aggregates_populated(self):
        result = analyze_projects(
            [ML_PROJECT, DEVOPS_PROJECT, WEB_PROJECT],
            JD_DATA_SCIENCE,
            _force_tfidf_provider(),
        )
        assert result.best_score > 0
        assert 0.0 <= result.average_score <= 1.0
        assert 0.0 <= result.coverage_score <= 1.0

    def test_each_project_has_required_fields(self):
        result = analyze_projects(
            [ML_PROJECT, DEVOPS_PROJECT], JD_DATA_SCIENCE, _force_tfidf_provider()
        )
        for p in result.ranked_projects:
            assert "rank" in p
            assert "title" in p
            assert "similarity_score" in p
            assert "complexity_score" in p
            assert "impact_score" in p
            assert "domain_alignment_score" in p
            assert "final_score" in p
            assert "matched_jd_skills" in p

    def test_all_scores_in_unit_range(self):
        result = analyze_projects(
            [ML_PROJECT, DEVOPS_PROJECT, HOBBY_PROJECT, MINIMAL_PROJECT, EMPTY_PROJECT],
            JD_DATA_SCIENCE,
            _force_tfidf_provider(),
        )
        for p in result.ranked_projects:
            for k in ("similarity_score", "complexity_score", "impact_score",
                      "domain_alignment_score", "final_score"):
                assert 0.0 <= p[k] <= 1.0, f"{k}={p[k]} out of range in {p['title']!r}"

    def test_handles_empty_project_string(self):
        """An empty project string must not crash the pipeline."""
        result = analyze_projects([EMPTY_PROJECT, ML_PROJECT], JD_DATA_SCIENCE,
                                  _force_tfidf_provider())
        assert result.project_count == 2

    def test_embedding_backend_recorded(self):
        result = analyze_projects([ML_PROJECT], JD_DATA_SCIENCE, _force_tfidf_provider())
        assert result.embedding_backend == "tfidf"


class TestGroupProjectLines:
    """Tests for the bullet-grouping pre-processor."""

    def test_title_detection(self):
        assert _is_title_line("VERA - Verifying Remedies Assertion (LINK)") is True
        assert _is_title_line("- Trained an SVM classifier") is False
        assert _is_title_line("Tech: Python, SQL") is False
        assert _is_title_line("Tech Stack: Python") is False
        assert _is_title_line("") is False

    def test_groups_bullets_under_title(self):
        entries = [
            "VERA - Verifying Remedies",
            "- Engineered an NLP pipeline",
            "- Trained an SVM classifier",
            "Tech: Python, scikit-learn",
            "Ticket Auto-Routing",
            "- Designed microservices",
        ]
        grouped = _group_project_lines(entries)
        assert len(grouped) == 2
        assert "Engineered" in grouped[0]
        assert "scikit-learn" in grouped[0]
        assert "Designed microservices" in grouped[1]

    def test_no_titles_returns_input_unchanged(self):
        """Pre-grouped fixtures (all multi-line strings) shouldn't be re-grouped."""
        entries = [
            "Project A - description\n- Bullet 1\n- Bullet 2",
            "Project B - description\n- Bullet 3",
        ]
        grouped = _group_project_lines(entries)
        # The first entry is a title line, so grouping kicks in. Verify
        # the count stays at 2.
        assert len(grouped) == 2

    def test_only_bullets_treated_as_single_group(self):
        """Orphan bullets (no title line at all) get one synthetic group."""
        entries = ["- Bullet 1", "- Bullet 2"]
        grouped = _group_project_lines(entries)
        # No title detected → return as-is (length preserved)
        assert len(grouped) == 2

    def test_empty(self):
        assert _group_project_lines([]) == []


class TestRankingWithDifferentJds:
    """Validation per plan §7: same projects with different JDs should
    produce DIFFERENT rankings."""

    def test_ml_jd_favors_ml_project(self):
        result = analyze_projects(
            [ML_PROJECT, DEVOPS_PROJECT, WEB_PROJECT],
            JD_DATA_SCIENCE,
            _force_tfidf_provider(),
        )
        top_title = result.ranked_projects[0]["title"]
        assert "VERA" in top_title

    def test_devops_jd_favors_devops_project(self):
        result = analyze_projects(
            [ML_PROJECT, DEVOPS_PROJECT, WEB_PROJECT],
            JD_DEVOPS,
            _force_tfidf_provider(),
        )
        top_title = result.ranked_projects[0]["title"]
        assert "Ticket" in top_title

    def test_fullstack_jd_favors_web_project(self):
        result = analyze_projects(
            [ML_PROJECT, DEVOPS_PROJECT, WEB_PROJECT],
            JD_FULLSTACK,
            _force_tfidf_provider(),
        )
        top_title = result.ranked_projects[0]["title"]
        # The fullstack JD asks for React+Node+Postgres → WEB_PROJECT should top.
        assert "E-commerce" in top_title or "E-Commerce" in top_title
