"""Role extraction, domain detection, seniority detection, prioritization,
and the ``parse_jd`` orchestrator.

The optional SBERT enhancement hooks (``sbert_model``, ``util``) live here as
module-level globals. The scoring layer can attach a model by assigning to
``app.services.jd_parser.analysis.sbert_model``; when None (the default),
``detect_domain_multi`` falls back to keyword-only scoring.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.utils.text_cleaning import normalize_jd_text

from .constants import (
    DOMAIN_KEYWORDS,
    JOB_TITLE_WORDS,
    SENIORITY_KEYWORD_MAP,
    SENIORITY_LEVELS,
    SENIORITY_TITLE_PREFIXES,
)
from .models import DomainScores, PrioritizedRequirement, RoleResult, SeniorityResult
from .skills import (
    _detect_requires_academics,
    _detect_requires_achievements,
    extract_education_level,
    extract_experience_requirement,
    extract_skills_from_jd,
)


# Optional SBERT model handle. Loaded by the matching/scoring layer (Phase 5).
# Kept here for parity with the original detect_domain implementation.
sbert_model = None
util = None  # set by the scoring layer when SBERT is loaded


def extract_role_title(text: str) -> str:
    """Extract the most likely job title (backward-compatible string return)."""
    result = extract_role_title_enhanced(text)
    return result.title


def extract_role_title_enhanced(text: str) -> RoleResult:
    """Extract the most likely job title with confidence scoring.

    Phase 2 enhancement: returns a RoleResult with the extracted title,
    confidence level (high/medium/low), and extraction method used.
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title_noise = {
        "about the job", "about the role", "job description", "responsibilities",
        "job responsibilities",
        "requirements", "about us", "about the team",
    }

    # Method 1: Heading extraction (first 5 lines, high confidence).
    #
    # Section-header rejection uses singular stems so plural forms are
    # caught via substring match:
    #   "requirement"     -> matches "requirement"  AND "requirements"
    #   "qualification"   -> matches "qualification" AND "qualifications"
    #   "responsibilit"   -> matches "responsibility" AND "responsibilities"
    #   "preferred"       -> matches "preferred"     (no plural)
    #   "education"       -> matches "education"     AND "educational"
    #   "experience"      -> matches "experience"    AND "experienced"
    # Using "required" (past tense) instead of "requirement" would NOT match
    # "requirements" (they diverge at char 8 — d vs m); that hole previously
    # caused JDs starting with "Requirements And Qualification" to return
    # the section header as the role title.
    section_header_stems = (
        "requirement", "preferred", "education", "experience",
        "qualification", "responsibilit",
        # P7.2 additions. These header words never appear in a real job
        # title, so rejecting any line containing them is safe and stops
        # section headers from being misread as the role:
        #   "reponsibilit" — observed misspelling of "responsibilit" (JD_4)
        #   "about"        — "About This Role" / "About Us" / "About the company" (JD_5)
        #   "overview" / "scope" / "summary" — generic section headers
        #   "eligibilit"   — "Eligibility" sections
        #   "core skill" / "key skill" / "what you" — skill-section headers
        "reponsibilit", "about", "overview", "scope", "summary",
        "eligibilit", "core skill", "key skill", "what you", "who you",
    )
    # P7.2: pronoun/auxiliary-verb tokens signal a sentence fragment, not a
    # job title (e.g. "In This Role, You Will ..."). Real titles are noun
    # phrases and never contain these, so their presence rejects the line.
    sentence_signal_tokens = {
        "you", "your", "we", "our", "us", "this", "will", "be",
        "are", "is", "have", "they", "i",
    }
    # P3patch.B: a line that LEADS with one of these is a responsibility
    # bullet or a requirement stem, not a job title. Observed failures:
    #   "Write well designed, testable code"  (JD-7, imperative)
    #   "Proficient in Python, SAS, SQL"      (JD-9, requirement stem)
    #   "Ensure designs are in compliance"    (imperative)
    imperative_or_requirement_leads = {
        # imperative responsibility verbs
        "write", "ensure", "build", "develop", "design", "create", "contribute",
        "perform", "manage", "collaborate", "identify", "maintain", "provide",
        "implement", "deliver", "drive", "support", "lead", "execute", "conduct",
        "analyze", "analyse", "optimize", "optimise", "review", "coordinate",
        "monitor", "assist", "participate", "handle", "own", "deploy", "test",
        # requirement stems
        "proficient", "proficiency", "experience", "experienced", "knowledge",
        "ability", "able", "strong", "expertise", "familiarity", "familiar",
        "understanding", "hands-on", "skilled", "competent", "demonstrated",
        "proven", "working",
    }

    def _is_rejected_title(candidate_lower: str) -> bool:
        """Return True if a candidate string is a section header, sentence
        fragment, responsibility bullet, or requirement stem — not a title."""
        if not candidate_lower:
            return True
        if any(stem in candidate_lower for stem in section_header_stems):
            return True
        tokens_list = re.findall(r"[a-z][a-z\-]*", candidate_lower)
        if tokens_list and tokens_list[0] in imperative_or_requirement_leads:
            return True
        tokens = set(tokens_list)
        if tokens & sentence_signal_tokens:
            return True
        return False

    # Words that terminate a job title when a greedy pattern capture runs on
    # into the surrounding sentence (e.g. "Senior Data Scientist to join our
    # team" → truncate at "to" → "Senior Data Scientist"). "of" is excluded
    # because it appears in real titles ("VP of Engineering").
    title_terminators = {
        "to", "within", "who", "that", "for", "and", "with", "at",
        "in", "on", "join", "will", "you", "your", "our", "we",
        "is", "are", "as", "by", "from", "the",
    }

    def _truncate_role_at_boundary(role: str) -> str:
        out = []
        for tok in role.split():
            if tok.lower() in title_terminators:
                break
            out.append(tok)
        return " ".join(out).strip(" -:;,.")

    # P3patch.B: a real job title names a ROLE — it contains a role noun
    # (engineer, developer, analyst, intern, manager, ...). Requiring one for
    # the high-confidence heading path rejects header fragments like
    # "Development Implementation" (no role noun) while keeping genuine titles
    # ("Full Stack Developer", "Decision Analyst"). JOB_TITLE_WORDS already
    # enumerates these role nouns.
    role_nouns = JOB_TITLE_WORDS - {"hiring", "looking", "senior", "junior"}
    for candidate_line in lines[:5]:
        lowered_first = candidate_line.lower()
        if lowered_first in title_noise:
            continue
        if _is_rejected_title(lowered_first):
            continue
        if len(candidate_line.split()) <= 6 and any(ch.isalpha() for ch in candidate_line):
            cand_tokens = set(re.findall(r"[a-z]+", lowered_first))
            if not (cand_tokens & role_nouns):
                continue  # no role noun → not a title (likely a section header)
            title = re.sub(r"\s+", " ", candidate_line).strip(" -:;,.")
            if title:
                return RoleResult(
                    title=title,
                    confidence="high",
                    extraction_method="heading",
                )

    # Method 2: Pattern-based extraction (medium confidence).
    # Specific, article-bearing patterns lead; the greedy bare "hiring X"
    # pattern is last so it can't pre-empt a better match. Any capture that
    # is itself a section header / sentence fragment is skipped, falling
    # through to the next pattern (P7.2: this stops "hiring requirements"
    # from beating "seeking a Software Engineer").
    role_patterns = [
        r"seeking an? ([a-zA-Z][a-zA-Z \-/]+)",
        r"looking for an? ([a-zA-Z][a-zA-Z \-/]+)",
        r"hiring an? ([a-zA-Z][a-zA-Z \-/]+)",
        r"role:\s*([a-zA-Z][a-zA-Z \-/]+)",
        r"position:\s*([a-zA-Z][a-zA-Z \-/]+)",
        r"title:\s*([a-zA-Z][a-zA-Z \-/]+)",
        r"as an? ([a-zA-Z][a-zA-Z \-/]+?) within",
        r"as an? ([a-zA-Z][a-zA-Z \-/]+?)[,\.]",
        r"opportunity for an? ([a-zA-Z][a-zA-Z \-/]+)",
        r"join\s+(?:us|our team)\s+as\s+(?:an?\s+)?([a-zA-Z][a-zA-Z \-/]+)",
        r"hiring ([a-zA-Z][a-zA-Z \-/]+)",  # greedy fallback — last
    ]
    lowered = text.lower()
    for pattern in role_patterns:
        match = re.search(pattern, lowered)
        if not match:
            continue
        role = re.sub(r"\s+", " ", match.group(1)).strip(" -:;,.")
        role = _truncate_role_at_boundary(role)
        if role and not _is_rejected_title(role):
            return RoleResult(
                title=role.title(),
                confidence="medium",
                extraction_method="pattern",
            )

    return RoleResult(
        title="not_specified",
        confidence="low",
        extraction_method="fallback",
    )


