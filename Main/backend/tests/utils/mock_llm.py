"""Deterministic mock LLM provider for tests (sub-phase 1.6).

Two patterns of use:

1. **Dict-backed** — pass a ``{cache_key: response_dict}`` map. The provider
   returns the matching response for every request; unknown keys raise
   ``KeyError`` (loud failure > silent fallthrough).

2. **Schema-driven default** — pass ``allow_default_empty=True`` to return
   a minimal valid instance for any unknown request. Useful for the
   hallucination-guard test (sub-phase 1.7) where we want SOMETHING in
   the ``llm_*`` fields without prescribing exact values.

The mock implements the same ``complete_json`` / ``batch_complete_json``
surface as ``LLMProvider`` so existing engine code accepts it as a drop-in.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Type

from pydantic import BaseModel

from app.utils.llm import LLMRequest, LLMUsage, _cache_key_for


@dataclass
class MockLLMProvider:
    """Deterministic in-memory LLM stand-in.

    Args:
        responses: Map of cache_key → JSON dict to return. Cache keys are
            computed via ``llm._cache_key_for`` from (model, system, user,
            schema_name) so tests can pre-compute them.
        allow_default_empty: When True, unknown requests return a
            ``schema()``-constructed instance (uses Pydantic defaults).
            When False, unknown requests raise ``KeyError``.
        model: Model string used when deriving cache keys. Defaults to a
            stable test value.
    """
    responses: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    allow_default_empty: bool = False
    model_name: str = "mock-model"

    # Bookkeeping (mirrors LLMProvider.usage for symmetry).
    usage: LLMUsage = field(default_factory=LLMUsage)

    @property
    def backend(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return self.model_name

    def complete_json(
        self,
        *,
        system: str,
        user: str,
        schema: Type[BaseModel],
        cache_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[BaseModel]:
        return self.batch_complete_json([
            LLMRequest(system=system, user=user, schema=schema, cache_key=cache_key, model=model)
        ])[0]

    def batch_complete_json(
        self, requests: Sequence[LLMRequest],
    ) -> List[Optional[BaseModel]]:
        out: List[Optional[BaseModel]] = []
        for req in requests:
            model = req.model or self.model_name
            key = req.cache_key or _cache_key_for(model, req.system, req.user, req.schema.__name__)
            if key in self.responses:
                self.usage.add(tokens_in=0, tokens_out=0, cost_usd=0.0)
                out.append(req.schema.model_validate(self.responses[key]))
                continue
            if self.allow_default_empty:
                # Build a minimally-valid instance using schema defaults.
                # Requires every required field has a default in the schema.
                try:
                    out.append(req.schema())
                except Exception:
                    # If the schema has required fields with no defaults,
                    # fall through to the loud KeyError below.
                    pass
                else:
                    self.usage.add(tokens_in=0, tokens_out=0, cost_usd=0.0)
                    continue
            raise KeyError(
                f"MockLLMProvider has no canned response for cache_key={key[:12]}…  "
                f"schema={req.schema.__name__}; system={req.system[:60]!r}; user={req.user[:60]!r}"
            )
        return out
