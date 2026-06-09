"""Generic text cleaning helpers.

Ported from Code/app_logic.py (clean_text, normalize_jd_text) plus Phase 1
formatting-robustness additions:
  - normalize_document_text: standardize whitespace, bullets, dashes, smart
    quotes, zero-width chars; de-hyphenate line breaks; strip page numbers.
    Designed to run *before* section detection so downstream regexes can
    rely on a stable representation.
"""

from __future__ import annotations

import re


# Bullet glyphs commonly emitted by PDF/DOCX extraction. Mapped to "- " so
# section detection and bullet-aware code paths treat them uniformly.
_BULLET_CHARS = (
    "•"  # bullet
    "●"  # black circle
    "○"  # white circle
    "▪"  # black small square
    "■"  # black square
    "▫"  # white small square
    "◦"  # white bullet
    "·"  # middle dot
    "⁃"  # hyphen bullet
    "∙"  # bullet operator
    "⁌"  # black leftwards bullet
    "⁍"  # black rightwards bullet
    "‧"  # hyphenation point
)

_BULLET_RE = re.compile(rf"[{_BULLET_CHARS}]\s*")

# Page-number-only lines: "1", "Page 1 of 3", "1 / 3", "1 | 3".
# Anchored to whole-line so "section 1" content lines aren't dropped.
_PAGE_NUMBER_RE = re.compile(
    r"^\s*(?:"
    r"page\s+\d+(?:\s+of\s+\d+)?"
    r"|\d+\s*(?:of|/|\|)\s*\d+"
    r"|\d{1,3}"
    r")\s*$",
    re.IGNORECASE,
)


def normalize_document_text(text: str) -> str:
    """Normalize PDF/DOCX-extracted text for downstream sectioning.

    Standardizes:
      - whitespace (NBSP, zero-width, BOM, soft hyphens)
      - smart quotes -> ASCII
      - bullet glyphs -> "- "
      - en/em/horizontal-bar dashes -> "-"
      - line-ending hyphenation ("imple-\\nmentation" -> "implementation")
      - line endings (\\r\\n, \\r -> \\n)
      - page-number-only lines (removed)
      - runs of blank lines collapsed to at most 2
      - runs of spaces/tabs collapsed to 1

    Case is preserved (section detection is case-insensitive but
    case-preserving lines help downstream NER/POS if added later).
    """
    if not isinstance(text, str) or not text:
        return ""

    # Zero-width chars and unusual whitespace
    text = text.replace(" ", " ")    # NBSP
    text = text.replace("​", "")     # ZWSP
    text = text.replace("‌", "")     # ZWNJ
    text = text.replace("‍", "")     # ZWJ
    text = text.replace("﻿", "")     # BOM
    text = text.replace("­", "")     # soft hyphen

    # Smart quotes -> ASCII
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')

    # Bullet glyphs -> "- "
    text = _BULLET_RE.sub("- ", text)

    # Hyphen/dash variants -> ASCII "-"
    # U+2010 hyphen, U+2011 non-breaking hyphen, U+2012 figure dash,
    # U+2013 en dash, U+2014 em dash, U+2015 horizontal bar, U+2212 minus sign
    text = (
        text.replace("‐", "-").replace("‑", "-").replace("‒", "-")
            .replace("–", "-").replace("—", "-").replace("―", "-")
            .replace("−", "-")
    )

    # Standardize line endings before any line-level work
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # End-of-line hyphenation: rejoin "x-\ny" to "x-y" (keep the hyphen).
    # Stripping the hyphen would be correct for PDF soft-wrap continuations
    # like "imple-\nmentation" but wrong for genuine compound words like
    # "six-\ncomponent". Without a dictionary we can't distinguish, so we
    # preserve the hyphen — it's worse to silently mangle "six-component"
    # into "sixcomponent" than to leave "imple-mentation" mildly off.
    text = re.sub(r"(\w)-\n(\w)", r"\1-\2", text)

    # Drop page-number-only lines
    kept_lines = []
    for line in text.split("\n"):
        if _PAGE_NUMBER_RE.match(line):
            continue
        kept_lines.append(line)
    text = "\n".join(kept_lines)

    # Collapse runs of blanks within a line; preserve newlines
    text = re.sub(r"[ \t]+", " ", text)

    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip("\n")


def clean_text(text: str) -> str:
    """Lowercase, remove punctuation, normalize whitespace.

    Currently unused by parse_resume but exported for downstream callers
    (notebooks, future scoring modules).
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s\-]', ' ', text)
    text = re.sub(r'(?<![\w])\-|\-(?![\w])', ' ', text)
    text = re.sub(r'[\r\n\t]+', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def normalize_jd_text(text: str) -> str:
    """Clean and normalize JD text."""
    if not isinstance(text, str):
        return ""
    cleaned = text.strip().replace("\r\n", "\n").replace("\r", "\n")
    cleaned = cleaned.lower()
    cleaned = re.sub(r"[^a-z0-9\n\-\+#\./,;: ]+", " ", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n\s+", "\n", cleaned)
    cleaned = re.sub(r"\n{2,}", "\n\n", cleaned)
    return cleaned.strip()
