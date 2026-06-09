"""Text normalization, whitelisting, synonyms, adaptive threshold.

The small primitives that everything else in the package builds on.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .constants import (
    SEMANTIC_SYNONYMS,
    SHORT_SKILL_WHITELIST,
    SKILL_ALIAS_MAP,
    WHITELIST_PATTERNS,
    _SYNONYM_REVERSE,
)


def is_whitelisted(phrase: str) -> bool:
    """Return True if phrase matches a tech-skill whitelist pattern."""
    if not phrase:
        return False
    p = phrase.strip().lower()
    return p in SHORT_SKILL_WHITELIST or any(pat.match(p) for pat in WHITELIST_PATTERNS)


def normalize_skill(skill: str) -> str:
    """Resolve abbreviations/variants to canonical form."""
    if not skill:
        return ""
    key = skill.lower().strip()
    return SKILL_ALIAS_MAP.get(key, key)


# ---------------------------------------------------------------------------
# Text normalization (shared by NB3 + NB8)
# ---------------------------------------------------------------------------

def normalize_text_for_skills(text: Optional[str]) -> str:
    """Normalize skill-focused text while preserving skill-list boundaries."""
    if not isinstance(text, str) or not text.strip():
        return ""
    cleaned = text.strip().lower()
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[\n;|]+", ", ", cleaned)
    cleaned = re.sub(r"[^a-z0-9,\+#\./\- ]+", " ", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" ,")


normalize_text = normalize_text_for_skills


def normalize_phrase(phrase: Optional[str]) -> str:
    """Normalize a single skill phrase for comparison and output."""
    normalized = normalize_text_for_skills(phrase)
    normalized = normalized.replace(",", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


# ---------------------------------------------------------------------------
# L3 — Semantic synonym lookup
# ---------------------------------------------------------------------------

def get_synonyms(phrase: str) -> List[str]:
    """Return all known synonyms for *phrase* (canonical or reverse lookup)."""
    key = phrase.strip().lower()
    results = list(SEMANTIC_SYNONYMS.get(key, []))
    for canonical in _SYNONYM_REVERSE.get(key, []):
        if canonical not in results:
            results.append(canonical)
    return results


def is_synonym_match(phrase_a: str, phrase_b: str) -> bool:
    """Return True if *phrase_a* and *phrase_b* are synonyms of each other."""
    a = phrase_a.strip().lower()
    b = phrase_b.strip().lower()
    if a == b:
        return True
    if b in [s.lower() for s in get_synonyms(a)]:
        return True
    if a in [s.lower() for s in get_synonyms(b)]:
        return True
    return False


# ---------------------------------------------------------------------------
# L1 — Adaptive cosine-similarity threshold (Phase 2)
# ---------------------------------------------------------------------------

DEFAULT_MATCH_THRESHOLD = 0.75

_THRESHOLD_BY_WORDS: List[Tuple[int, float]] = [
    (1, 0.65),
    (2, 0.58),
    (3, 0.52),
]


def compute_adaptive_threshold(jd_phrase: str) -> float:
    """Return a cosine-similarity threshold adapted to *jd_phrase* length."""
    word_count = len(jd_phrase.strip().split())
    for max_words, threshold in _THRESHOLD_BY_WORDS:
        if word_count <= max_words:
            return threshold
    return _THRESHOLD_BY_WORDS[-1][1]
