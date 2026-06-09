"""Sub-phase 1.23 — live Ollama smoke for experience enrichment."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.experience_intelligence import (
    CANDIDATE_CATEGORIES, analyze_experience,
)
from app.services.jd_intelligence import analyze_jd
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


def test_experience_enrichment_against_gemini():
    resume = parse_resume(str(FIXTURES / "Eklavya_Singh_Rathore_Resume.pdf"))
    jd_text = extract_text_from_docx(str(FIXTURES / "JD_1.docx"))
    provider = LLMProvider(backend=BACKEND_GEMINI)
    jd = analyze_jd(jd_text, llm_provider=provider)
    result = analyze_experience(resume, jd.to_dict(), llm_provider=provider)

    assert result.llm_candidate_type in CANDIDATE_CATEGORIES
    assert result.llm_relevant_experience_months is not None
    assert result.llm_relevant_experience_months >= 0
    assert result.llm_rationale and len(result.llm_rationale) > 20
