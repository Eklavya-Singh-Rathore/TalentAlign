"""Sub-phase 1.22 — Experience Intelligence LLM enrichment.

Verifies:
  * llm_provider=None → llm_* fields stay None; result byte-identical.
  * llm_provider=mock → all llm_* fields populated; one LLM call.
  * Baseline scoring fields unchanged when LLM runs.
  * Graceful degradation on LLM None.
  * llm_candidate_type agrees with deterministic ±1 tier on fixture.
"""

from __future__ import annotations

import pytest

from app.services.experience_intelligence import (
    CANDIDATE_CATEGORIES,
    ExperienceIntelligence,
    analyze_experience,
)
from app.utils.llm_schemas import ExperienceStructure
from tests.utils.mock_llm import MockLLMProvider


SAMPLE_RESUME = {
    "internships": [
        "Data & Insights Intern - Skypoint",
        "Apr 2026 - Present",
        "Validated daily business reports.",
        "Built Power BI dashboards for healthcare clients.",
    ],
    "work_experience": [],
    "skills": ["python", "sql", "power bi"],
}
SAMPLE_JD = {
    "role_title": "Junior Data Analyst",
    "primary_domain": "data_science",
    "required_skills": ["python", "sql", "tableau"],
    "experience_years": 0,
}


def _canned_experience_response():
    return {
        "candidate_type": "early_career",
        "relevant_experience_months": 2,
        "leadership_signals": [],
        "impact_metrics": ["Validated reports for healthcare clients"],
        "rationale": "Active internship demonstrates basic data-analyst competence "
                     "but minimal relevant experience yet.",
    }


class _AnyKeyExperienceMock(MockLLMProvider):
    def __init__(self, response_dict):
        super().__init__(responses={}, model_name="mock-model")
        self._response = response_dict

    def batch_complete_json(self, requests):
        out = []
        for req in requests:
            self.usage.add(tokens_in=0, tokens_out=0, cost_usd=0.0)
            out.append(ExperienceStructure.model_validate(self._response))
        return out


# ─── Backward compat ─────────────────────────────────────────────────────────


class TestBackwardCompat:
    def test_no_provider_keeps_llm_fields_none(self):
        result = analyze_experience(SAMPLE_RESUME, SAMPLE_JD)
        assert isinstance(result, ExperienceIntelligence)
        assert result.llm_candidate_type is None
        assert result.llm_relevant_experience_months is None
        assert result.llm_leadership_signals is None
        assert result.llm_impact_metrics is None
        assert result.llm_rationale is None

    def test_empty_resume_keeps_llm_fields_none(self):
        result = analyze_experience({}, SAMPLE_JD)
        assert result.llm_candidate_type is None

    def test_deterministic_without_provider(self):
        a = analyze_experience(SAMPLE_RESUME, SAMPLE_JD)
        b = analyze_experience(SAMPLE_RESUME, SAMPLE_JD)
        assert a.to_dict() == b.to_dict()


# ─── Enrichment ──────────────────────────────────────────────────────────────


class TestEnrichmentPopulates:
    def test_llm_fields_populated_with_mock(self):
        mock = _AnyKeyExperienceMock(_canned_experience_response())
        result = analyze_experience(SAMPLE_RESUME, SAMPLE_JD, llm_provider=mock)
        assert result.llm_candidate_type == "early_career"
        assert result.llm_relevant_experience_months == 2
        assert result.llm_impact_metrics == ["Validated reports for healthcare clients"]
        assert result.llm_rationale.startswith("Active internship")
        assert mock.usage.calls == 1   # one call per analyze_experience

    def test_baseline_fields_unaffected_by_llm(self):
        baseline = analyze_experience(SAMPLE_RESUME, SAMPLE_JD).to_dict()
        mock = _AnyKeyExperienceMock(_canned_experience_response())
        gated = analyze_experience(SAMPLE_RESUME, SAMPLE_JD, llm_provider=mock).to_dict()
        for key in baseline.keys():
            if key.startswith("llm_"):
                continue
            assert baseline[key] == gated[key], f"baseline {key} changed under LLM"

    def test_llm_candidate_type_within_one_tier_of_deterministic(self):
        """The plan calls for LLM classification to agree with deterministic
        ±1 tier on existing fixtures."""
        mock = _AnyKeyExperienceMock(_canned_experience_response())
        result = analyze_experience(SAMPLE_RESUME, SAMPLE_JD, llm_provider=mock)
        det_idx = CANDIDATE_CATEGORIES.index(result.candidate_category)
        llm_idx = CANDIDATE_CATEGORIES.index(result.llm_candidate_type)
        assert abs(det_idx - llm_idx) <= 1


# ─── Graceful degradation ────────────────────────────────────────────────────


class _AlwaysNone:
    from app.utils.llm import LLMUsage as _U
    usage = _U()
    backend = "none"

    def complete_json(self, **_kw): return None
    def batch_complete_json(self, requests): return [None] * len(requests)


class TestGracefulDegradation:
    def test_provider_returns_none_keeps_llm_fields_none(self):
        result = analyze_experience(SAMPLE_RESUME, SAMPLE_JD, llm_provider=_AlwaysNone())
        assert result.llm_candidate_type is None
        # Baseline fields still populated
        assert result.candidate_category in CANDIDATE_CATEGORIES
