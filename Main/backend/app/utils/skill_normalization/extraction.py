"""Section detection + multi-source skill extraction.

Resume header aliases, section splitter, "tech stack:" line miner, and the
full-text fallback for resumes without reliable section markers.
"""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Tuple

from .constants import SEMANTIC_SYNONYMS, SKILL_ALIAS_MAP
from .filters import (
    clean_skills,
    deduplicate_phrases,
    has_technical_signal,
    is_valid_jd_skill,
    is_valid_skill,
    split_skill_line,
)
from .text import normalize_phrase, normalize_skill, normalize_text_for_skills


# ---------------------------------------------------------------------------
# L8 — Multi-source skill aggregation helper
# ---------------------------------------------------------------------------

_TECH_STACK_RE = re.compile(r"tech\s*stack\s*[:\-]\s*(.+)", re.IGNORECASE)

RESUME_SECTION_ALIASES: Dict[str, Tuple[str, ...]] = {
    "skills": (
        "skills", "technical skills", "core skills", "key skills", "skill set",
        "technical expertise", "technologies", "tools and technologies",
        "tools & technologies", "programming languages", "languages",
        "competencies", "core competencies", "technical proficiency",
        "technical toolkit", "technology stack", "tech stack",
        # Phase 1 (P1.4) additions
        "tools", "tech skills", "engineering skills", "stack",
        "software skills", "tools and skills",
    ),
    "projects": (
        "project", "projects", "academic project", "academic projects",
        "personal project", "personal projects", "key projects",
        "project experience", "notable projects", "project work",
        "projects & achievements", "major projects", "side projects",
        "project details", "project detail",
        # Phase 1 (P1.4) additions
        "selected projects", "open source contributions", "open source projects",
        "capstone project", "capstone projects", "research projects",
        "course projects", "featured projects",
    ),
    "certifications": (
        "certification", "certifications", "certificate", "certificates",
        "licenses & certifications", "professional certifications",
        "courses & certifications", "online courses", "training",
        "courses", "professional development",
        # Phase 1 (P1.4) additions
        "credentials", "licenses", "trainings", "certifications & training",
        "certifications and training", "licenses and certifications",
    ),
    "internships": (
        "internship", "internships", "internship experience",
        "industrial training", "industry experience", "summer internship",
        "summer internships", "internship & training", "internship details",
        # Phase 1 (P1.4) additions
        "internship history", "trainee experience", "intern experience",
    ),
    "work_experience": (
        "work experience", "experience", "professional experience",
        "employment history", "employment", "career history",
        "relevant experience", "job experience", "work history",
        # Phase 1 (P1.4) additions
        "professional history", "industry experience", "career experience",
        "work and experience",
    ),
    "education": (
        "education", "educational background", "academic background",
        "academic qualification", "academic qualifications", "qualifications",
        "academic details", "scholastic details", "academic history",
        # Phase 1 (P1.4) additions
        "education & training", "education and training", "academic profile",
    ),
    "achievements": (
        "achievement", "achievements", "accomplishment", "accomplishments",
        "award", "awards", "honors", "honours", "awards & honors",
        "awards & achievements", "recognition",
        "extra-curricular activities", "extracurricular activities",
        "extracurriculars", "leadership", "activities", "competition",
        "competitions", "hackathon", "hackathons",
        # Phase 1 (P1.4) additions
        "honors and awards", "honors & awards", "awards and recognition",
        "publications", "publications & talks", "extra curricular",
        "co-curricular activities", "co curricular activities",
        "volunteer experience", "volunteering",
    ),
}


def _compile_section_patterns() -> Dict[str, re.Pattern]:
    patterns: Dict[str, re.Pattern] = {}
    for section_key, aliases in RESUME_SECTION_ALIASES.items():
        escaped = "|".join(re.escape(alias) for alias in aliases)
        patterns[section_key] = re.compile(rf"^\s*(?:{escaped})\s*[:\-]?\s*$", re.IGNORECASE)
    return patterns


SECTION_PATTERNS: Dict[str, re.Pattern] = _compile_section_patterns()


# Phase 1 (P1.3): tolerate decorated headers like
#   "=== Skills ===", "### Skills", "--- Skills ---", "*** Skills ***",
#   "> Skills", "■ Skills", "Skills."
# Decoration is stripped from both ends before SECTION_PATTERNS is consulted,
# so the strict alias regex stays simple and the alias map stays the source
# of truth for header names.
_HEADER_LEADING_DECORATION = re.compile(r"^[\s\-=*#>~_|·▪■▫□◆◇►▶▸★✦❖]+")
_HEADER_TRAILING_DECORATION = re.compile(r"[\s\-=*#>~_|:.·▪■▫□◆◇►▶▸★✦❖]+$")


def _normalize_header_candidate(line: str) -> str:
    """Strip decorative prefixes/suffixes so SECTION_PATTERNS can match the bare alias."""
    line = _HEADER_LEADING_DECORATION.sub("", line)
    line = _HEADER_TRAILING_DECORATION.sub("", line)
    return line.strip()


