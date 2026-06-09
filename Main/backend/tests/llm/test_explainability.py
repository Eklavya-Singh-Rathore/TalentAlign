"""Sub-phase 1.24 — explainability data layer.

Verifies aggregation from the four engines into a single LLMExplanation,
and the optional polishing LLM call.
"""

from __future__ import annotations

import pytest

from app.services.experience_intelligence import ExperienceIntelligence
from app.services.explainability import (
    LLMExplanation,
    assemble_explanation,
)
from app.services.jd_intelligence import JDIntelligence
from app.services.project_intelligence import ProjectIntelligence
from app.utils.llm_schemas import Explanation
from tests.utils.mock_llm import MockLLMProvider


# ─── Fixtures ────────────────────────────────────────────────────────────────


def _jd_intel():
    return JDIntelligence(
        clean_text="...",
        role_title="Senior Backend Engineer",
        role_confidence="high",
        seniority_level="senior",
        required_skills=["python", "postgres"],
        llm_role_summary="Senior Backend Engineer",
        llm_responsibilities=["Build services", "Mentor"],
        llm_seniority="senior",
        llm_confidence=0.9,
        llm_excluded_noise=["internal partners"],
    )


def _exp_intel():
    return ExperienceIntelligence(
        candidate_category="early_career",
        classification_confidence="medium",
        total_experience_months=18.0,
        llm_candidate_type="early_career",
        llm_relevant_experience_months=14,
        llm_leadership_signals=["Led 2-person team"],
        llm_impact_metrics=["Reduced latency 40%"],
        llm_rationale="Internship + 1 yr full-time on relevant ML pipeline.",
    )


def _proj_intel():
    return ProjectIntelligence(
        project_count=3,
        ranked_projects=[
            {"rank": 1, "title": "Resume Scorer", "final_score": 0.81,
             "similarity_score": 0.75, "llm_relevance": 0.85,
             "llm_rationale": "Direct ML pipeline match.",
             "matched_jd_skills": ["python", "sklearn"]},
            {"rank": 2, "title": "Auto-router", "final_score": 0.62,
             "similarity_score": 0.55, "llm_relevance": 0.7,
             "llm_rationale": "NLP overlap.",
             "matched_jd_skills": ["python"]},
            {"rank": 3, "title": "VERA", "final_score": 0.45,
             "similarity_score": 0.40, "llm_relevance": 0.5,
             "llm_rationale": "Partial overlap on classification.",
             "matched_jd_skills": ["sklearn"]},
        ],
        best_score=0.81,
        embedding_backend="tfidf",
        llm_top_strengths=["NLP pipelines", "ML deployment"],
        llm_top_gaps=["No cloud deployment experience"],
    )


def _match_result_with_validation():
    return {
        "matched": [{"resume_phrase": "python", "jd_phrase": "python"}],
        "unmatched_in_resume": [],
        "missing_from_resume": [],
        "llm_validation": {
            "kept": [{"resume_phrase": "data pipeline", "jd_phrase": "etl",
                      "confidence": 0.85, "reason": "alias"}],
            "rejected": [{"resume_phrase": "deep learning",
                          "jd_phrase": "learning frameworks",
                          "confidence": 0.7, "reason": "shared common word only"}],
            "skipped_reason": None,
            "candidate_count": 2,
        },
    }


# ─── Aggregation (no LLM polishing) ──────────────────────────────────────────


