"""Validation, cleaning, cluster matching, deduplication, POS filtering.

Builds on :mod:`.text` for normalization. Filters in this module are pure
(no I/O) except for the lazy spaCy load behind :func:`filter_non_skill_phrases_pos`.
"""

from __future__ import annotations

import logging
import re
from typing import Iterable, List, Optional

from .constants import (
    JD_ACTION_VERBS,
    JD_GENERIC_TAIL_TOKENS,
    JD_NOISE_PHRASES,
    JD_NOISE_SUBSTRINGS,
    JD_TOKEN_BLACKLIST,
    MATCH_SCORE_BY_TYPE,
    NON_SKILL_WORDS,
    SEMANTIC_SYNONYMS,
    SKILL_ALIAS_MAP,
    SKILL_CLUSTERS,
    SKILL_NOISE_SUBSTRINGS,
    SOFT_SKILL_BLACKLIST,
    TECH_SIGNAL_TOKENS,
    _JD_PREPOSITION_LEADS,
    _SYNONYM_REVERSE,
)
from .text import is_whitelisted, normalize_phrase, normalize_skill

logger = logging.getLogger(__name__)


# P3patch.D: URL / domain detection. Web TLDs that do NOT collide with tech
# extensions (.net→asp.net, .io→socket.io, .ai, .co, .dev, .app are excluded).
_URL_RE = re.compile(
    r"(?:https?://|www\.)|\b[a-z][a-z0-9\-]*\.(?:com|org|edu|gov|in)\b"
)

# P3patch.D: role-noun tails. A phrase ending in one of these is a JOB TITLE
# (e.g. "data analyst", "data science consultant", "ml engineer"), not a
# skill. Note the -ing forms ("engineering", "consulting") are NOT here, so
# genuine skills like "data engineering" survive.
JOB_TITLE_TAIL: set = {
    "analyst", "scientist", "consultant", "engineer", "developer", "manager",
    "architect", "administrator", "designer", "specialist", "coordinator",
    "intern", "officer", "director", "executive", "researcher", "trainee",
    "associate", "lead", "head",
}


def is_valid_skill(phrase: str) -> bool:
    """Return True if phrase passes the unified blacklist/whitelist filter."""
    if not phrase:
        return False
    p = phrase.strip().lower()
    if len(p) < 2:
        return False
    # P3patch.D: drop URLs/domains BEFORE the whitelist — the "word.word"
    # whitelist pattern (for node.js / react.js) otherwise lets "linkedin.com"
    # through. Web TLDs (.com/.org/...) don't collide with tech (.js/.io/.net).
    if _URL_RE.search(p):
        return False
    if is_whitelisted(p):
        return True
    if p in NON_SKILL_WORDS:
        return False
    if p in JD_NOISE_PHRASES:
        return False
    if p in SOFT_SKILL_BLACKLIST:
        return False
    # P3patch.D: drop job titles (e.g. "data analyst", "ml engineer").
    title_tokens = p.split()
    if title_tokens and title_tokens[-1] in JOB_TITLE_TAIL:
        return False
    if len(p.split()) > 3:
        return False
    if any(sub in p for sub in SKILL_NOISE_SUBSTRINGS):
        return False
    return True


# Academic-degree abbreviations are credentials, not skills. Rejected only when
# the entire phrase IS the degree token (so standalone "b.tech" no longer leaks,
# while a longer phrase that merely contains such a token is unaffected).
_DEGREE_ABBREVIATIONS = {
    "b.tech", "btech", "m.tech", "mtech", "b.e", "m.e", "b.sc", "bsc",
    "m.sc", "msc", "b.com", "bcom", "m.com", "mcom", "b.arch", "barch",
    "b.des", "bdes", "b.ed", "bed", "m.ed", "med", "b.pharm", "m.pharm",
    "bca", "mca", "bba", "mba", "phd", "ph.d", "mbbs", "bachelors", "masters",
}