def _match_section_key(stripped_line: str) -> Optional[str]:
    """Return the section key whose alias matches *stripped_line*, or None."""
    for section_key, pattern in SECTION_PATTERNS.items():
        if pattern.match(stripped_line):
            return section_key
    candidate = _normalize_header_candidate(stripped_line)
    if candidate == stripped_line:
        return None  # nothing was stripped; strict pass already failed
    for section_key, pattern in SECTION_PATTERNS.items():
        if pattern.match(candidate):
            return section_key
    return None


def split_resume_into_sections(raw_text: str) -> Dict[str, List[str]]:
    """Split resume text into structured sections using shared header patterns."""
    sections = {key: [] for key in RESUME_SECTION_ALIASES}
    if not raw_text:
        return sections

    current_section = None
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        matched_section = _match_section_key(stripped)
        if matched_section:
            current_section = matched_section
            continue
        if current_section is not None:
            sections[current_section].append(stripped)
    return sections


def extract_skills_from_section(section_entries: Iterable) -> List[str]:
    """Pull skill-like tokens from a free-form section (projects, internships,
    work_experience). Looks for 'Tech Stack:' / 'Technologies:' / 'Skills:'
    lines and comma-separated lists.
    """
    results: List[str] = []
    if not section_entries:
        return results
    for entry in section_entries:
        text = entry if isinstance(entry, str) else (
            " ".join(str(v) for v in entry.values()) if isinstance(entry, dict) else ""
        )
        if not text:
            continue
        for line in text.splitlines():
            line = line.strip()
            m = _TECH_STACK_RE.search(line)
            payload = None
            if m:
                payload = m.group(1)
            elif ":" in line and any(
                kw in line.lower().split(":", 1)[0]
                for kw in ("technolog", "skill", "stack", "tools")
            ):
                payload = line.split(":", 1)[1]
            if payload:
                for tok in split_skill_line(payload):
                    p = normalize_skill(normalize_phrase(tok))
                    if is_valid_skill(p) and p not in results:
                        results.append(p)
    return results


_KNOWN_FALLBACK_SKILLS: Optional[List[str]] = None


def _get_known_fallback_skills() -> List[str]:
    global _KNOWN_FALLBACK_SKILLS
    if _KNOWN_FALLBACK_SKILLS is None:
        phrases = (
            list(SKILL_ALIAS_MAP.keys()) +
            list(SKILL_ALIAS_MAP.values()) +
            list(SEMANTIC_SYNONYMS.keys()) +
            [syn for syns in SEMANTIC_SYNONYMS.values() for syn in syns]
        )
        _KNOWN_FALLBACK_SKILLS = sorted({
            normalize_skill(phrase)
            for phrase in phrases
            if phrase and is_valid_skill(normalize_phrase(phrase))
        }, key=lambda item: (-len(item.split()), -len(item), item))
    return list(_KNOWN_FALLBACK_SKILLS)


def extract_skills_from_full_text(text: str, cap: int = 25) -> List[str]:
    """Fallback skill mining for resumes without reliable sectioning.

    Phase 1 (P1.5): tightened so non-technical phrases (names, education
    blurbs, partial sentences) are filtered out via has_technical_signal.
    Lines with a short "Label: payload" structure are stripped to the payload
    before tokenization, so headers like "Tech Stack: TensorFlow, PyTorch"
    don't contaminate the candidate list with "tech stack tensorflow".
    """
    if not text or not text.strip():
        return []

    candidates: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # Strip "Label: payload" prefix when the label looks like a header.
        if ":" in stripped:
            prefix, _, payload = stripped.partition(":")
            if 1 <= len(prefix.split()) <= 4:
                stripped = payload.strip()
                if not stripped:
                    continue
        for chunk in re.split(r"[,;|•/\t]+", stripped):
            phrase = normalize_skill(normalize_phrase(chunk))
            if not phrase or not is_valid_skill(phrase):
                continue
            if not has_technical_signal(phrase):
                continue
            candidates.append(phrase)

    normalized_text = f" {normalize_text_for_skills(text)} "
    for phrase in _get_known_fallback_skills():
        if f" {phrase} " in normalized_text:
            candidates.append(phrase)

    return clean_skills(deduplicate_phrases(candidates), cap=cap)


def clean_jd_skill_phrases(phrases: Iterable[str], cap: int = 40) -> List[str]:
    """Normalize and filter JD skill phrases more aggressively than resume skills."""
    cleaned: List[str] = []
    for phrase in phrases or []:
        normalized = normalize_skill(normalize_phrase(phrase))
        if not normalized or not is_valid_jd_skill(normalized):
            continue
        if normalized not in cleaned:
            cleaned.append(normalized)
            if len(cleaned) >= cap:
                break
    return cleaned
