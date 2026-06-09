"""Phase 1 (P1.5) — per-section fallback + tightened full-text mining."""

from __future__ import annotations

from app.utils.skill_normalization import extract_skills_from_full_text


class TestExtractSkillsFromFullText:
    def test_strips_label_prefix_when_short(self) -> None:
        text = "Tech Stack: TensorFlow, PyTorch"
        out = extract_skills_from_full_text(text)
        assert "tensorflow" in out
        assert "pytorch" in out
        # No "tech stack tensorflow" multi-word contamination
        assert not any("stack" in s and "tensorflow" in s for s in out)

    def test_filters_non_technical_phrases(self) -> None:
        text = "Jane Roe\nB.Tech CSE"
        out = extract_skills_from_full_text(text)
        # Names and education degrees should not appear as skills
        assert "jane roe" not in out
        assert "b.tech cse" not in out

    def test_keeps_whitelisted_short_skills(self) -> None:
        text = "SQL, AWS, GCP"
        out = extract_skills_from_full_text(text)
        assert "sql" in out
        # AWS / GCP normalize through SKILL_ALIAS_MAP. The current alias map
        # has a circular 'aws' <-> 'amazon web services' mapping, so the final
        # canonical form after two normalize_skill passes is 'aws'.
        assert "aws" in out
        assert "google cloud platform" in out

    def test_returns_empty_for_empty_input(self) -> None:
        assert extract_skills_from_full_text("") == []
        assert extract_skills_from_full_text("   \n  ") == []

    def test_mines_known_skills_from_prose(self) -> None:
        text = "Worked extensively with tensorflow and pytorch on neural networks."
        out = extract_skills_from_full_text(text)
        assert "tensorflow" in out
        assert "pytorch" in out

    def test_caps_result_length(self) -> None:
        # Cap defaults to 25; verify clipping works on big inputs.
        text = ", ".join(["python"] * 100)
        out = extract_skills_from_full_text(text, cap=5)
        assert len(out) <= 5
