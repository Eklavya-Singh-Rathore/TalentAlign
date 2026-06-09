"""Tests for the ported scoring + improvement + analysis engines (P3.5)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.scoring_engine import (
    COMPONENTS,
    build_relevance_mask,
    compute_academic_score,
    compute_achievements_score,
    compute_all_scores,
    compute_composite_score,
    compute_effective_score,
    compute_internship_score,
    compute_work_exp_score,
    generate_breakdown_table,
    get_match_level,
    normalize_display_score,
    validate_weights,
)
from app.services.improvement_engine import (
    estimate_gap_impacts_pipeline,
    simulate_improvements_pipeline,
)
from app.services.analysis import analyze_resume_jd
from app.services.experience_intelligence import reconcile_internship_work_experience
from app.utils.embeddings import BACKEND_TFIDF, EmbeddingProvider
from app.utils.file_handling import extract_text_from_docx

FIXTURES = Path(__file__).resolve().parent / "fixtures"

EQUAL_WEIGHTS = {
    "skills_weight": 0.35, "projects_weight": 0.25, "internship_weight": 0.15,
    "experience_weight": 0.1, "academics_weight": 0.1, "achievements_weight": 0.05,
}
FULL_SCORES = {"S_sk": 0.8, "S_pr": 0.6, "S_in": 0.4, "S_we": 0.5, "S_ac": 0.9, "S_ah": 0.2}


class TestMatchLevel:
    # Bands now apply to the normalized DISPLAY scale (0-100).
    @pytest.mark.parametrize("score,level", [
        (95, "EXCELLENT"), (75, "GOOD"), (55, "MODERATE"),
        (35, "BELOW AVERAGE"), (10, "POOR"), (0, "POOR"),
    ])
    def test_levels(self, score, level):
        assert get_match_level(score) == level


class TestDisplayNormalization:
    def test_bounds_and_clamping(self):
        assert normalize_display_score(0.0) == 0.0
        assert normalize_display_score(1.0) == 100.0
        assert normalize_display_score(-5) == 0.0
        assert normalize_display_score(5) == 100.0

    def test_monotonic_preserves_ranking(self):
        xs = [0.05, 0.20, 0.30, 0.45, 0.55, 0.70, 0.90]
        ys = [normalize_display_score(x) for x in xs]
        assert ys == sorted(ys)
        assert all(0.0 <= y <= 100.0 for y in ys)

    def test_anchor_points(self):
        assert normalize_display_score(0.30) == 50.0
        assert normalize_display_score(0.45) == 68.0


class TestValidateWeights:
    def test_valid(self):
        assert validate_weights(EQUAL_WEIGHTS) is True

    def test_missing_key(self):
        with pytest.raises(ValueError, match="Missing weight"):
            validate_weights({"skills_weight": 1.0})

    def test_negative(self):
        w = dict(EQUAL_WEIGHTS); w["skills_weight"] = -0.1; w["projects_weight"] = 0.45
        with pytest.raises(ValueError):
            validate_weights(w)


class TestComposite:
    def test_composite_score(self):
        # sum(w_i * s_i)
        expected = sum(EQUAL_WEIGHTS[wk] * FULL_SCORES[sk] for sk, _n, wk in COMPONENTS)
        assert compute_composite_score(FULL_SCORES, EQUAL_WEIGHTS) == pytest.approx(round(expected, 6))

    def test_effective_score_excludes_and_renorms(self):
        # Exclude work_experience + academics → their weight redistributes.
        mask = {"skills": True, "projects": True, "internships": True,
                "work_experience": False, "academics": False, "achievements": True}
        eff, renorm, excluded = compute_effective_score(FULL_SCORES, EQUAL_WEIGHTS, mask)
        # excluded components reported
        names = {e["component"] for e in excluded}
        assert names == {"Work Experience", "Academics"}
        # renormalized active weights sum to ~1.0
        active = renorm["skills_weight"] + renorm["projects_weight"] + renorm["internship_weight"] + renorm["achievements_weight"]
        assert active == pytest.approx(1.0, abs=1e-3)
        assert renorm["experience_weight"] == 0.0 and renorm["academics_weight"] == 0.0
        assert 0.0 <= eff <= 1.0

    def test_breakdown_has_all_six(self):
        mask = {"skills": True, "projects": True, "internships": True,
                "work_experience": False, "academics": False, "achievements": True}
        _eff, renorm, _ = compute_effective_score(FULL_SCORES, EQUAL_WEIGHTS, mask)
        bd = generate_breakdown_table(FULL_SCORES, renorm, mask)
        assert len(bd) == 6
        assert {b["component"] for b in bd} == {c[1] for c in COMPONENTS}
        # excluded components show zero
        we = next(b for b in bd if b["component"] == "Work Experience")
        assert we["score_achieved"] == 0.0 and we["active"] is False


class TestComponentScorers:
    def test_work_exp_no_requirement(self):
        assert compute_work_exp_score(["Engineer - 3 years"], 0) == 1.0

    def test_work_exp_partial(self):
        assert 0.0 < compute_work_exp_score(["Engineer - 2 years"], 5) < 1.0

    def test_work_exp_empty(self):
        assert compute_work_exp_score([], 3) == 0.0

    def test_academic_cgpa(self):
        assert compute_academic_score(["B.Tech CSE, CGPA: 9.0/10"]) == pytest.approx(0.9, abs=1e-3)

    def test_academic_degree_fallback(self):
        assert compute_academic_score(["B.Tech in CS"]) == 0.6

    def test_academic_empty(self):
        assert compute_academic_score([]) == 0.0

    def test_achievements_hackathon_plus_cert(self):
        r = compute_achievements_score(
            achievements=["Won Smart India Hackathon"], certifications=["AWS"], provider=None
        )
        assert r["score"] > 0
        assert "hackathon" in r["achievement_categories"]
        assert r["certification_count"] == 1

    def test_achievements_empty(self):
        assert compute_achievements_score(achievements=[], certifications=[])["score"] == 0.0

    def test_cert_suggestions_only_for_technical_skills(self):
        # Soft/conceptual gaps must not become "obtain a certification in X".
        r = compute_achievements_score(
            achievements=[], certifications=[],
            missing_skills=["analytical reasoning", "mysql", "technical curiosity", "python"],
        )
        joined = " ".join(r["suggested_certifications"])
        assert "mysql" in joined and "python" in joined
        assert "analytical reasoning" not in joined
        assert "technical curiosity" not in joined


class TestImprovementEngine:
    def _report(self):
        # Minimal skill-match report with 2 missing skills.
        return {
            "summary": {"skills_score_S_sk": 0.4, "total_matched": 2, "total_jd_phrases": 4,
                        "weighted_jd_total": 4.0, "match_type_counts": {"exact": 2}},
            "matched": [{"resume_phrase": "python", "jd_phrase": "python", "jd_bucket": "required",
                         "similarity": 1.0, "match_type": "exact"}],
            "missing_from_resume": ["docker", "kubernetes"],
            "jd_skill_entries": [{"phrase": p, "bucket": "required"} for p in ["python", "sql", "docker", "kubernetes"]],
            "resume_skill_phrases": ["python", "sql"],
        }

    def test_gap_pipeline_ranks_and_filters(self):
        scores = {"S_sk": 0.4, "S_pr": 0.5, "S_in": 0.0, "S_we": 0.0, "S_ac": 0.0, "S_ah": 0.0}
        mask = {"skills": True, "projects": True, "internships": True,
                "work_experience": False, "academics": False, "achievements": True}
        gap = estimate_gap_impacts_pipeline(scores, EQUAL_WEIGHTS, self._report(), ["docker", "kubernetes"], mask)
        assert "ranked_gaps" in gap
        assert all(g["impact"] > 0 for g in gap["ranked_gaps"])
        # ranks are 1..n
        assert [g["rank"] for g in gap["ranked_gaps"]] == list(range(1, len(gap["ranked_gaps"]) + 1))

    def test_simulation_pipeline_produces_predicted_scores(self):
        scores = {"S_sk": 0.4, "S_pr": 0.5, "S_in": 0.0, "S_we": 0.0, "S_ac": 0.0, "S_ah": 0.0}
        mask = {"skills": True, "projects": True, "internships": True,
                "work_experience": False, "academics": False, "achievements": True}
        gap = estimate_gap_impacts_pipeline(scores, EQUAL_WEIGHTS, self._report(), ["docker", "kubernetes"], mask)
        sims = simulate_improvements_pipeline(scores, EQUAL_WEIGHTS, gap, self._report(), ["docker", "kubernetes"])
        for s in sims["ranked_simulations"]:
            assert s["new_score"] >= s["current_score"]
            assert s["delta"] > 0
        assert "combined_result" in sims


class TestOrchestrator:
    def _provider(self):
        return EmbeddingProvider(backend=BACKEND_TFIDF)

    def test_full_payload_structure(self):
        jd = extract_text_from_docx(str(FIXTURES / "JD_1.docx"))
        out = analyze_resume_jd(
            str(FIXTURES / "Eklavya_Singh_Rathore_Resume.pdf"), jd,
            provider=self._provider(), llm_provider=None,
        )
        # Required top-level sections present
        for key in ("placement_score", "match_level", "component_breakdown",
                    "skills_analysis", "improvement_suggestions", "recommendations",
                    "resume_extraction", "jd_extraction", "matching_transparency",
                    "debug", "final_summary"):
            assert key in out, key
        assert 0.0 <= out["placement_score"] <= 100.0
        assert len(out["component_breakdown"]) == 6
        assert out["match_level"] in {"EXCELLENT", "GOOD", "MODERATE", "BELOW AVERAGE", "POOR"}

    def test_deterministic_without_llm(self):
        jd = extract_text_from_docx(str(FIXTURES / "JD_3.docx"))
        a = analyze_resume_jd(str(FIXTURES / "VIGNESH B_Resume.pdf"), jd, provider=self._provider())
        b = analyze_resume_jd(str(FIXTURES / "VIGNESH B_Resume.pdf"), jd, provider=self._provider())
        assert a["placement_score"] == b["placement_score"]
        assert a["component_breakdown"] == b["component_breakdown"]

    def test_empty_jd_raises(self):
        with pytest.raises(ValueError):
            analyze_resume_jd(str(FIXTURES / "VIGNESH B_Resume.pdf"), "  ", provider=self._provider())


class TestInternshipSingleSource:
    """Fix #1: internship reclassification is a single source of truth, so the
    scoring engine agrees with the experience-intelligence reclassification."""

    def _provider(self):
        return EmbeddingProvider(backend=BACKEND_TFIDF)

    def test_reconcile_moves_intern_titled_work_entry(self):
        pr = {
            "internships": [],
            "work_experience": ["Data & Insights Intern - Skypoint (3 months): built dashboards"],
        }
        interns, work = reconcile_internship_work_experience(pr)
        assert interns and "Intern" in interns[0]
        assert work == []

    def test_reconcile_trusts_existing_split(self):
        pr = {
            "internships": ["ML Intern - 2 months"],
            "work_experience": ["Software Engineer - 3 years"],
        }
        interns, work = reconcile_internship_work_experience(pr)
        assert interns == ["ML Intern - 2 months"]
        assert work == ["Software Engineer - 3 years"]

    def test_scoring_reads_reconciled_internships(self):
        provider = self._provider()
        parsed_jd = {
            "raw_text": "Data analyst internship: analytics, dashboards, SQL.",
            "rules": {}, "experience_years": 0,
        }
        report = {"summary": {}, "matched": [], "missing_from_resume": []}
        raw = {
            "internships": [],
            "work_experience": ["Data Science Intern - 3 months: analytics, dashboards"],
            "projects": [], "education": [], "achievements": [],
            "certifications": [], "skills": [],
        }
        # Bug reproduction: scoring the raw parsed_resume yields S_in == 0.
        assert compute_all_scores(raw, parsed_jd, report, provider=provider)["S_in"] == 0.0
        # Fix: reconcile first (as the orchestrator now does) → S_in > 0.
        fixed = dict(raw)
        fixed["internships"], fixed["work_experience"] = reconcile_internship_work_experience(raw)
        assert compute_all_scores(fixed, parsed_jd, report, provider=provider)["S_in"] > 0.0

    def test_orchestrator_agrees_on_internship_signal(self):
        """End-to-end: when experience intelligence recognizes internships, the
        scoring engine's S_in must be > 0 (no dual-source disagreement)."""
        jd = extract_text_from_docx(str(FIXTURES / "JD_3.docx"))
        out = analyze_resume_jd(
            str(FIXTURES / "Eklavya_Singh_Rathore_Resume.pdf"), jd,
            provider=self._provider(), llm_provider=None,
        )
        if out["experience_intelligence"]["internship_count"] > 0:
            assert out["component_scores"]["S_in"] > 0.0
            assert out["resume_extraction"]["internships"]


