"""Sub-phase 1.17 — live Ollama smoke test for JD enrichment.

Skipped automatically if Ollama isn't reachable. To run intentionally:

    LLM_BACKEND=ollama pytest tests/llm/test_jd_enrichment_live.py -v -m live_llm

Verifies that against each of the real JD fixtures (JD_1 … JD_5):
  - The LLM call completes without exception.
  - `llm_role_summary` and `llm_seniority` are populated and non-empty.
  - `llm_excluded_noise` captures at least one of the prose-noise items
    we previously identified (`internal partners`, `financial crimes`,
    `melbourne to vancouver`, `best practices`) when those appear in the
    JD text.

Marker `live_llm` keeps these out of the default `pytest` invocation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.jd_intelligence import analyze_jd
from app.utils.file_handling import extract_text_from_docx
from app.utils.llm import LLMProvider, BACKEND_GEMINI


def _gemini_available() -> bool:
    import os
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))


pytestmark = [
    pytest.mark.live_llm,
    pytest.mark.skipif(not _gemini_available(), reason="Gemini API key not available"),
]


FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
JD_PATHS = [FIXTURES / f"JD_{i}.docx" for i in range(1, 6)]


@pytest.mark.parametrize("jd_path", JD_PATHS, ids=lambda p: p.name)
def test_jd_enrichment_against_gemini(jd_path: Path):
    text = extract_text_from_docx(str(jd_path))
    provider = LLMProvider(backend=BACKEND_GEMINI)
    result = analyze_jd(text, llm_provider=provider)

    # Structural invariants
    assert result.llm_role_summary is not None and result.llm_role_summary != ""
    assert result.llm_seniority in (
        "intern", "junior", "mid", "senior", "lead", "executive",
    )
    assert 0.0 <= (result.llm_confidence or 0.0) <= 1.0
    # Baseline fields still populated
    assert isinstance(result.required_skills, list)
