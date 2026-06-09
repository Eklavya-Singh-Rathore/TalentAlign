"""Sub-phases 1.8 / 1.9 / 1.10 / 1.11 — LLM validation gate in match_skills.

Coverage:
  * 1.8 — constants are env-overridable; defaults match the plan.
  * 1.9 — MatchValidation schema accepts the expected response shape.
  * 1.10 — gate hook is non-breaking with no provider; with mock provider
           it removes false positives and keeps true positives; rejected
           pairs become unmatched/missing.
  * 1.11 — skipped_reason populated for no_provider, cost_cap, timeout,
           schema_failure, transport_error.

All tests use ``MockLLMProvider`` or a tiny stub — no real LLM calls.
"""

from __future__ import annotations

from typing import Optional

import pytest

from app.services.skill_matcher import (
    LLM_VALIDATE_HIGH,
    LLM_VALIDATE_LOW,
    LLM_VALIDATE_TIERS,
    match_skills,
)
from app.utils.embeddings import BACKEND_TFIDF, EmbeddingProvider
from app.utils.llm import (
    LLMRequest,
    LLMUsage,
    SKIP_COST_CAP,
    SKIP_NO_PROVIDER,
    SKIP_SCHEMA_FAILURE,
    SKIP_TIMEOUT,
    SKIP_TRANSPORT_ERROR,
    _cache_key_for,
)
from app.utils.llm_schemas import MatchValidation, MatchValidationItem
from tests.utils.mock_llm import MockLLMProvider


def _provider():
    return EmbeddingProvider(backend=BACKEND_TFIDF)


# ─── 1.8 — constants & env overrides ─────────────────────────────────────────


class TestConstants:
    def test_defaults_match_plan(self):
        assert LLM_VALIDATE_LOW == 0.45
        assert LLM_VALIDATE_HIGH == 0.75
        assert set(LLM_VALIDATE_TIERS) == {"semantic", "partial"}

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("TALENTALIGN_LLM_VALIDATE_LOW", "0.50")
        monkeypatch.setenv("TALENTALIGN_LLM_VALIDATE_TIERS", "partial")
        # Re-import the module to pick up env overrides
        import importlib
        import app.services.skill_matcher as sm
        importlib.reload(sm)
        assert sm.LLM_VALIDATE_LOW == 0.50
        assert set(sm.LLM_VALIDATE_TIERS) == {"partial"}
        # Restore defaults for other tests
        monkeypatch.delenv("TALENTALIGN_LLM_VALIDATE_LOW")
        monkeypatch.delenv("TALENTALIGN_LLM_VALIDATE_TIERS")
        importlib.reload(sm)


# ─── 1.10 — backward compatibility (no provider == byte-identical) ───────────


class TestBackwardCompat:
    def test_no_llm_provider_keys_unchanged(self):
        """When llm_provider is None, result keys are baseline only."""
        result = match_skills(
            ["python"], [{"phrase": "python", "bucket": "required"}], _provider()
        )
        assert set(result.keys()) == {
            "matched", "unmatched_in_resume", "missing_from_resume"
        }

    def test_llm_provider_adds_llm_validation_key(self):
        """When provider is passed, result gains 'llm_validation'."""
        # Use a mock that no-ops because there are no borderline pairs.
        mock = MockLLMProvider(responses={})
        result = match_skills(
            ["python"], [{"phrase": "python", "bucket": "required"}], _provider(),
            llm_provider=mock,
        )
        assert "llm_validation" in result
        assert result["llm_validation"]["candidate_count"] == 0
        # No call made — exact matches aren't in LLM_VALIDATE_TIERS
        assert mock.usage.calls == 0


# ─── Helper: build a mock that always rejects, always accepts, or mixed ──────


def _mock_returning(verdicts):
    """Build a mock LLM that returns a MatchValidation with the given verdicts.

    verdicts: list of (pair_id, is_valid_match, confidence, reason).
    """
    response = {
        "items": [
            {"pair_id": pid, "is_valid_match": valid, "confidence": conf, "reason": reason}
            for pid, valid, conf, reason in verdicts
        ]
    }
    # The mock returns this for ANY call; we use allow_default_empty
    # equivalent by populating a single key that matches whatever cache_key
    # the gate computes.
    return _AnyKeyMock(response)


