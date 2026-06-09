"""Sub-phases 1.1, 1.3, 1.4, 1.5 — LLMProvider core + cache + cost cap + retry.

Covers:
  - 1.1: skeleton + cascade resolver + singleton.
  - 1.3: cache hits (LRU + disk).
  - 1.4: cost-cap skip, schema-failure reformat-retry, telemetry counters.
  - 1.5: Ollama adapter wired but not invoked here (live test under -m live_llm).

All deterministic — no real Ollama / Groq calls. The Ollama and Groq
internals are exercised by patching ``httpx`` and the ``groq.Groq`` client.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from pydantic import BaseModel, Field

from app.utils.llm import (
    BACKEND_GROQ,
    BACKEND_GEMINI,
    BACKEND_MOCK,
    BACKEND_NONE,
    LLMProvider,
    SKIP_COST_CAP,
    SKIP_NO_PROVIDER,
    SKIP_SCHEMA_FAILURE,
    SKIP_TIMEOUT,
    SKIP_TRANSPORT_ERROR,
    _cache_key_for,
    _cost_for,
    get_llm_provider,
    reset_default_provider,
)
from app.utils.llm_schemas import JDStructure, MatchValidation, MatchValidationItem


# ── A tiny test schema with defaults so the 'none' path can short-circuit ──

class Tiny(BaseModel):
    answer: str = Field(default="x")


# ─── 1.1 — backend resolution ────────────────────────────────────────────────


class TestBackendResolution:
    def test_explicit_none(self):
        p = LLMProvider(backend=BACKEND_NONE)
        assert p.backend == BACKEND_NONE

    def test_explicit_mock(self):
        p = LLMProvider(backend=BACKEND_MOCK)
        assert p.backend == BACKEND_MOCK

    def test_groq_without_key_degrades_to_none(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        p = LLMProvider(backend=BACKEND_GROQ)
        assert p.backend == BACKEND_NONE

    def test_explicit_gemini(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        p = LLMProvider(backend=BACKEND_GEMINI)
        assert p.backend == BACKEND_GEMINI

    def test_gemini_without_key_degrades_to_none(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        p = LLMProvider(backend=BACKEND_GEMINI)
        assert p.backend == BACKEND_NONE

    def test_auto_with_gemini_key(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.delenv("LLM_BACKEND", raising=False)
        p = LLMProvider()
        assert p.backend == BACKEND_GEMINI

    def test_auto_without_gemini_key_degrades_to_none(self, monkeypatch):
        monkeypatch.delenv("LLM_BACKEND", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        p = LLMProvider()
        assert p.backend == BACKEND_NONE

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("LLM_BACKEND", "none")
        p = LLMProvider()  # auto, but env wins
        assert p.backend == BACKEND_NONE

    def test_invalid_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            LLMProvider(backend="nope")

    def test_singleton(self, monkeypatch):
        reset_default_provider()
        monkeypatch.setenv("LLM_BACKEND", "none")
        a = get_llm_provider()
        b = get_llm_provider()
        assert a is b
        reset_default_provider()


# ─── 1.1 — 'none' backend returns None and counts skipped_reason ─────────────


class TestNoneBackend:
    def test_complete_json_returns_none(self):
        p = LLMProvider(backend=BACKEND_NONE)
        out = p.complete_json(system="s", user="u", schema=Tiny)
        assert out is None
        assert p.usage.skipped.get(SKIP_NO_PROVIDER) == 1

    def test_batch_complete_returns_list_of_none(self):
        p = LLMProvider(backend=BACKEND_NONE)
        from app.utils.llm import LLMRequest
        out = p.batch_complete_json([
            LLMRequest(system="s1", user="u1", schema=Tiny),
            LLMRequest(system="s2", user="u2", schema=Tiny),
        ])
        assert out == [None, None]
        assert p.usage.skipped.get(SKIP_NO_PROVIDER) == 2


# ─── 1.3 — cache (LRU + disk) ────────────────────────────────────────────────


class TestCache:
    def test_disk_round_trip(self, tmp_path: Path):
        p = LLMProvider(backend=BACKEND_GEMINI, cache_dir=tmp_path)
        # Force backend resolution to bypass API key checks
        p._backend = BACKEND_GEMINI  # type: ignore

        key = _cache_key_for("gemini-2.5-flash", "sys", "usr", "Tiny")
        p._cache_put(key, {"answer": "cached"})

        # New provider with same dir reads it from disk
        p2 = LLMProvider(backend=BACKEND_NONE, cache_dir=tmp_path)
        got = p2._cache_get(key)
        assert got == {"answer": "cached"}

    def test_lru_eviction(self, tmp_path: Path):
        p = LLMProvider(backend=BACKEND_NONE, cache_dir=tmp_path, lru_size=2)
        p._cache_put("k1", {"v": 1})
        p._cache_put("k2", {"v": 2})
        p._cache_put("k3", {"v": 3})   # evicts k1 from LRU
        assert "k1" not in p._lru
        assert "k2" in p._lru
        assert "k3" in p._lru

    def test_cache_hit_increments_counter(self, tmp_path: Path):
        # Use a provider with backend=gemini but stubbed dispatch
        p = LLMProvider(backend=BACKEND_GEMINI, cache_dir=tmp_path)
        p._backend = BACKEND_GEMINI  # type: ignore
        key = _cache_key_for(p.model, "sys", "usr", "Tiny")
        p._cache_put(key, {"answer": "from-cache"})

        with patch.object(LLMProvider, "_dispatch", return_value=None) as dispatch_mock:
            out = p.complete_json(system="sys", user="usr", schema=Tiny)
        assert out is not None
        assert out.answer == "from-cache"
        assert p.usage.cache_hits == 1
        dispatch_mock.assert_not_called()

    def test_cache_key_stable(self):
        k1 = _cache_key_for("m", "s", "u", "S")
        k2 = _cache_key_for("m", "s", "u", "S")
        assert k1 == k2
        # Different schema → different key
        assert _cache_key_for("m", "s", "u", "X") != k1


# ─── 1.4 — cost cap, telemetry, schema-failure retry ─────────────────────────


class TestCostCapAndRetry:
    def test_cost_cap_skips(self, tmp_path: Path):
        p = LLMProvider(backend=BACKEND_GEMINI, cache_dir=tmp_path, cost_cap_usd=0.001)
        p._backend = BACKEND_GEMINI  # type: ignore
        # Bump usage above the cap
        p.usage.add(tokens_in=10000, tokens_out=10000, cost_usd=1.0)

        with patch.object(LLMProvider, "_dispatch") as dispatch_mock:
            out = p.complete_json(system="s", user="u", schema=Tiny)
        assert out is None
        assert p.usage.skipped.get(SKIP_COST_CAP) == 1
        dispatch_mock.assert_not_called()

    def test_schema_failure_then_reformat_succeeds(self, tmp_path: Path):
        # Tiny has a default for 'answer'; use a strict schema where
        # missing fields actually fail validation.
        class Strict(BaseModel):
            model_config = {"extra": "forbid"}
            answer: str

        p = LLMProvider(backend=BACKEND_GEMINI, cache_dir=tmp_path)
        p._backend = BACKEND_GEMINI  # type: ignore
        responses = [
            {"wrong_key": "bad"},      # first attempt fails validation
            {"answer": "good"},        # reformat retry succeeds
        ]
        with patch.object(LLMProvider, "_dispatch", side_effect=responses):
            out = p.complete_json(system="s", user="u", schema=Strict)
        assert out is not None
        assert out.answer == "good"

    def test_schema_failure_after_retry_returns_none(self, tmp_path: Path):
        p = LLMProvider(backend=BACKEND_GEMINI, cache_dir=tmp_path)
        p._backend = BACKEND_GEMINI  # type: ignore
        with patch.object(LLMProvider, "_dispatch", side_effect=[{"bad": "x"}, {"bad": "x"}]):
            # Tiny has a default for 'answer' so {"bad": "x"} actually validates
            # (extra fields ignored by default). Use a stricter schema instead.
            class Strict(BaseModel):
                model_config = {"extra": "forbid"}
                answer: str

            p2 = LLMProvider(backend=BACKEND_GEMINI, cache_dir=tmp_path)
            p2._backend = BACKEND_GEMINI  # type: ignore
            with patch.object(LLMProvider, "_dispatch", side_effect=[{"bad": "x"}, {"bad": "x"}]):
                out = p2.complete_json(system="s", user="u", schema=Strict)
            assert out is None
            assert p2.usage.skipped.get(SKIP_SCHEMA_FAILURE) == 1


# ─── Cost helper ─────────────────────────────────────────────────────────────


class TestCostHelper:
    def test_unknown_model_zero_cost(self):
        assert _cost_for("unknown-model", 1000, 1000) == 0.0

    def test_groq_pricing(self):
        # Sanity: should be non-zero and proportional to tokens.
        a = _cost_for("qwen-2.5-32b", 1000, 1000)
        b = _cost_for("qwen-2.5-32b", 2000, 2000)
        assert a > 0
        assert b == pytest.approx(a * 2, rel=1e-9)


# ─── Gemini adapter wiring (mocked httpx) ───────────────────────────────────


class TestGeminiAdapterMocked:
    """Exercises the Gemini HTTP path without hitting a real server."""

    def test_successful_call(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        p = LLMProvider(backend=BACKEND_GEMINI, cache_dir=tmp_path)
        p._backend = BACKEND_GEMINI  # type: ignore

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps({"answer": "from-gemini"})}
                        ]
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 20,
                "candidatesTokenCount": 10,
            }
        }
        with patch("httpx.Client") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.post.return_value = fake_resp
            out = p.complete_json(system="s", user="u", schema=Tiny)

        assert out is not None
        assert out.answer == "from-gemini"
        assert p.usage.tokens_in == 20
        assert p.usage.tokens_out == 10
        assert p.usage.cost_usd == 0.0

    def test_4xx_no_retry(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        p = LLMProvider(backend=BACKEND_GEMINI, cache_dir=tmp_path)
        p._backend = BACKEND_GEMINI  # type: ignore
        fake_resp = MagicMock()
        fake_resp.status_code = 401
        fake_resp.text = "unauthorized"
        with patch("httpx.Client") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.post.return_value = fake_resp
            out = p.complete_json(system="s", user="u", schema=Tiny)
        assert out is None
        assert p.usage.skipped.get(SKIP_TRANSPORT_ERROR) == 1

    def test_timeout_records_skip(self, tmp_path: Path, monkeypatch):
        import httpx
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        p = LLMProvider(
            backend=BACKEND_GEMINI, cache_dir=tmp_path, max_retries=0, timeout_s=0.01,
        )
        p._backend = BACKEND_GEMINI  # type: ignore
        with patch("httpx.Client") as MockClient:
            ctx = MockClient.return_value.__enter__.return_value
            ctx.post.side_effect = httpx.TimeoutException("slow")
            out = p.complete_json(system="s", user="u", schema=Tiny)
        assert out is None
        assert p.usage.skipped.get(SKIP_TIMEOUT) == 1