class TestAchievementDynamicActivation:
    """Proposal 2: the Achievements/Certifications component is deactivated (and
    its weight redistributed) only when the resume has neither achievements nor
    certifications; otherwise it scores with the existing capped logic."""

    def test_mask_inactive_when_no_achievements_or_certs(self):
        mask = build_relevance_mask({"rules": {}}, {"achievements": [], "certifications": []})
        assert mask["achievements"] is False

    def test_mask_active_with_certs_only(self):
        mask = build_relevance_mask({"rules": {}}, {"achievements": [], "certifications": ["AWS"]})
        assert mask["achievements"] is True

    def test_mask_active_with_achievements_only(self):
        mask = build_relevance_mask({"rules": {}}, {"achievements": ["Won hackathon"], "certifications": []})
        assert mask["achievements"] is True

    def test_weight_redistributes_when_deactivated(self):
        # With achievements inactive, its weight flows to the active components
        # and the active (non-zero) renormalized weights still sum to 1.0.
        mask = build_relevance_mask({"rules": {}}, {"achievements": [], "certifications": []})
        _eff, renorm, excluded = compute_effective_score(FULL_SCORES, EQUAL_WEIGHTS, mask)
        assert renorm["achievements_weight"] == 0.0
        assert "Achievements_Certifications" in {e["component"] for e in excluded}
        assert sum(v for v in renorm.values() if v > 0) == pytest.approx(1.0, abs=1e-3)

    def test_mask_active_when_jd_requires_achievements_even_if_absent(self):
        # Guard: an explicit JD achievements requirement keeps the component
        # active (scored 0) even when the resume has none, so the gap penalizes.
        mask = build_relevance_mask(
            {"rules": {"requires_achievements": True}},
            {"achievements": [], "certifications": []},
        )
        assert mask["achievements"] is True