class TestAggregation:
    def test_jd_fields_carried_through(self):
        expl = assemble_explanation(jd_intel=_jd_intel())
        assert expl.jd_role == "Senior Backend Engineer"
        assert expl.jd_responsibilities == ["Build services", "Mentor"]
        assert expl.jd_excluded_noise == ["internal partners"]
        assert expl.jd_seniority_llm == "senior"
        assert expl.jd_seniority_baseline == "senior"
        assert expl.jd_llm_confidence == 0.9

    def test_experience_fields_carried_through(self):
        expl = assemble_explanation(exp_intel=_exp_intel())
        assert expl.candidate_type_baseline == "early_career"
        assert expl.candidate_type_llm == "early_career"
        assert expl.relevant_experience_months == 14
        assert expl.experience_rationale.startswith("Internship")
        assert "Led 2-person team" in expl.leadership_signals
        assert "Reduced latency 40%" in expl.impact_metrics

    def test_project_fields_carried_through(self):
        expl = assemble_explanation(proj_intel=_proj_intel())
        assert len(expl.top_projects) == 3
        assert expl.top_projects[0]["title"] == "Resume Scorer"
        assert expl.top_projects[0]["llm_rationale"] == "Direct ML pipeline match."
        assert expl.top_strengths == ["NLP pipelines", "ML deployment"]
        assert expl.top_gaps == ["No cloud deployment experience"]
        assert expl.embedding_backend == "tfidf"

    def test_top_n_caps(self):
        # Limit to top-2 instead of default 3
        expl = assemble_explanation(proj_intel=_proj_intel(), top_n_projects=2)
        assert len(expl.top_projects) == 2

    def test_validation_fields_carried_through(self):
        expl = assemble_explanation(match_result=_match_result_with_validation())
        assert expl.matches_validated_kept == 1
        assert expl.matches_validated_rejected == 1
        assert expl.rejected_pairs[0]["resume_phrase"] == "deep learning"
        assert expl.validation_skipped_reason is None

    def test_empty_inputs_yield_empty_payload(self):
        expl = assemble_explanation()
        assert expl.jd_role is None
        assert expl.top_projects == []
        assert expl.top_strengths == []
        assert expl.matches_validated_kept == 0
        assert expl.llm_polishing_used is False

    def test_no_llm_polishing_keeps_fields_none(self):
        expl = assemble_explanation(
            jd_intel=_jd_intel(), exp_intel=_exp_intel(), proj_intel=_proj_intel(),
        )
        assert expl.overall_summary is None
        assert expl.next_steps is None
        assert expl.llm_polishing_used is False


# ─── Polishing LLM call ──────────────────────────────────────────────────────


class _AnyKeyExplanationMock(MockLLMProvider):
    def __init__(self, response):
        super().__init__(responses={}, model_name="mock-model")
        self._response = response

    def batch_complete_json(self, requests):
        out = []
        for req in requests:
            self.usage.add(tokens_in=0, tokens_out=0, cost_usd=0.0)
            out.append(Explanation.model_validate(self._response))
        return out


class TestPolishing:
    def _canned(self):
        return {
            "overall_summary": "Strong ML alignment with minor cloud-deployment gap.",
            "top_strengths": ["NLP", "MLOps basics", "Production code"],
            "top_gaps": ["Cloud infra", "Team leadership"],
            "next_steps": ["Earn AWS SAA cert", "Lead a small project"],
        }

    def test_polishing_populates_overall_and_next_steps(self):
        mock = _AnyKeyExplanationMock(self._canned())
        expl = assemble_explanation(
            jd_intel=_jd_intel(), exp_intel=_exp_intel(), proj_intel=_proj_intel(),
            llm_provider=mock,
        )
        assert expl.overall_summary.startswith("Strong")
        assert expl.next_steps == ["Earn AWS SAA cert", "Lead a small project"]
        assert expl.llm_polishing_used is True
        assert mock.usage.calls == 1

    def test_polishing_overrides_strengths_and_gaps(self):
        mock = _AnyKeyExplanationMock(self._canned())
        expl = assemble_explanation(
            proj_intel=_proj_intel(),   # has its own top_strengths/gaps
            llm_provider=mock,
        )
        # Polished list takes precedence
        assert expl.top_strengths == ["NLP", "MLOps basics", "Production code"]
        assert expl.top_gaps == ["Cloud infra", "Team leadership"]


class _AlwaysNone:
    from app.utils.llm import LLMUsage as _U
    usage = _U()
    backend = "none"

    def complete_json(self, **_kw): return None
    def batch_complete_json(self, requests): return [None] * len(requests)


class TestGracefulDegradation:
    def test_polishing_failure_leaves_overall_none(self):
        expl = assemble_explanation(
            jd_intel=_jd_intel(), proj_intel=_proj_intel(),
            llm_provider=_AlwaysNone(),
        )
        assert expl.overall_summary is None
        assert expl.next_steps is None
        assert expl.llm_polishing_used is False
        # Project-level top_strengths still survive as the fallback.
        assert expl.top_strengths == ["NLP pipelines", "ML deployment"]
