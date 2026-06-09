"""Hallucination guard for the matcher's baseline output.

INVARIANT:
The matcher's matched/missing/unmatched output is byte-identical to the
no-LLM baseline regardless of what an LLM returns in *informational*
``llm_*`` fields elsewhere in the pipeline (e.g. ``llm_skills_inferred``
on projects, ``llm_responsibilities`` on the JD).

This file asserts that baseline for the matcher without an LLM provider.
``match_skills`` does accept an optional ``llm_provider`` argument for the
borderline validation gate; tests that exercise that path live in
``test_validation_gate.py``. The invariant here is that, regardless of any
LLM enrichment populated elsewhere, the deterministic matcher contract
({matched, unmatched_in_resume, missing_from_resume}) cannot drift.
"""

from __future__ import annotations

from app.services.skill_matcher import match_skills
from app.utils.embeddings import BACKEND_TFIDF, EmbeddingProvider


def _provider():
    return EmbeddingProvider(backend=BACKEND_TFIDF)


def _baseline_match():
    resume = ["python", "sql", "react", "docker", "scikit-learn"]
    jd_entries = [
        {"phrase": "python", "bucket": "required"},
        {"phrase": "reactjs", "bucket": "required"},     # alias
        {"phrase": "kubernetes", "bucket": "optional"},  # missing
        {"phrase": "machine learning library", "bucket": "required"},  # synonym
    ]
    return match_skills(resume, jd_entries, provider=_provider())


class TestHallucinationGuardBaseline:
    def test_matcher_output_deterministic(self):
        """Two runs of the matcher on identical input produce identical output."""
        a = _baseline_match()
        b = _baseline_match()
        assert a == b

    def test_matched_count_is_baseline(self):
        """Snapshot the matcher's output so any future enrichment cannot mutate it.

        Note: match_skills normalizes JD phrases at entry, so 'reactjs' → 'react'
        (via SKILL_ALIAS_MAP) and matches as 'exact' on both sides.
        """
        result = _baseline_match()
        matched_phrases = sorted(
            (m["resume_phrase"], m["jd_phrase"], m["match_type"]) for m in result["matched"]
        )
        # Frozen snapshot — change requires explicit justification.
        assert matched_phrases == [
            ("python", "python", "exact"),
            ("react", "react", "exact"),
            ("scikit-learn", "machine learning library", "synonym"),
        ]
        assert result["missing_from_resume"] == ["kubernetes"]
        assert sorted(result["unmatched_in_resume"]) == ["docker", "sql"]

    def test_match_result_keys_without_llm_provider(self):
        """Without an llm_provider, match_skills returns only the deterministic keys.

        The validation gate adds ``llm_validation`` to the result only when an
        ``llm_provider`` is passed; that path is covered in ``test_validation_gate.py``.
        """
        result = _baseline_match()
        assert set(result.keys()) == {"matched", "unmatched_in_resume", "missing_from_resume"}