class TestProposal4ExperienceModel:
    """Proposal 4: role-based internship counts + internship->experience bridge."""

    def _prov(self):
        return EmbeddingProvider(backend=BACKEND_TFIDF)

    def test_internship_count_is_role_based(self):
        prov = self._prov()
        jd = "data internship analytics dashboards"
        one_role = ["Data Intern", "Jan 2023 - Jun 2023",
                    "- built dashboards", "- analytics", "- more analytics"]
        two_roles = ["Data Intern", "Jan 2023 - Jun 2023", "- built dashboards",
                     "ML Intern", "Jul 2023 - Dec 2023", "- trained models"]
        # Two dated roles must out-score one role on the count component, instead
        # of both saturating on entry-line count.
        assert compute_internship_score(two_roles, jd, prov) > compute_internship_score(one_role, jd, prov)

    def test_internship_bridges_experience_for_freshers(self):
        # No work experience, but a year-long internship → partial (non-zero) credit.
        s = compute_work_exp_score([], 2, internships=["Data Intern", "Jan 2023 - Jan 2024"])
        assert 0.0 < s < 1.0

    def test_professional_experience_outweighs_internship(self):
        # Same tenure: professional work yields higher S_we than internship-only.
        work_only = compute_work_exp_score(["Engineer", "Jan 2022 - Jan 2024"], 2)
        intern_only = compute_work_exp_score([], 2, internships=["Intern", "Jan 2022 - Jan 2024"])
        assert work_only > intern_only

    def test_no_experience_no_internship_is_zero(self):
        assert compute_work_exp_score([], 2, internships=[]) == 0.0
