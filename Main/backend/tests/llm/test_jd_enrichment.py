"""Sub-phase 1.16 — JD Intelligence LLM enrichment.

Verifies:
  - `analyze_jd(text)` (no provider) → llm_* fields stay None; behavior
    byte-identical to baseline.
  - `analyze_jd(text, llm_provider=mock)` → llm_* fields populated.
  - LLM failure (provider=`none` or transport error) → llm_* stay None and
    pipeline still returns a complete JDIntelligence.
  - `excluded_noise` round-trips into the dataclass.

All tests use ``MockLLMProvider`` — zero real LLM calls. The live-Ollama
smoke (sub-phase 1.17) lives in ``test_jd_enrichment_live.py`` and is
gated by ``@pytest.mark.live_llm``.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.services.jd_intelligence import analyze_jd, JDIntelligence
from app.utils.llm import LLMRequest, _cache_key_for
from app.utils.llm_schemas import JDStructure
from tests.utils.mock_llm import MockLLMProvider


SAMPLE_JD = """Senior Backend Engineer

About the job
We are looking for a Senior Backend Engineer to build distributed services.

Required Skills:
- Python
- PostgreSQL
- Docker
- Kafka

Preferred:
- Kubernetes
- gRPC

Responsibilities:
- Design and own backend services
- Mentor junior engineers
- Drive code quality through reviews

5+ years of experience required.
Bachelor's degree in CS.
"""


def _canned_jd_response():
    return {
        "role_summary": "Senior Backend Engineer",
        "seniority": "senior",
        "responsibilities": [
            "Design and own backend services",
            "Mentor junior engineers",
            "Drive code quality through reviews",
        ],
        "required_skills_clean": ["python", "postgresql", "docker", "kafka"],
        "preferred_skills_clean": ["kubernetes", "grpc"],
        "excluded_noise": ["internal partners", "best practices"],
        "confidence": 0.91,
    }


class _AnyKeyJDMock(MockLLMProvider):
    """Mock that returns the same JD response for any cache key."""

    def __init__(self, response_dict):
        super().__init__(responses={}, model_name="mock-model")
        self._response = response_dict

    def batch_complete_json(self, requests):
        from app.utils.llm_schemas import JDStructure
        out = []
        for req in requests:
            self.usage.add(tokens_in=0, tokens_out=0, cost_usd=0.0)
            out.append(JDStructure.model_validate(self._response))
        return out


# ─── Backward compat ─────────────────────────────────────────────────────────


class TestBackwardCompat:
    def test_no_provider_keeps_llm_fields_none(self):
        result = analyze_jd(SAMPLE_JD)
        assert isinstance(result, JDIntelligence)
        # All llm_* fields must be None when no provider is passed.
        assert result.llm_role_summary is None
        assert result.llm_responsibilities is None
        assert result.llm_seniority is None
        assert result.llm_confidence is None
        assert result.llm_excluded_noise is None

    def test_empty_text_returns_default_object(self):
        result = analyze_jd("")
        assert result.llm_role_summary is None

    def test_deterministic_without_provider(self):
        a = analyze_jd(SAMPLE_JD)
        b = analyze_jd(SAMPLE_JD)
        assert a.to_dict() == b.to_dict()


# ─── Enrichment ──────────────────────────────────────────────────────────────


class TestEnrichmentPopulates:
    def test_llm_fields_populated_with_mock(self):
        mock = _AnyKeyJDMock(_canned_jd_response())
        result = analyze_jd(SAMPLE_JD, llm_provider=mock)
        assert result.llm_role_summary == "Senior Backend Engineer"
        assert result.llm_seniority == "senior"
        assert result.llm_confidence == pytest.approx(0.91)
        assert "Design and own backend services" in result.llm_responsibilities
        assert "internal partners" in result.llm_excluded_noise
        # One LLM call per JD analysis
        assert mock.usage.calls == 1

    def test_baseline_fields_unaffected_by_llm(self):
        """The non-llm_* fields must be IDENTICAL to the no-LLM run."""
        baseline = analyze_jd(SAMPLE_JD).to_dict()
        mock = _AnyKeyJDMock(_canned_jd_response())
        gated = analyze_jd(SAMPLE_JD, llm_provider=mock).to_dict()
        for key in baseline.keys():
            if key.startswith("llm_"):
                continue
            assert baseline[key] == gated[key], f"baseline field {key} changed under LLM"

    def test_to_dict_round_trips_llm_fields(self):
        mock = _AnyKeyJDMock(_canned_jd_response())
        result = analyze_jd(SAMPLE_JD, llm_provider=mock)
        d = result.to_dict()
        assert d["llm_role_summary"] == "Senior Backend Engineer"
        assert d["llm_seniority"] == "senior"
        assert d["llm_excluded_noise"] == ["internal partners", "best practices"]


# ─── Graceful degradation ────────────────────────────────────────────────────


class _AlwaysNoneProvider:
    """LLM provider stand-in that always returns None (e.g. backend=none)."""

    from app.utils.llm import LLMUsage as _U
    usage = _U()
    backend = "none"

    def complete_json(self, **_kwargs):
        return None

    def batch_complete_json(self, requests):
        return [None] * len(requests)


class TestGracefulDegradation:
    def test_provider_returns_none_keeps_llm_fields_none(self):
        result = analyze_jd(SAMPLE_JD, llm_provider=_AlwaysNoneProvider())
        # llm_* fields remain None — engine produces a complete result.
        assert result.llm_role_summary is None
        assert result.llm_responsibilities is None
        # Baseline fields still populated.
        assert result.role_title != ""
        assert isinstance(result.required_skills, list)


# ─── Hallucination guard (cross-reference sub-phase 1.7) ─────────────────────


class TestHallucinationStaysOutOfMatcher:
    """LLM-extracted skills (`llm_excluded_noise`, etc.) must not change
    matched/missing in any downstream consumer. The hallucination guard test
    file (test_no_hallucination_pollution.py) covers the matcher directly;
    this test ensures JDIntelligence carries no plumbing that would let the
    LLM 'recommended skills' leak into required_skills."""

    def test_required_skills_unchanged_by_llm(self):
        baseline = analyze_jd(SAMPLE_JD)
        mock = _AnyKeyJDMock(_canned_jd_response())
        gated = analyze_jd(SAMPLE_JD, llm_provider=mock)
        # The baseline-derived required_skills list MUST NOT change just
        # because the LLM offered a "cleaner" list in required_skills_clean.
        assert baseline.required_skills == gated.required_skills
        # The LLM's clean list is informational only — it lives in
        # llm_* fields, never in `required_skills`.
        assert gated.llm_role_summary is not None  # confirms LLM ran
