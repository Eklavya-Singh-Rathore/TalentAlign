"""Skill normalization package.

Public API is re-exported here so callers continue to do::

    from app.utils.skill_normalization import normalize_skill, SKILL_ALIAS_MAP

unchanged from before the split. Internals live in:
  * :mod:`.constants` — shared data (alias map, synonyms, blacklists, weights)
  * :mod:`.text`      — basic normalization, synonyms, adaptive threshold
  * :mod:`.filters`   — validation, cleaning, cluster, POS filter
  * :mod:`.extraction` — section detection and skill extraction
  * :mod:`.scoring`   — DebugLog and weighted/hybrid score computation
"""

from __future__ import annotations

from .constants import (
    JD_ACTION_VERBS,
    JD_BUCKET_WEIGHTS,
    JD_GENERIC_TAIL_TOKENS,
    JD_NOISE_PHRASES,
    JD_NOISE_SUBSTRINGS,
    JD_TOKEN_BLACKLIST,
    MATCH_SCORE_BY_TYPE,
    NON_SKILL_WORDS,
    SEMANTIC_SYNONYMS,
    SHORT_SKILL_WHITELIST,
    SKILL_ALIAS_MAP,
    SKILL_CLUSTERS,
    SKILL_NOISE_SUBSTRINGS,
    SKILL_SCORE_COMPONENT_WEIGHTS,
    SOFT_SKILL_BLACKLIST,
    TECH_SIGNAL_TOKENS,
    WHITELIST_PATTERNS,
)
from .extraction import (
    RESUME_SECTION_ALIASES,
    SECTION_PATTERNS,
    clean_jd_skill_phrases,
    extract_skills_from_full_text,
    extract_skills_from_section,
    split_resume_into_sections,
)
from .filters import (
    clamp_match_score,
    clean_skills,
    compute_token_overlap_ratio,
    deduplicate_phrases,
    filter_non_skill_phrases_pos,
    has_technical_signal,
    is_valid_jd_skill,
    is_valid_skill,
    merge_unique_skills,
    skills_share_cluster,
    split_skill_line,
)
from .scoring import (
    DebugLog,
    compute_hybrid_skill_score,
    compute_optimal_top_n,
    compute_phrase_specificity_weight,
    compute_weighted_skill_score,
)
from .text import (
    DEFAULT_MATCH_THRESHOLD,
    compute_adaptive_threshold,
    get_synonyms,
    is_synonym_match,
    is_whitelisted,
    normalize_phrase,
    normalize_skill,
    normalize_text,
    normalize_text_for_skills,
)


__all__ = [
    "NON_SKILL_WORDS",
    "JD_NOISE_PHRASES",
    "SKILL_NOISE_SUBSTRINGS",
    "JD_NOISE_SUBSTRINGS",
    "JD_TOKEN_BLACKLIST",
    "JD_ACTION_VERBS",
    "JD_GENERIC_TAIL_TOKENS",
    "TECH_SIGNAL_TOKENS",
    "SOFT_SKILL_BLACKLIST",
    "WHITELIST_PATTERNS",
    "SHORT_SKILL_WHITELIST",
    "SKILL_ALIAS_MAP",
    "JD_BUCKET_WEIGHTS",
    "MATCH_SCORE_BY_TYPE",
    "SKILL_SCORE_COMPONENT_WEIGHTS",
    "SKILL_CLUSTERS",
    "is_whitelisted",
    "is_valid_skill",
    "is_valid_jd_skill",
    "has_technical_signal",
    "normalize_skill",
    "normalize_text_for_skills",
    "normalize_text",
    "normalize_phrase",
    "clean_skills",
    "compute_token_overlap_ratio",
    "skills_share_cluster",
    "clamp_match_score",
    "split_skill_line",
    "deduplicate_phrases",
    "merge_unique_skills",
    "RESUME_SECTION_ALIASES",
    "SECTION_PATTERNS",
    "split_resume_into_sections",
    "extract_skills_from_section",
    "extract_skills_from_full_text",
    "clean_jd_skill_phrases",
    "DebugLog",
    "DEFAULT_MATCH_THRESHOLD",
    "compute_adaptive_threshold",
    "SEMANTIC_SYNONYMS",
    "get_synonyms",
    "is_synonym_match",
    "filter_non_skill_phrases_pos",
    "compute_optimal_top_n",
    "compute_phrase_specificity_weight",
    "compute_weighted_skill_score",
    "compute_hybrid_skill_score",
]