def detect_domain(text: str) -> str:
    """Detect JD domain (backward-compatible string return).

    When sbert_model is None (Phase 1 default), falls back to keyword-only
    detection (preserves original behavior of the SBERT-disabled path).
    """
    result = detect_domain_multi(text)
    return result.primary


def detect_domain_multi(text: str) -> DomainScores:
    """Detect JD domain with multi-domain scoring.

    Phase 2 enhancement: returns a DomainScores with primary domain,
    optional secondary domain, and a full score dict across all domains.
    Scores are normalized to 0.0–1.0 range.
    """
    lowered = normalize_jd_text(text)

    # Step 1: Keyword-based scoring
    kw_scores: Dict[str, int] = {domain: 0 for domain in DOMAIN_KEYWORDS}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                kw_scores[domain] += 1

    # Step 2: Normalize scores to 0.0–1.0.
    # P3patch.C: normalize by a FIXED saturation count, NOT by the domain's
    # keyword-list length. The old `count / len(keywords)` penalized domains
    # with longer keyword lists (expanding software_dev to 23 terms diluted
    # its per-match weight and flipped JD_5 to 'design'). A fixed denominator
    # means "more matches → higher score" regardless of list size; 3 matches
    # saturates to 1.0.
    DOMAIN_SATURATION = 3.0
    normalized_scores: Dict[str, float] = {}
    for domain, count in kw_scores.items():
        normalized_scores[domain] = round(min(count / DOMAIN_SATURATION, 1.0), 4)

    # Step 3: SBERT enhancement (when available)
    if sbert_model is not None and util is not None:
        domain_descriptions = {
            "data_science": "data science machine learning deep learning statistics analytics data analysis modeling",
            "software_dev": "software development engineering full stack backend frontend web application api programming",
            "business": "business analysis strategy finance operations management marketing consulting",
            "freshers": "fresher entry level campus hire graduate trainee junior position",
            "devops": "devops site reliability infrastructure cicd kubernetes docker terraform cloud deployment",
            "cybersecurity": "cybersecurity information security penetration testing vulnerability soc threat analysis",
            "product_management": "product management strategy roadmap stakeholder user stories agile sprint planning",
            "design": "ui ux design user experience user interface figma sketch prototyping design system",
        }
        jd_embedding = sbert_model.encode(lowered[:500], convert_to_numpy=True)
        for domain, description in domain_descriptions.items():
            desc_embedding = sbert_model.encode(description, convert_to_numpy=True)
            sim = float(util.cos_sim(jd_embedding, desc_embedding).item())
            # Blend: 60% keyword, 40% SBERT
            kw_component = normalized_scores.get(domain, 0.0)
            normalized_scores[domain] = round(0.6 * kw_component + 0.4 * sim, 4)

    # Step 4: Determine primary and secondary domains
    sorted_domains = sorted(normalized_scores.items(), key=lambda x: x[1], reverse=True)

    primary = sorted_domains[0][0] if sorted_domains else "freshers"
    primary_score = sorted_domains[0][1] if sorted_domains else 0.0

    # Only assign primary if it has a meaningful score
    if primary_score == 0.0:
        primary = "freshers"

    # Secondary domain: must have a non-zero score and be different from primary
    secondary = None
    if len(sorted_domains) > 1 and sorted_domains[1][1] > 0.0:
        secondary = sorted_domains[1][0]

    return DomainScores(
        primary=primary,
        secondary=secondary,
        scores=normalized_scores,
    )