def is_valid_jd_skill(phrase: str) -> bool:
    """JD-specific filter that removes legal/boilerplate and soft-skill noise."""
    p = normalize_skill(normalize_phrase(phrase))
    if p in _DEGREE_ABBREVIATIONS:
        return False
    if not is_valid_skill(p):
        return False
    tokens = p.split()
    if any(token in JD_TOKEN_BLACKLIST for token in tokens):
        return False
    if tokens and tokens[0] in JD_ACTION_VERBS:
        return False
    if tokens and tokens[0] in _JD_PREPOSITION_LEADS:
        return False
    # P3patch.A: reject value/behaviour fragments and imperative leads that
    # leak from "Accountabilities" / "Values" / leadership-behaviour prose:
    #   "be authentic", "to meet the needs", "e energise" (split fragment).
    if len(tokens) >= 2:
        if tokens[0] in {"be", "to", "by", "as"}:
            return False
        # A stray single-letter first token (not a real 1-letter skill like
        # C or R) signals a split fragment, e.g. "e energise".
        if len(tokens[0]) == 1 and tokens[0] not in {"c", "r"}:
            return False
    if tokens and tokens[-1] in JD_GENERIC_TAIL_TOKENS:
        return False
    if any(sub in p for sub in JD_NOISE_SUBSTRINGS):
        return False
    if re.search(r"\b(?:gender|religion|race|color|age|disability)\b", p):
        return False
    if re.search(r"\b\d+\+?\s*years?\b", p):
        return False
    if re.search(r"\b(?:engineers?|implement|hands?|degree|bachelor|master|phd|date)\b", p):
        return False
    if len(tokens) == 1 and not (
        is_whitelisted(p) or
        p in SKILL_ALIAS_MAP or
        p in SKILL_ALIAS_MAP.values() or
        p in SEMANTIC_SYNONYMS or
        p in _SYNONYM_REVERSE or
        p in TECH_SIGNAL_TOKENS
    ):
        return False
    return True


def clean_skills(skills: Iterable[str], cap: Optional[int] = 30) -> List[str]:
    """Filter noise, normalize aliases, deduplicate, cap length."""
    cleaned: List[str] = []
    for s in skills:
        if not s:
            continue
        p = s.lower().strip()
        if not is_valid_skill(p):
            continue
        p = normalize_skill(p)
        if p not in cleaned:
            cleaned.append(p)
    if cap is None:
        return cleaned
    return cleaned[:cap]


def has_technical_signal(phrase: str) -> bool:
    """Return True when a phrase contains at least one technical anchor."""
    p = normalize_skill(normalize_phrase(phrase))
    if not p:
        return False
    if is_whitelisted(p) or p in SKILL_ALIAS_MAP or p in SKILL_ALIAS_MAP.values():
        return True
    if p in SEMANTIC_SYNONYMS or p in _SYNONYM_REVERSE:
        return True
    tokens = {tok for tok in re.split(r"[\s/\-]+", p) if tok}
    return bool(tokens & TECH_SIGNAL_TOKENS)


def compute_token_overlap_ratio(phrase_a: str, phrase_b: str) -> float:
    """Compute overlap on normalized, non-trivial tokens."""
    stop_tokens = NON_SKILL_WORDS | JD_TOKEN_BLACKLIST | {"s"}
    tokens_a = {
        tok for tok in re.split(r"[\s/\-]+", normalize_phrase(phrase_a))
        if tok and tok not in stop_tokens
    }
    tokens_b = {
        tok for tok in re.split(r"[\s/\-]+", normalize_phrase(phrase_b))
        if tok and tok not in stop_tokens
    }
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / float(max(len(tokens_a), len(tokens_b)))


def _cluster_names_for_skill(phrase: str) -> set:
    tokens = {tok for tok in re.split(r"[\s/\-]+", normalize_skill(normalize_phrase(phrase))) if tok}
    normalized = normalize_skill(normalize_phrase(phrase))
    clusters = set()
    for name, members in SKILL_CLUSTERS.items():
        normalized_members = {normalize_skill(normalize_phrase(member)) for member in members}
        member_tokens = set().union(*(member.split() for member in normalized_members))
        if normalized in normalized_members or tokens & member_tokens:
            clusters.add(name)
    return clusters