class _AnyKeyMock(MockLLMProvider):
    """Mock that returns the same response for any cache key."""

    def __init__(self, response_dict):
        super().__init__(responses={}, model_name="mock-model")
        self._response = response_dict

    def batch_complete_json(self, requests):
        from app.utils.llm_schemas import MatchValidation
        out = []
        for req in requests:
            self.usage.add(tokens_in=0, tokens_out=0, cost_usd=0.0)
            out.append(MatchValidation.model_validate(self._response))
        return out


# ─── 1.10 — gate removes rejected pairs ──────────────────────────────────────


class TestGateRejection:
    def test_partial_rejection_moves_pair_to_unmatched_and_missing(self):
        """A borderline match the LLM rejects must disappear from `matched` and
        its resume/JD phrases must surface in unmatched/missing.

        With TF-IDF, "machine learning" vs "machine learning models" cosine is
        ~0.66, classified as `semantic` (still in LLM_VALIDATE_TIERS, still
        in the [0.45, 0.75] band)."""
        resume = ["machine learning"]
        jd = [{"phrase": "machine learning models", "bucket": "required"}]
        baseline = match_skills(resume, jd, _provider())
        # Baseline produces ONE gated match (semantic OR partial).
        assert len(baseline["matched"]) == 1
        assert baseline["matched"][0]["match_type"] in LLM_VALIDATE_TIERS
        assert LLM_VALIDATE_LOW <= baseline["matched"][0]["similarity"] <= LLM_VALIDATE_HIGH
        assert baseline["missing_from_resume"] == []

        # Now with an LLM that rejects it.
        mock = _mock_returning([("p0", False, 0.85, "Different concept tiers.")])
        result = match_skills(resume, jd, _provider(), llm_provider=mock)
        assert result["matched"] == []
        assert "machine learning" in result["unmatched_in_resume"]
        assert "machine learning models" in result["missing_from_resume"]
        # Validation payload populated
        v = result["llm_validation"]
        assert v["candidate_count"] == 1
        assert len(v["rejected"]) == 1
        assert v["rejected"][0]["resume_phrase"] == "machine learning"
        assert v["skipped_reason"] is None

    def test_partial_acceptance_keeps_pair(self):
        resume = ["machine learning"]
        jd = [{"phrase": "machine learning models", "bucket": "required"}]
        mock = _mock_returning([("p0", True, 0.92, "Direct subset relationship.")])
        result = match_skills(resume, jd, _provider(), llm_provider=mock)
        # Pair stays matched, no rejections
        assert len(result["matched"]) == 1
        v = result["llm_validation"]
        assert len(v["kept"]) == 1
        assert len(v["rejected"]) == 0
        assert v["kept"][0]["confidence"] == 0.92

    def test_exact_match_never_gated(self):
        """Exact-tier matches are NEVER sent to the LLM."""
        resume = ["python"]
        jd = [{"phrase": "python", "bucket": "required"}]
        # Even with a mock that would reject everything, exact stays.
        mock = _mock_returning([("p0", False, 0.99, "would reject")])
        result = match_skills(resume, jd, _provider(), llm_provider=mock)
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "exact"
        # Gate ran with zero candidates → zero LLM calls
        assert mock.usage.calls == 0
        assert result["llm_validation"]["candidate_count"] == 0


# ─── 1.11 — skipped_reason telemetry ─────────────────────────────────────────


class _StubProvider:
    """A minimal provider that returns None and lets us preset skipped reasons."""

    def __init__(self, skip_reason: str):
        self.usage = LLMUsage()
        self.usage.record_skip(skip_reason)

    @property
    def backend(self):
        return "stub"

    def batch_complete_json(self, requests):
        return [None] * len(requests)


