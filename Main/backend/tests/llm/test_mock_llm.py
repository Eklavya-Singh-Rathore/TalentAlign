"""Sub-phase 1.6 — MockLLMProvider returns canned data, raises on unknowns."""

from __future__ import annotations

import pytest

from app.utils.llm import LLMRequest, _cache_key_for
from app.utils.llm_schemas import JDStructure
from tests.utils.mock_llm import MockLLMProvider


def _jd_response():
    return {
        "role_summary": "Backend Engineer",
        "seniority": "mid",
        "responsibilities": ["Build services"],
        "required_skills_clean": ["python"],
        "preferred_skills_clean": [],
        "excluded_noise": [],
        "confidence": 0.85,
    }


class TestMockLLMProvider:
    def test_canned_response_returned(self):
        key = _cache_key_for("mock-model", "sys", "usr", "JDStructure")
        mock = MockLLMProvider(responses={key: _jd_response()})
        out = mock.complete_json(system="sys", user="usr", schema=JDStructure)
        assert out is not None
        assert out.role_summary == "Backend Engineer"
        assert out.seniority == "mid"

    def test_unknown_key_raises_loudly(self):
        mock = MockLLMProvider(responses={})
        with pytest.raises(KeyError, match="MockLLMProvider has no canned response"):
            mock.complete_json(system="s", user="u", schema=JDStructure)

    def test_allow_default_empty_constructs_minimum(self):
        # JDStructure has required fields (role_summary, seniority, confidence)
        # without defaults, so default-empty falls through to KeyError.
        mock = MockLLMProvider(responses={}, allow_default_empty=True)
        with pytest.raises(KeyError):
            mock.complete_json(system="s", user="u", schema=JDStructure)

    def test_batched_round_trip(self):
        key1 = _cache_key_for("mock-model", "s1", "u1", "JDStructure")
        key2 = _cache_key_for("mock-model", "s2", "u2", "JDStructure")
        r1 = _jd_response()
        r2 = _jd_response()
        r2["role_summary"] = "Senior Engineer"
        mock = MockLLMProvider(responses={key1: r1, key2: r2})
        out = mock.batch_complete_json([
            LLMRequest(system="s1", user="u1", schema=JDStructure),
            LLMRequest(system="s2", user="u2", schema=JDStructure),
        ])
        assert len(out) == 2
        assert out[0].role_summary == "Backend Engineer"
        assert out[1].role_summary == "Senior Engineer"

    def test_backend_is_mock(self):
        assert MockLLMProvider().backend == "mock"

    def test_usage_increments_on_canned_hit(self):
        key = _cache_key_for("mock-model", "s", "u", "JDStructure")
        mock = MockLLMProvider(responses={key: _jd_response()})
        mock.complete_json(system="s", user="u", schema=JDStructure)
        assert mock.usage.calls == 1
