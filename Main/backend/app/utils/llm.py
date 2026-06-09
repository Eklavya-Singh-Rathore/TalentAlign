"""LLM provider abstraction with graceful degradation.

Mirrors the ``EmbeddingProvider`` pattern in ``embeddings.py``: a single
``LLMProvider`` class exposes ``complete_json`` / ``batch_complete_json``,
auto-selecting a backend at runtime:

  1. gemini  — Google Gemini 2.5 Flash via the Generative Language REST API.
               Primary production backend.
  2. groq    — scaffolded but inactive; activates when LLM_BACKEND=groq and
               GROQ_API_KEY are set.
  3. mock    — returns canned fixtures from ``tests/fixtures/llm/``. CI default.
  4. none    — every call returns ``None``; pipeline degrades gracefully.

Responsibilities:

* Class + dataclasses + cascade resolver + singleton.
* SHA-256 cache keys, in-process LRU(1024), on-disk JSON under
  ``$TALENTALIGN_LLM_CACHE_DIR``.
* Cost cap, timeout, retry with backoff, reformat-on-schema-failure retry,
  ``skipped_reason`` telemetry on ``LLMUsage``.
* Gemini adapter via ``httpx`` against
  ``generativelanguage.googleapis.com/v1beta/models/{model}:generateContent``
  with ``responseMimeType='application/json'``.
* ``MockLLMProvider`` lives in ``tests/utils/mock_llm.py`` to keep production
  code clean of test concerns.

Threading: the in-process LRU uses ``functools.lru_cache``-style ordering
via an ``OrderedDict`` guarded by a lock. Disk cache writes are atomic
(temp file + rename). Provider instances are intended to be process-wide
singletons (``get_llm_provider()``).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Type, Union

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


# ── Backend identifiers ─────────────────────────────────────────────────────

BACKEND_AUTO = "auto"
BACKEND_GROQ = "groq"   # scaffolded; Phase 6 only
BACKEND_GEMINI = "gemini"
BACKEND_MOCK = "mock"
BACKEND_NONE = "none"

_VALID_BACKENDS = {BACKEND_AUTO, BACKEND_GROQ, BACKEND_GEMINI, BACKEND_MOCK, BACKEND_NONE}


# ── Reasons a call may be skipped (telemetry on LLMUsage) ───────────────────

SKIP_NO_PROVIDER = "no_provider"
SKIP_COST_CAP = "cost_cap"
SKIP_TIMEOUT = "timeout"
SKIP_SCHEMA_FAILURE = "schema_failure"
SKIP_TRANSPORT_ERROR = "transport_error"


# ── Default settings ────────────────────────────────────────────────────────

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_S = 15.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_COST_CAP_USD = 0.10
DEFAULT_LRU_SIZE = 1024


# ── Per-model approximate $/token rates ($USD per 1K tokens) ────────────────
#
# Groq rates are placeholders kept here so the Phase 6 cutover doesn't need to
# touch this file beyond confirming numbers.

PRICING_TABLE: Dict[str, Dict[str, float]] = {
    # Gemini (free tier default)
    "gemini-1.5-flash": {"input": 0.0, "output": 0.0},
    "gemini-2.5-flash": {"input": 0.0, "output": 0.0},
    "gemini-2.0-flash": {"input": 0.0, "output": 0.0},
    # Groq placeholder — confirmed at sub-phase 6.3 calibration.
    "qwen-2.5-32b": {"input": 0.00029, "output": 0.00079},
    "llama-3.1-70b-versatile": {"input": 0.00059, "output": 0.00079},
}


# ── Dataclasses ─────────────────────────────────────────────────────────────


@dataclass
class LLMRequest:
    """One LLM call: system + user prompt + the schema the response must match."""
    system: str
    user: str
    schema: Type[BaseModel]
    cache_key: Optional[str] = None   # caller-provided opaque key; auto-derived if None
    model: Optional[str] = None       # overrides provider default for this request only


@dataclass
class LLMUsage:
    """Mutable counter of LLM activity for one process. Surfaced for telemetry."""
    calls: int = 0
    cache_hits: int = 0
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    skipped: Dict[str, int] = field(default_factory=dict)

    def record_skip(self, reason: str) -> None:
        self.skipped[reason] = self.skipped.get(reason, 0) + 1

    def add(self, *, tokens_in: int, tokens_out: int, cost_usd: float) -> None:
        self.calls += 1
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.cost_usd += cost_usd

    def hit(self) -> None:
        self.cache_hits += 1


# ── Cache helpers (sub-phase 1.3) ───────────────────────────────────────────


def _cache_key_for(model: str, system: str, user: str, schema_name: str) -> str:
    """Stable SHA-256 over the canonical request tuple."""
    h = hashlib.sha256()
    for piece in (model, system, user, schema_name):
        h.update(piece.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def _default_cache_dir() -> Path:
    """Resolve the on-disk cache root from env, falling back to a project-local default."""
    env = os.environ.get("TALENTALIGN_LLM_CACHE_DIR")
    if env:
        return Path(env)
    # Project-local default — keeps everything under D: per user preference.
    here = Path(__file__).resolve()
    backend_root = here.parents[2]  # app/utils/llm.py → backend/
    return backend_root / ".cache" / "talentalign-llm"


# ── Main provider class ─────────────────────────────────────────────────────


class LLMProvider:
    """Single interface for structured-JSON LLM calls with backend cascade.

    Backend cascade (auto):
        gemini (if GEMINI_API_KEY or GOOGLE_API_KEY is set)
          → none (final fallback; every call returns None).

    Explicit overrides via ``LLM_BACKEND`` env: ``gemini`` / ``groq`` /
    ``mock`` / ``none``. Groq is wired but only activates when
    ``LLM_BACKEND='groq'`` and ``GROQ_API_KEY`` are set.
    """

    def __init__(
        self,
        backend: str = BACKEND_AUTO,
        model: Optional[str] = None,
        cache_dir: Optional[Union[str, Path]] = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        max_retries: int = DEFAULT_MAX_RETRIES,
        cost_cap_usd: float = DEFAULT_COST_CAP_USD,
        lru_size: int = DEFAULT_LRU_SIZE,
    ) -> None:
        if backend not in _VALID_BACKENDS:
            raise ValueError(f"Unknown backend {backend!r}; must be one of {_VALID_BACKENDS}")
        self._requested_backend = backend
        self._model_override = model or os.environ.get("TALENTALIGN_LLM_MODEL")
        self._cache_dir = Path(cache_dir) if cache_dir else _default_cache_dir()
        # Env overrides let callers tune latency/budget without code changes. Explicit
        # constructor args still win when not left at their defaults.
        if timeout_s == DEFAULT_TIMEOUT_S:
            timeout_s = float(os.environ.get("TALENTALIGN_LLM_TIMEOUT", timeout_s))
        if cost_cap_usd == DEFAULT_COST_CAP_USD:
            cost_cap_usd = float(os.environ.get("TALENTALIGN_LLM_COST_CAP", cost_cap_usd))
        self._timeout_s = timeout_s
        self._max_retries = max_retries
        self._cost_cap_usd = cost_cap_usd
        self._lru_size = lru_size

        self._backend: Optional[str] = None
        self._usage = LLMUsage()
        self._lru: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._lock = threading.Lock()

    # ── Resolution ──────────────────────────────────────────────────────────

    @property
    def backend(self) -> str:
        if self._backend is None:
            self._resolve_backend()
        return self._backend  # type: ignore[return-value]

    @property
    def model(self) -> str:
        if self._model_override:
            return self._model_override
        if self.backend == BACKEND_GEMINI:
            return DEFAULT_GEMINI_MODEL
        # Mock + none don't care, but return something sensible for cache keys.
        return self._model_override or DEFAULT_GEMINI_MODEL

    @property
    def usage(self) -> LLMUsage:
        return self._usage

    def _resolve_backend(self) -> None:
        # Env override always wins.
        env_choice = os.environ.get("LLM_BACKEND")
        choice = self._requested_backend
        if choice == BACKEND_AUTO and env_choice:
            choice = env_choice.lower()

        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

        if choice == BACKEND_NONE:
            self._backend = BACKEND_NONE
            logger.info("LLM backend resolved: none (calls will return None)")
            return
        if choice == BACKEND_MOCK:
            self._backend = BACKEND_MOCK
            logger.info("LLM backend resolved: mock")
            return
        if choice == BACKEND_GROQ:
            # Phase 6 path. Verify key presence; do NOT make a network call here.
            if not os.environ.get("GROQ_API_KEY"):
                logger.warning("Groq backend requested but GROQ_API_KEY missing — degrading to 'none'")
                self._backend = BACKEND_NONE
                return
            self._backend = BACKEND_GROQ
            logger.info("LLM backend resolved: groq")
            return
        if choice == BACKEND_GEMINI:
            if not gemini_key:
                logger.warning("Gemini backend requested but GEMINI_API_KEY/GOOGLE_API_KEY missing — degrading to 'none'")
                self._backend = BACKEND_NONE
                return
            self._backend = BACKEND_GEMINI
            logger.info("LLM backend resolved: gemini")
            return

        # auto cascade: gemini (if key set) -> none
        if gemini_key:
            self._backend = BACKEND_GEMINI
            logger.info("LLM backend resolved (auto): gemini")
            return
        self._backend = BACKEND_NONE
        logger.info("LLM backend resolved (auto): none (Gemini key missing)")

    # ── Public API ──────────────────────────────────────────────────────────

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: Type[BaseModel],
        cache_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[BaseModel]:
        """One LLM call returning a schema-validated pydantic model, or None.

        Failure modes (all return None and increment a ``skipped`` counter):
          - backend == 'none' → SKIP_NO_PROVIDER
          - cost cap exceeded → SKIP_COST_CAP
          - timeout / transport error after retries → SKIP_TIMEOUT / SKIP_TRANSPORT_ERROR
          - schema validation fails after reformat retry → SKIP_SCHEMA_FAILURE
        """
        req = LLMRequest(system=system, user=user, schema=schema, cache_key=cache_key, model=model)
        out = self.batch_complete_json([req])
        return out[0]

    def batch_complete_json(
        self,
        requests: Sequence[LLMRequest],
    ) -> List[Optional[BaseModel]]:
        """Issue many requests in one call (sequential under Ollama; provider-batched on Groq).

        Order in equals order out — callers can zip with their input list.
        """
        backend = self.backend
        if backend == BACKEND_NONE:
            for _ in requests:
                self._usage.record_skip(SKIP_NO_PROVIDER)
            return [None] * len(requests)

        results: List[Optional[BaseModel]] = []
        for req in requests:
            results.append(self._complete_one(req, backend))
        return results

    # ── Internals ───────────────────────────────────────────────────────────

    def _complete_one(self, req: LLMRequest, backend: str) -> Optional[BaseModel]:
        model = req.model or self.model
        schema_name = req.schema.__name__
        key = req.cache_key or _cache_key_for(model, req.system, req.user, schema_name)

        # 1. Cache lookup.
        cached = self._cache_get(key)
        if cached is not None:
            self._usage.hit()
            return self._validate_or_none(cached, req.schema, schema_name)

        # 2. Cost cap.
        if self._usage.cost_usd >= self._cost_cap_usd:
            self._usage.record_skip(SKIP_COST_CAP)
            return None

        # 3. Dispatch by backend.
        try:
            raw = self._dispatch(backend, model, req.system, req.user, req.schema)
        except _TransportTimeout as exc:
            logger.warning("LLM transport timeout: %s", exc)
            self._usage.record_skip(SKIP_TIMEOUT)
            return None
        except _TransportError as exc:
            logger.warning("LLM transport error: %s", exc)
            self._usage.record_skip(SKIP_TRANSPORT_ERROR)
            return None

        if raw is None:
            return None

        # 4. Validate. Reformat-retry once on failure.
        validated = self._validate_or_none(raw, req.schema, schema_name)
        if validated is None:
            try:
                raw = self._dispatch(
                    backend, model,
                    req.system + "\n\nYour previous response was not valid JSON for the schema. Return ONLY a valid JSON object.",
                    req.user, req.schema,
                )
            except (_TransportTimeout, _TransportError):
                raw = None
            if raw is None:
                self._usage.record_skip(SKIP_SCHEMA_FAILURE)
                return None
            validated = self._validate_or_none(raw, req.schema, schema_name)
            if validated is None:
                self._usage.record_skip(SKIP_SCHEMA_FAILURE)
                return None

        # 5. Cache the validated raw (so future cache hits don't re-validate).
        self._cache_put(key, raw if isinstance(raw, dict) else validated.model_dump())
        return validated

    def _dispatch(
        self,
        backend: str,
        model: str,
        system: str,
        user: str,
        schema: Type[BaseModel],
    ) -> Optional[Dict[str, Any]]:
        if backend == BACKEND_GEMINI:
            return self._call_gemini(model, system, user, schema)
        if backend == BACKEND_GROQ:
            return self._call_groq(model, system, user, schema)
        return None

    def _call_gemini(
        self, model: str, system: str, user: str, schema: Type[BaseModel],
    ) -> Optional[Dict[str, Any]]:
        """Google Gemini API call with structured JSON output and retry/backoff."""
        import httpx
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise _TransportError("Missing Gemini API Key.")

        schema_blob = json.dumps(schema.model_json_schema(), indent=2)
        full_system = (
            f"{system}\n\n"
            f"Respond with a single JSON object matching this schema EXACTLY:\n```json\n{schema_blob}\n```\n"
            "Return ONLY the JSON object — no prose, no markdown fences."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": user}]}
            ],
            "systemInstruction": {
                "parts": [{"text": full_system}]
            },
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        last_exc: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                with httpx.Client(timeout=self._timeout_s) as c:
                    r = c.post(url, json=payload, headers={"Content-Type": "application/json"})
                if r.status_code >= 500:
                    raise _TransportError(f"Gemini 5xx: {r.status_code}")
                if r.status_code >= 400:
                    raise _TransportError(f"Gemini 4xx: {r.status_code} {r.text[:200]}")
                
                body = r.json()
                candidates = body.get("candidates", [])
                if not candidates:
                    return None
                
                content_block = candidates[0].get("content", {})
                parts = content_block.get("parts", [])
                content = parts[0].get("text", "") if parts else ""
                
                usage = body.get("usageMetadata", {})
                tokens_in = int(usage.get("promptTokenCount", 0) or 0)
                tokens_out = int(usage.get("candidatesTokenCount", 0) or 0)
                
                cost = _cost_for(model, tokens_in, tokens_out)
                self._usage.add(tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost)
                
                try:
                    return json.loads(content) if content else None
                except json.JSONDecodeError:
                    return None
            except httpx.TimeoutException as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(1.0 * (3 ** attempt))
                    continue
                raise _TransportTimeout(str(exc)) from exc
            except _TransportError:
                if attempt < self._max_retries:
                    time.sleep(1.0 * (3 ** attempt))
                    continue
                raise
            except Exception as exc:
                last_exc = exc
                raise _TransportError(str(exc)) from exc

        if last_exc:
            raise _TransportError(str(last_exc))
        return None

    def _call_groq(
        self, model: str, system: str, user: str, schema: Type[BaseModel],
    ) -> Optional[Dict[str, Any]]:
        """Phase 6 only: Groq via OpenAI-compatible API. Lazy SDK import.

        Activates when LLM_BACKEND=groq + GROQ_API_KEY are set. Wired here
        so the Phase 6 cutover is a config change, not a code change.
        """
        try:
            from groq import Groq  # type: ignore
        except ImportError:
            self._usage.record_skip(SKIP_TRANSPORT_ERROR)
            return None

        schema_blob = json.dumps(schema.model_json_schema(), indent=2)
        full_system = (
            f"{system}\n\n"
            f"Respond with a single JSON object matching this schema EXACTLY:\n```json\n{schema_blob}\n```\n"
            "Return ONLY the JSON object — no prose."
        )
        client = Groq(api_key=os.environ["GROQ_API_KEY"], timeout=self._timeout_s)
        for attempt in range(self._max_retries + 1):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": full_system},
                        {"role": "user", "content": user},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                content = resp.choices[0].message.content or ""
                usage = getattr(resp, "usage", None)
                tin = int(getattr(usage, "prompt_tokens", 0) or 0)
                tout = int(getattr(usage, "completion_tokens", 0) or 0)
                self._usage.add(tokens_in=tin, tokens_out=tout, cost_usd=_cost_for(model, tin, tout))
                try:
                    return json.loads(content) if content else None
                except json.JSONDecodeError:
                    return None
            except Exception as exc:  # pragma: no cover — Phase 6 path
                if attempt < self._max_retries:
                    time.sleep(1.0 * (3 ** attempt))
                    continue
                logger.warning("Groq call failed: %s", exc)
                raise _TransportError(str(exc)) from exc
        return None

    # ── Cache plumbing ──────────────────────────────────────────────────────

    def _cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if key in self._lru:
                self._lru.move_to_end(key)
                return self._lru[key]
        # Disk fallback.
        path = self._cache_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                self._lru[key] = data
                self._evict_if_needed()
            return data
        except Exception:
            return None

    def _cache_put(self, key: str, data: Dict[str, Any]) -> None:
        with self._lock:
            self._lru[key] = data
            self._lru.move_to_end(key)
            self._evict_if_needed()
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            tmp = self._cache_dir / f"{key}.json.tmp"
            final = self._cache_dir / f"{key}.json"
            with tmp.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, final)
        except Exception as exc:
            logger.warning("LLM cache write failed for key %s: %s", key[:8], exc)

    def _evict_if_needed(self) -> None:
        # Caller must hold self._lock.
        while len(self._lru) > self._lru_size:
            self._lru.popitem(last=False)

    @staticmethod
    def _validate_or_none(
        raw: Dict[str, Any], schema: Type[BaseModel], schema_name: str
    ) -> Optional[BaseModel]:
        try:
            return schema.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Schema validation failed for %s: %s", schema_name, exc)
            return None


# ── Helpers ─────────────────────────────────────────────────────────────────


def _cost_for(model: str, tokens_in: int, tokens_out: int) -> float:
    """Estimate $ cost from token counts; 0.0 if model unknown (Ollama-local)."""
    rates = PRICING_TABLE.get(model)
    if not rates:
        return 0.0
    return (tokens_in / 1000.0) * rates["input"] + (tokens_out / 1000.0) * rates["output"]


class _TransportTimeout(Exception):
    pass


class _TransportError(Exception):
    pass


# ── Module singleton (matches embeddings.get_embedding_provider) ────────────


_default_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Return the process-wide default LLMProvider (auto backend)."""
    global _default_provider
    if _default_provider is None:
        _default_provider = LLMProvider(backend=BACKEND_AUTO)
    return _default_provider


def reset_default_provider() -> None:
    """Clear the cached default provider (useful for tests)."""
    global _default_provider
    _default_provider = None
