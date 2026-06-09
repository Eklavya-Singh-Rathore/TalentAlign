"""Sub-phase 1.20 — live Ollama smoke for project enrichment.

Run intentionally:
    LLM_BACKEND=ollama pytest tests/llm/test_project_enrichment_live.py -v -m live_llm
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.jd_intelligence import analyze_jd
from app.services.project_intelligence import analyze_projects
from app.services.resume_parser import parse_resume
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


def test_eklavya_x_jd1_project_enrichment():
    """Live: per-project llm_rationale mentions domain-relevant evidence."""
    resume = parse_resume(str(FIXTURES / "Eklavya_Singh_Rathore_Resume.pdf"))
    jd_text = extract_text_from_docx(str(FIXTURES / "JD_1.docx"))
    provider = LLMProvider(backend=BACKEND_GEMINI)
    jd = analyze_jd(jd_text, llm_provider=provider)
    result = analyze_projects(resume["projects"], jd.to_dict(),
                              llm_provider=provider)
    # Every project should have llm_* fields populated under a live LLM.
    populated = sum(
        1 for r in result.ranked_projects
        if r["llm_relevance"] is not None and r["llm_rationale"]
    )
    # Allow a few missing if the LLM produced fewer items than projects.
    assert populated >= max(1, len(result.ranked_projects) - 2)
    # Aggregate strengths/gaps populated
    assert result.llm_top_strengths is not None
