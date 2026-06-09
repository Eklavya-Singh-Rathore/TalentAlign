"""Phase 1 (P1.2) — text cleaning / formatting robustness."""

from __future__ import annotations

from app.utils.text_cleaning import normalize_document_text


class TestNormalizeDocumentText:
    def test_returns_empty_for_empty_input(self) -> None:
        assert normalize_document_text("") == ""
        assert normalize_document_text(None) == ""  # type: ignore[arg-type]

    def test_converts_unicode_bullets_to_dashes(self) -> None:
        text = "Skills\n• Python\n● SQL\n▪ React\n◦ Vue\n· TypeScript"
        out = normalize_document_text(text)
        for line in out.splitlines()[1:]:
            assert line.startswith("- "), line

    def test_converts_dash_variants_to_ascii_hyphen(self) -> None:
        text = "A – B\nA — C\nA ‐ D\nA ‑ E\nA − F"
        out = normalize_document_text(text)
        for line in out.splitlines():
            assert "–" not in line and "—" not in line and "‐" not in line

    def test_strips_zero_width_and_nbsp(self) -> None:
        text = "Hello World​!‌‍﻿"
        out = normalize_document_text(text)
        assert " " not in out
        assert "​" not in out
        assert "‌" not in out
        assert "‍" not in out
        assert "﻿" not in out
        assert out == "Hello World!"

    def test_strips_soft_hyphen(self) -> None:
        text = "imple­mentation"
        assert normalize_document_text(text) == "implementation"

    def test_smart_quotes_become_ascii(self) -> None:
        text = "“hello” ‘world’"
        out = normalize_document_text(text)
        assert "“" not in out and "”" not in out
        assert "‘" not in out and "’" not in out

    def test_end_of_line_hyphenation_is_joined_with_hyphen(self) -> None:
        # We rejoin "x-\ny" -> "x-y" (keep the hyphen) rather than "xy".
        # This preserves genuine compound words like "six-component" at the
        # cost of leaving PDF soft-wrap continuations like "imple-mentation"
        # mildly off — the safer trade-off without a dictionary.
        text = "imple-\nmentation of six-\ncomponent pipelines"
        out = normalize_document_text(text)
        assert "imple-mentation" in out
        assert "six-component" in out
        assert "imple-\n" not in out

    def test_drops_page_number_lines(self) -> None:
        text = "Resume\n1\nContent\nPage 2 of 3\n1 / 4\n1 | 5\nMore content"
        out = normalize_document_text(text).splitlines()
        assert "Resume" in out
        assert "Content" in out
        assert "More content" in out
        assert "1" not in out
        assert "Page 2 of 3" not in out
        assert "1 / 4" not in out
        assert "1 | 5" not in out

    def test_collapses_blank_lines_to_two(self) -> None:
        text = "A\n\n\n\n\nB"
        out = normalize_document_text(text)
        assert out == "A\n\nB"

    def test_preserves_section_header_case(self) -> None:
        text = "SKILLS\nPython"
        out = normalize_document_text(text)
        assert "SKILLS" in out