class TestSkippedReasonTelemetry:
    def _force_borderline_pair(self):
        # As above — produces one partial in band.
        return (["machine learning"],
                [{"phrase": "machine learning models", "bucket": "required"}])

    def test_no_provider_skip_reported(self):
        resume, jd = self._force_borderline_pair()
        result = match_skills(resume, jd, _provider(),
                              llm_provider=_StubProvider(SKIP_NO_PROVIDER))
        v = result["llm_validation"]
        assert v["skipped_reason"] == SKIP_NO_PROVIDER
        # Pair stays matched because we couldn't validate
        assert len(result["matched"]) == 1

    def test_cost_cap_skip_reported(self):
        resume, jd = self._force_borderline_pair()
        result = match_skills(resume, jd, _provider(),
                              llm_provider=_StubProvider(SKIP_COST_CAP))
        assert result["llm_validation"]["skipped_reason"] == SKIP_COST_CAP

    def test_timeout_skip_reported(self):
        resume, jd = self._force_borderline_pair()
        result = match_skills(resume, jd, _provider(),
                              llm_provider=_StubProvider(SKIP_TIMEOUT))
        assert result["llm_validation"]["skipped_reason"] == SKIP_TIMEOUT

    def test_schema_failure_skip_reported(self):
        resume, jd = self._force_borderline_pair()
        result = match_skills(resume, jd, _provider(),
                              llm_provider=_StubProvider(SKIP_SCHEMA_FAILURE))
        assert result["llm_validation"]["skipped_reason"] == SKIP_SCHEMA_FAILURE

    def test_transport_error_skip_reported(self):
        resume, jd = self._force_borderline_pair()
        result = match_skills(resume, jd, _provider(),
                              llm_provider=_StubProvider(SKIP_TRANSPORT_ERROR))
        assert result["llm_validation"]["skipped_reason"] == SKIP_TRANSPORT_ERROR


# ─── 1.10 — multi-pair gate (one batched call, mixed verdicts) ──────────────


class TestBatchedValidation:
    def test_mixed_verdicts_partial_rejection(self):
        # Two borderline pairs (gated tier): keep one, reject the other.
        resume = ["machine learning", "deep learning"]
        jd = [
            {"phrase": "machine learning models", "bucket": "required"},
            {"phrase": "deep learning frameworks", "bucket": "required"},
        ]
        baseline = match_skills(resume, jd, _provider())
        # Baseline: both should be gated-tier matches
        gated_count = sum(
            1 for m in baseline["matched"]
            if m["match_type"] in LLM_VALIDATE_TIERS
            and LLM_VALIDATE_LOW <= m["similarity"] <= LLM_VALIDATE_HIGH
        )
        assert gated_count == 2

        # LLM keeps p0, rejects p1. Order in `matched` is implementation-
        # defined when similarities tie, so test the structural invariants
        # only: 1 kept + 1 rejected, totals balance, one batched call.
        mock = _mock_returning([
            ("p0", True, 0.9, "subset"),
            ("p1", False, 0.6, "different concept tier"),
        ])
        result = match_skills(resume, jd, _provider(), llm_provider=mock)
        assert len(result["matched"]) == 1
        v = result["llm_validation"]
        assert len(v["kept"]) == 1
        assert len(v["rejected"]) == 1
        # Rejected pair's resume phrase → unmatched; JD phrase → missing.
        rejected_resume = v["rejected"][0]["resume_phrase"]
        rejected_jd = v["rejected"][0]["jd_phrase"]
        assert rejected_resume in result["unmatched_in_resume"]
        assert rejected_jd in result["missing_from_resume"]
        # Surviving match corresponds to the kept verdict.
        kept_resume = v["kept"][0]["resume_phrase"]
        assert result["matched"][0]["resume_phrase"] == kept_resume
        # One batched LLM call (not two)
        assert mock.usage.calls == 1

    def test_no_borderline_pairs_zero_calls(self):
        # Only an exact match — gate has zero candidates.
        resume = ["python"]
        jd = [{"phrase": "python", "bucket": "required"}]
        mock = _mock_returning([])
        result = match_skills(resume, jd, _provider(), llm_provider=mock)
        assert mock.usage.calls == 0
        assert result["llm_validation"]["candidate_count"] == 0