def parse_jd(text: str) -> Dict[str, object]:
    """Parse a job description into structured requirements."""
    if not isinstance(text, str) or not text.strip():
        return {
            "required_skills": [], "preferred_skills": [], "optional_skills": [],
            "experience_years": 0, "education_level": "not_specified",
            "role_title": "not_specified", "domain_detected": "freshers",
            "raw_text": "",
            "_rejected_skill_candidates": [],
            "rules": {
                "requires_experience": False,
                "requires_academics": False,
                "requires_achievements": False,
                "requires_internship_emphasis": False,
            },
        }
    text = text.strip()
    skill_data = extract_skills_from_jd(text)
    exp_years = extract_experience_requirement(text)
    edu_level = extract_education_level(text)

    rules = {
        "requires_experience": exp_years > 0,
        "requires_academics": _detect_requires_academics(text),
        "requires_achievements": _detect_requires_achievements(text),
        "requires_internship_emphasis": False,
    }

    return {
        "required_skills": skill_data["required_skills"],
        "preferred_skills": skill_data["preferred_skills"],
        "optional_skills": skill_data.get("optional_skills", []),
        "experience_years": exp_years,
        "education_level": edu_level,
        "role_title": extract_role_title(text),
        "domain_detected": detect_domain(text),
        "raw_text": text,
        "_rejected_skill_candidates": skill_data.get("_rejected_skill_candidates", []),
        "rules": rules,
    }


# ─── Phase 2: Seniority Detection ───────────────────────────────────────────


