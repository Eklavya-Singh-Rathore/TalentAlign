"""JD parser package.

Public API re-exports so callers continue to do::

    from app.services.jd_parser import parse_jd, detect_seniority

unchanged from before the split. Internals live in:
  * :mod:`.constants` — section cues, domain keywords, seniority taxonomies
  * :mod:`.models`    — SeniorityResult / RoleResult / DomainScores / PrioritizedRequirement
  * :mod:`.skills`    — JD skill mining + experience / education / rule helpers
  * :mod:`.analysis`  — role / domain / seniority / prioritization + ``parse_jd``

The ``sbert_model`` and ``util`` module-level globals live in :mod:`.analysis`;
the scoring layer can attach a model by assigning to
``app.services.jd_parser.analysis.sbert_model`` (the original module-attribute
contract via ``app.services.jd_parser.sbert_model`` is also surfaced here but
re-export semantics mean direct attribute assignment to this namespace does
not propagate into ``analysis``).
"""

from __future__ import annotations

from .analysis import (
    detect_domain,
    detect_domain_multi,
    detect_seniority,
    extract_role_title,
    extract_role_title_enhanced,
    parse_jd,
    prioritize_requirements,
    sbert_model,
    util,
)
from .constants import (
    DOMAIN_KEYWORDS,
    GENERIC_SKIP_PHRASES,
    JOB_TITLE_WORDS,
    PREFERRED_CUES,
    REQUIRED_CUES,
    SENIORITY_KEYWORD_MAP,
    SENIORITY_LEVELS,
    SENIORITY_TITLE_PREFIXES,
)
from .models import (
    DomainScores,
    PrioritizedRequirement,
    RoleResult,
    SeniorityResult,
)
from .skills import (
    extract_education_level,
    extract_experience_requirement,
    extract_skills_from_jd,
    _extract_candidates_from_text,
    _normalize_skill_phrase,
)


__all__ = [
    # Constants
    "REQUIRED_CUES",
    "PREFERRED_CUES",
    "GENERIC_SKIP_PHRASES",
    "DOMAIN_KEYWORDS",
    "JOB_TITLE_WORDS",
    "SENIORITY_LEVELS",
    "SENIORITY_KEYWORD_MAP",
    "SENIORITY_TITLE_PREFIXES",
    # SBERT hooks
    "sbert_model",
    "util",
    # Dataclasses
    "SeniorityResult",
    "RoleResult",
    "DomainScores",
    "PrioritizedRequirement",
    # Extraction
    "extract_skills_from_jd",
    "extract_experience_requirement",
    "extract_education_level",
    # Analysis
    "extract_role_title",
    "extract_role_title_enhanced",
    "detect_domain",
    "detect_domain_multi",
    "detect_seniority",
    "prioritize_requirements",
    "parse_jd",
]