def skills_share_cluster(left: str, right: str) -> bool:
    """Return True when two skills belong to at least one ontology cluster."""
    return bool(_cluster_names_for_skill(left) & _cluster_names_for_skill(right))


def clamp_match_score(match_type: str, similarity: float) -> float:
    """Clamp score into the configured range for a match tier."""
    low, high = MATCH_SCORE_BY_TYPE.get(match_type, (0.0, 1.0))
    if low == high:
        return round(low, 4)
    bounded = max(low, min(float(similarity or 0.0), high))
    return round(bounded, 4)


def split_skill_line(raw_line: str) -> List[str]:
    """Split multi-skill resume lines ('Languages: Python, Java') into tokens.

    Skips soft-skills categories entirely (non-technical, not useful).
    """
    if not raw_line:
        return []
    if ":" in raw_line:
        prefix = raw_line.split(":", 1)[0].strip().lower()
        if "soft" in prefix:
            return []
        raw_line = raw_line.split(":", 1)[1]
    tokens = re.split(r"[,;|]+", raw_line)
    results: List[str] = []
    for token in tokens:
        token = token.strip()
        if token and len(token) >= 2:
            results.append(token)
    return results


def deduplicate_phrases(phrases: Iterable[str]) -> List[str]:
    """Remove exact and substring-redundant duplicates while preserving order."""
    unique: List[str] = []
    for phrase in phrases:
        np_ = normalize_phrase(phrase)
        if len(np_) < 2 or np_ in NON_SKILL_WORDS or np_ in unique:
            continue
        redundant = False
        to_remove: List[str] = []
        np_tokens = np_.split()
        for existing in unique:
            existing_tokens = existing.split()
            if np_ == existing:
                redundant = True
                break
            if np_ in existing and len(np_tokens) <= len(existing_tokens):
                to_remove.append(existing)
            elif existing in np_ and len(existing_tokens) <= len(np_tokens):
                redundant = True
                break
        if redundant:
            continue
        if to_remove:
            unique = [item for item in unique if item not in to_remove]
        unique.append(np_)
    return unique


def merge_unique_skills(*skill_groups: Iterable[str], cap: Optional[int] = None) -> List[str]:
    """Merge multiple skill collections into a cleaned, ordered list."""
    merged: List[str] = []
    for group in skill_groups:
        for phrase in group or []:
            normalized = normalize_skill(normalize_phrase(phrase))
            if normalized and is_valid_skill(normalized) and normalized not in merged:
                merged.append(normalized)
                if cap is not None and len(merged) >= cap:
                    return merged
    return merged


# ---------------------------------------------------------------------------
# L4 — POS-based skill filtering (Phase 2)
# ---------------------------------------------------------------------------

_spacy_nlp = None
_SPACY_AVAILABLE: Optional[bool] = None


def _load_spacy():
    """Load spaCy en_core_web_sm lazily. Sets _SPACY_AVAILABLE flag."""
    global _spacy_nlp, _SPACY_AVAILABLE
    if _SPACY_AVAILABLE is not None:
        return
    try:
        import spacy
        _spacy_nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
        _SPACY_AVAILABLE = True
        logger.info("spaCy en_core_web_sm loaded — POS filtering enabled.")
    except Exception:
        _SPACY_AVAILABLE = False
        logger.info("spaCy model not available — POS filtering disabled (graceful fallback).")


def filter_non_skill_phrases_pos(phrases: List[str]) -> List[str]:
    """Keep only noun-bearing phrases using spaCy POS tagging."""
    _load_spacy()
    if not _SPACY_AVAILABLE or _spacy_nlp is None:
        return list(phrases)

    filtered: List[str] = []
    for phrase in phrases:
        if is_whitelisted(phrase):
            filtered.append(phrase)
            continue
        doc = _spacy_nlp(phrase)
        has_noun = any(t.pos_ in ("NOUN", "PROPN") for t in doc)
        all_non_noun = all(t.pos_ in ("VERB", "ADV", "ADJ", "ADP", "DET", "AUX", "SCONJ", "CCONJ") for t in doc)
        if has_noun and not all_non_noun:
            filtered.append(phrase)
    return filtered