def detect_seniority(
    text: str,
    experience_years: int = 0,
    role_title: str = "not_specified",
) -> SeniorityResult:
    """Detect the seniority level expected by a job description.

    Uses three signals in priority order:
    1. Explicit seniority keywords in the JD text
    2. Seniority prefixes in the extracted role title
    3. Required experience years as a fallback

    Args:
        text: Raw JD text.
        experience_years: Extracted minimum experience requirement.
        role_title: Extracted role title from the JD.

    Returns:
        SeniorityResult with level, confidence, and supporting signals.
    """
    lowered = text.lower()
    role_lower = role_title.lower() if role_title else ""
    signals: List[str] = []
    keyword_hits: Dict[str, int] = {level: 0 for level in SENIORITY_LEVELS}

    # Signal 1: Explicit keywords in JD text
    for level, keywords in SENIORITY_KEYWORD_MAP.items():
        for keyword in keywords:
            if keyword in lowered:
                keyword_hits[level] += 1
                signals.append(f"keyword '{keyword}' → {level}")

    # Find the level with most keyword hits
    best_keyword_level = max(keyword_hits, key=keyword_hits.get)
    best_keyword_count = keyword_hits[best_keyword_level]

    # Signal 2: Role title prefix
    title_level: Optional[str] = None
    for level, prefixes in SENIORITY_TITLE_PREFIXES.items():
        for prefix in prefixes:
            if role_lower.startswith(prefix):
                title_level = level
                signals.append(f"role title prefix '{prefix}' → {level}")
                break
        if title_level:
            break

    # Signal 3: Experience years fallback
    exp_level: Optional[str] = None
    if experience_years > 0:
        if experience_years <= 1:
            exp_level = "junior"
        elif experience_years <= 3:
            exp_level = "mid"
        elif experience_years <= 5:
            exp_level = "mid"
        elif experience_years <= 9:
            exp_level = "senior"
        elif experience_years <= 14:
            exp_level = "lead"
        else:
            exp_level = "executive"
        signals.append(f"experience {experience_years} years → {exp_level}")

    # Decision logic
    if best_keyword_count >= 2:
        # Strong keyword signal — high confidence
        return SeniorityResult(
            level=best_keyword_level,
            confidence="high",
            signals=signals,
        )

    if title_level and best_keyword_count >= 1 and title_level == best_keyword_level:
        # Title and keyword agree — high confidence
        return SeniorityResult(
            level=title_level,
            confidence="high",
            signals=signals,
        )

    if title_level:
        # Title prefix found — medium confidence
        return SeniorityResult(
            level=title_level,
            confidence="medium",
            signals=signals,
        )

    if best_keyword_count >= 1:
        # Single keyword — medium confidence
        return SeniorityResult(
            level=best_keyword_level,
            confidence="medium",
            signals=signals,
        )

    if exp_level:
        # Experience fallback — low confidence
        return SeniorityResult(
            level=exp_level,
            confidence="low",
            signals=signals,
        )

    # No signals at all — default to mid with low confidence
    return SeniorityResult(
        level="mid",
        confidence="low",
        signals=["no explicit seniority signals found, defaulting to mid"],
    )


# ─── Phase 2: Requirement Prioritization ─────────────────────────────────────


def prioritize_requirements(
    skills_data: Dict[str, List[str]],
    seniority_level: str = "mid",
) -> List[PrioritizedRequirement]:
    """Rank extracted JD skills by importance.

    Priority assignment rules:
    1. Required skills → "critical" (top half) or "high" (bottom half, if >10)
    2. Preferred skills → "medium"
    3. Optional skills → "low"
    4. Earlier position within a bucket = higher priority
    5. Seniority adjustments: not yet implemented (reserved for future use)

    Args:
        skills_data: Dict with keys "required_skills", "preferred_skills",
                     "optional_skills" (lists of skill strings).
        seniority_level: Detected seniority level (currently reserved).

    Returns:
        List of PrioritizedRequirement objects, sorted by priority.
    """
    requirements: List[PrioritizedRequirement] = []

    required_skills = skills_data.get("required_skills", [])
    preferred_skills = skills_data.get("preferred_skills", [])
    optional_skills = skills_data.get("optional_skills", [])

    # Required skills: split into critical (top half) and high (bottom half)
    critical_cutoff = len(required_skills) // 2 if len(required_skills) > 10 else len(required_skills)

    for i, skill in enumerate(required_skills):
        if i < critical_cutoff:
            priority = "critical"
            reason = "required skill, high position in JD"
        else:
            priority = "high"
            reason = "required skill, lower position in JD"
        requirements.append(PrioritizedRequirement(
            skill=skill,
            bucket="required",
            priority=priority,
            priority_reason=reason,
            position=i,
        ))

    # Preferred skills → medium
    for i, skill in enumerate(preferred_skills):
        requirements.append(PrioritizedRequirement(
            skill=skill,
            bucket="preferred",
            priority="medium",
            priority_reason="preferred skill",
            position=i,
        ))

    # Optional skills → low
    for i, skill in enumerate(optional_skills):
        requirements.append(PrioritizedRequirement(
            skill=skill,
            bucket="optional",
            priority="low",
            priority_reason="optional skill",
            position=i,
        ))

    return requirements
