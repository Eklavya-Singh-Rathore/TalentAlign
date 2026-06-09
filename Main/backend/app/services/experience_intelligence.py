"""Experience Intelligence Engine — Phase 3 orchestrator.

Evaluates real candidate experience depth by analyzing internships,
work experience, and durations from parsed resumes against JD requirements.

Pipeline:
    Parsed Resume + JD Intelligence →
        Extract Internships →
        Extract Durations →
        Detect Relevance →
        Score Quality →
        Classify Candidate →
        Structured Output

Design decisions:
  - No SBERT dependency (keyword-based relevance for now; Phase 5 adds SBERT).
  - Works with the raw section strings from resume_parser.py.
  - Integrates with JD Intelligence Engine output for relevance matching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set

from app.utils.duration_extraction import (
    DurationResult,
    AggregatedDuration,
    aggregate_durations,
    extract_duration_months,
    get_duration_factor,
)
from app.utils.skill_normalization import normalize_skill, normalize_phrase


# Matches "Intern", "Internship", "Trainee", "Apprentice" as standalone words
# (case-insensitive). Used by _reclassify_internship_entries to detect
# internship-titled entries that landed in work_experience because the PDF's
# section header was "Experience" rather than "Internships".
_INTERN_TITLE_RE = re.compile(
    r"\b(?:intern(?:ship)?|trainee|apprentice|co-?op)\b",
    re.IGNORECASE,
)

# Leading characters that mark a bullet / list body line (vs a role header).
_ROLE_BODY_PREFIXES = ("-", "•", "*", "◦", "·", "‣", "▪", "–", "—", "+")


def _looks_like_role_header(entry: str) -> bool:
    """Heuristic: a short, capitalized, non-bullet line that introduces a role
    (company or job title), as opposed to a bullet point or a wrapped sentence
    body line. Used to locate role-block boundaries during reclassification."""
    s = entry.strip()
    if not s or s[0] in _ROLE_BODY_PREFIXES:
        return False
    if len(s) > 65:  # role headers are short; long lines are body sentences
        return False
    first_alpha = next((c for c in s if c.isalpha()), "")
    return first_alpha.isupper()


def _is_date_anchor(entry: str) -> bool:
    """True when an entry is a role's date-range line (one per role)."""
    return extract_duration_months(entry).extraction_method == "date_range"


def _segment_role_blocks(
    work_experience: List[str], anchors: List[int]
) -> List[tuple[int, int]]:
    """Segment a flat work_experience list into per-role ``[start, end)`` blocks.

    Date-range lines are the anchors (one per role). The boundary before each
    role is found by walking back over its short header cluster (company/title
    lines), capped at 4 lines to avoid swallowing the previous role's body.
    """
    anchor_set = set(anchors)
    boundaries = [0]
    for a in anchors[1:]:
        idx = a - 1
        steps = 0
        while (
            idx > boundaries[-1]
            and idx not in anchor_set
            and steps < 4
            and _looks_like_role_header(work_experience[idx])
        ):
            idx -= 1
            steps += 1
        boundaries.append(idx + 1)
    boundaries.append(len(work_experience))
    return [(boundaries[k], boundaries[k + 1]) for k in range(len(boundaries) - 1)]


def _reclassify_internship_entries(
    internships: List[str],
    work_experience: List[str],
) -> tuple[List[str], List[str]]:
    """Reclassify intern-titled roles the parser routed into work_experience.

    Resumes frequently use a single "Experience" heading for both internships
    and full-time roles, so intern-titled work lands in ``work_experience`` with
    an empty ``internships`` list. This reconciles that split:

      - Explicit Internships section already present  → trust it (no change).
      - No work_experience entry carries an intern marker → leave it alone.
      - Single dated role (≤1 date anchor) → treat the whole block as one role
        and move it to internships when it carries an internship marker.
      - Multiple dated roles (≥2 date anchors) → segment into per-role blocks and
        classify EACH independently, so a genuine professional role is not swept
        into internships just because a sibling role is an internship (the
        experienced-candidate misclassification this fixes).

    The multi-role path is heuristic (date-anchored segmentation); resumes whose
    dates are not machine-detectable fall back to the single-block behavior.
    """
    if internships:
        # Trust the original split; don't reclassify.
        return list(internships), list(work_experience)

    if not any(_INTERN_TITLE_RE.search(entry) for entry in work_experience):
        # Pure work experience (no internship words) stays as work experience.
        return [], list(work_experience)

    anchors = [i for i, e in enumerate(work_experience) if _is_date_anchor(e)]
    if len(anchors) <= 1:
        # Single (or undated) role: the whole section is one internship block.
        return list(work_experience), []

    # Multiple dated roles: classify each role block on its own merits.
    internships_out: List[str] = []
    work_out: List[str] = []
    for start, end in _segment_role_blocks(work_experience, anchors):
        block = work_experience[start:end]
        if any(_INTERN_TITLE_RE.search(e) for e in block):
            internships_out.extend(block)
        else:
            work_out.extend(block)
    return internships_out, work_out


def reconcile_internship_work_experience(parsed_resume: Dict) -> tuple[List[str], List[str]]:
    """Single source of truth for the internship vs work-experience split.

    The scoring engine (``compute_internship_score`` / ``compute_work_exp_score``)
    and this engine must agree on which entries count as internships. The resume
    parser routes everything under a single "Experience" header into
    ``work_experience``, so intern-titled roles can land there. Applying the same
    reclassification the experience analysis uses — once, in the orchestrator —
    keeps every downstream consumer consistent and fixes the dual-source-of-truth
    bug where ``S_in`` scored 0 for candidates whose internship sat in
    ``work_experience``.

    Returns the reconciled ``(internships, work_experience)`` lists. Idempotent:
    re-running on already-reconciled lists is a no-op.
    """
    return _reclassify_internship_entries(
        parsed_resume.get("internships", []),
        parsed_resume.get("work_experience", []),
    )


# ─── Constants ───────────────────────────────────────────────────────────────

CANDIDATE_CATEGORIES = ["fresher", "early_career", "experienced", "senior_professional"]

# Experience year thresholds for classification
FRESHER_MAX_MONTHS = 6          # ≤6 months total → fresher
EARLY_CAREER_MAX_MONTHS = 24    # ≤24 months total → early career
EXPERIENCED_MAX_MONTHS = 96     # ≤96 months (8 years) → experienced
# >96 months → senior professional

# Relevance scoring weights (keyword-based, no SBERT)
RELEVANCE_TITLE_WEIGHT = 0.4
RELEVANCE_SKILL_WEIGHT = 0.4
RELEVANCE_DOMAIN_WEIGHT = 0.2


# ─── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass
class InternshipAnalysis:
    """Analysis of a single internship entry."""
    raw_text: str
    duration: DurationResult
    relevance_score: float        # 0.0–1.0
    relevance_signals: List[str]
    company_detected: str         # company name if extractable


@dataclass
class WorkExperienceAnalysis:
    """Analysis of a single work experience entry."""
    raw_text: str
    duration: DurationResult
    relevance_score: float        # 0.0–1.0
    relevance_signals: List[str]
    role_detected: str            # role title if extractable


@dataclass
class ExperienceIntelligence:
    """Complete structured output from the Experience Intelligence Engine."""

    # ── Candidate classification ───────────────────────────────────────────
    candidate_category: str       # fresher/early_career/experienced/senior_professional
    classification_confidence: str  # high/medium/low
    classification_signals: List[str] = field(default_factory=list)

    # ── Internship analysis ────────────────────────────────────────────────
    internship_count: int = 0
    internship_analyses: List[Dict] = field(default_factory=list)
    internship_total_months: float = 0.0
    internship_quality_score: float = 0.0  # 0.0–1.0

    # ── Work experience analysis ───────────────────────────────────────────
    work_experience_count: int = 0
    work_experience_analyses: List[Dict] = field(default_factory=list)
    work_experience_total_months: float = 0.0
    work_experience_quality_score: float = 0.0  # 0.0–1.0

    # ── Combined quality score ─────────────────────────────────────────────
    experience_quality_score: float = 0.0  # 0.0–1.0
    total_experience_months: float = 0.0

    # ── JD alignment ──────────────────────────────────────────────────────
    experience_meets_jd_requirement: bool = False
    jd_required_years: int = 0

    # ── LLM enrichment (sub-phase 1.21) ───────────────────────────────────
    # Optional; default None. Populated only when an LLM provider is passed.
    # INFORMATIONAL ONLY — never feeds back into scoring.
    llm_candidate_type: Optional[str] = None
    llm_relevant_experience_months: Optional[int] = None
    llm_leadership_signals: Optional[List[str]] = None
    llm_impact_metrics: Optional[List[str]] = None
    llm_rationale: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize to a plain dictionary."""
        return asdict(self)


# ─── Relevance Detection (keyword-based) ─────────────────────────────────────


def _extract_keywords_from_jd(
    jd_skills: List[str],
    jd_domain: str = "",
    jd_role: str = "",
) -> Set[str]:
    """Build a set of normalized keywords from JD data for relevance matching."""
    keywords = set()

    # Add normalized skills
    for skill in jd_skills:
        normalized = normalize_skill(normalize_phrase(skill.lower().strip()))
        if normalized and len(normalized) > 1:
            keywords.add(normalized)
        # Also add the raw lowered form for substring matching
        raw = skill.lower().strip()
        if raw and len(raw) > 1:
            keywords.add(raw)

    # Add domain keywords
    if jd_domain and jd_domain != "freshers":
        keywords.add(jd_domain.replace("_", " "))

    # Add role keywords
    if jd_role and jd_role != "not_specified":
        for word in jd_role.lower().split():
            if len(word) > 2:
                keywords.add(word)

    return keywords


def _compute_relevance(
    text: str,
    jd_keywords: Set[str],
) -> tuple[float, list[str]]:
    """Compute keyword-based relevance score for an experience entry.

    Returns (score, signals) where score is 0.0–1.0 and signals list
    the matching keywords found.
    """
    if not text or not jd_keywords:
        return 0.0, []

    text_lower = text.lower()
    matched_keywords: List[str] = []

    for keyword in jd_keywords:
        if keyword in text_lower:
            matched_keywords.append(keyword)

    if not matched_keywords:
        return 0.0, []

    # Score: proportion of JD keywords found in this entry, capped at 1.0
    # We use a log-scaled approach to avoid penalizing entries that don't
    # mention ALL keywords (an entry mentioning 3-4 relevant skills is good)
    raw_ratio = len(matched_keywords) / max(len(jd_keywords), 1)
    # Boost: even 2-3 keyword matches in a single entry is meaningful
    boosted = min(raw_ratio * 3.0, 1.0)
    score = round(boosted, 4)

    signals = [f"matched: {kw}" for kw in matched_keywords[:5]]
    return score, signals


# ─── Internship Analysis ─────────────────────────────────────────────────────


def _detect_company(text: str) -> str:
    """Attempt to extract company name from an internship entry.

    Heuristic: look for patterns like "at <Company>", "Company Name -",
    or "Intern at <Company>".
    """
    patterns = [
        r"(?:at|@)\s+([A-Z][A-Za-z\s&.]+?)(?:\s*[-,|]|\s+as\s+|\s*$)",
        r"^([A-Z][A-Za-z\s&.]+?)\s*[-|]\s*",
        r"(?:intern(?:ship)?|worked)\s+(?:at|with)\s+([A-Z][A-Za-z\s&.]+?)(?:\s*[-,.]|\s*$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            company = match.group(1).strip()
            if len(company) > 2 and len(company.split()) <= 5:
                return company
    return ""


def analyze_internship(
    entry: str,
    jd_keywords: Set[str],
) -> InternshipAnalysis:
    """Analyze a single internship entry."""
    duration = extract_duration_months(entry)
    relevance_score, relevance_signals = _compute_relevance(entry, jd_keywords)
    company = _detect_company(entry)

    return InternshipAnalysis(
        raw_text=entry,
        duration=duration,
        relevance_score=relevance_score,
        relevance_signals=relevance_signals,
        company_detected=company,
    )


def score_internships(
    internships: List[str],
    jd_keywords: Set[str],
) -> tuple[float, list[InternshipAnalysis]]:
    """Score all internship entries combined.

    Score components:
      - Count (40%): min(count / 2, 1.0) — having 2+ internships is full marks
      - Relevance (30%): max relevance across entries
      - Duration (30%): duration factor of the longest internship

    Returns (quality_score, analyses).
    """
    if not internships:
        return 0.0, []

    analyses = [analyze_internship(entry, jd_keywords) for entry in internships]

    # Count component
    count_score = min(len(internships) / 2.0, 1.0) * 0.4

    # Relevance component
    max_relevance = max(a.relevance_score for a in analyses) if analyses else 0.0
    relevance_score = max_relevance * 0.3

    # Duration component
    durations = [a.duration.months for a in analyses if a.duration.months is not None]
    best_duration = max(durations, default=None)
    duration_score = get_duration_factor(best_duration) * 0.3

    quality = min(round(count_score + relevance_score + duration_score, 4), 1.0)
    return quality, analyses


# ─── Work Experience Analysis ─────────────────────────────────────────────────


def _detect_role(text: str) -> str:
    """Attempt to extract role title from a work experience entry.

    Phase 3 fix B: broadened to cover:
      - Internship/trainee titles ("Data & Insights Intern - Skypoint")
      - Role names containing '&' / '+' / '-' (Data & Insights, R&D, ...)
      - More role suffixes (Intern, Trainee, Associate, Coordinator,
        Researcher, Scientist, Director)
    """
    # Allow & and + and . in the role name so multi-word titles like
    # "Data & Insights Intern" or "C++ Engineer" or "R&D Lead" match.
    role_word = r"[A-Za-z][A-Za-z\s/&+\.]*"
    role_suffixes = (
        r"Engineer|Developer|Analyst|Designer|Manager|Lead|Consultant|"
        r"Architect|Specialist|Scientist|Researcher|Director|Officer|"
        r"Intern|Trainee|Apprentice|Associate|Coordinator|Administrator"
    )
    patterns = [
        rf"^([A-Z]{role_word}?(?:{role_suffixes}))\b",
        rf"(?:as\s+(?:a\s+|an\s+)?|role:\s*)({role_word}?(?:{role_suffixes}))\b",
        rf"^([A-Z]{role_word}?)\s*[-|@]",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            role = re.sub(r"\s+", " ", match.group(1)).strip(" -:;,.")
            if len(role) > 3 and len(role.split()) <= 6:
                return role
    return ""


def analyze_work_experience(
    entry: str,
    jd_keywords: Set[str],
) -> WorkExperienceAnalysis:
    """Analyze a single work experience entry."""
    duration = extract_duration_months(entry)
    relevance_score, relevance_signals = _compute_relevance(entry, jd_keywords)
    role = _detect_role(entry)

    return WorkExperienceAnalysis(
        raw_text=entry,
        duration=duration,
        relevance_score=relevance_score,
        relevance_signals=relevance_signals,
        role_detected=role,
    )


def score_work_experience(
    work_experience: List[str],
    jd_keywords: Set[str],
    required_years: int = 0,
) -> tuple[float, list[WorkExperienceAnalysis]]:
    """Score all work experience entries combined.

    When required_years > 0:
      Score = min(total_detected_years / required_years, 1.0)
    When required_years == 0:
      Score = 1.0 if any work experience exists, else 0.0
      (JD doesn't require experience, so any is a bonus)

    Returns (quality_score, analyses).
    """
    if not work_experience:
        return 0.0, []

    analyses = [analyze_work_experience(entry, jd_keywords) for entry in work_experience]

    if required_years <= 0:
        # JD doesn't require experience — having any is positive
        return 1.0 if work_experience else 0.0, analyses

    # Sum detected durations
    total_months = 0.0
    for analysis in analyses:
        if analysis.duration.months is not None:
            total_months += analysis.duration.months

    # Also try direct year extraction from entries (original logic)
    if total_months == 0:
        for entry in work_experience:
            entry_lower = entry.lower()
            y = re.search(r"(\d+\.?\d*)\s*years?", entry_lower)
            if y:
                total_months += float(y.group(1)) * 12
                continue
            m = re.search(r"(\d+\.?\d*)\s*months?", entry_lower)
            if m:
                total_months += float(m.group(1))

    total_years = total_months / 12.0
    if total_years <= 0:
        return 0.0, analyses

    score = min(round(total_years / required_years, 4), 1.0)
    return score, analyses


# ─── Candidate Classification ────────────────────────────────────────────────


def classify_candidate(
    internship_months: float,
    work_experience_months: float,
    internship_count: int,
    work_experience_count: int,
) -> tuple[str, str, list[str]]:
    """Classify candidate as fresher/early_career/experienced/senior_professional.

    Args:
        internship_months: Total internship duration in months.
        work_experience_months: Total work experience in months.
        internship_count: Number of internship entries.
        work_experience_count: Number of work experience entries.

    Returns:
        (category, confidence, signals)
    """
    total_months = internship_months + work_experience_months
    signals: List[str] = []

    signals.append(f"total experience: {total_months:.1f} months")
    signals.append(f"internships: {internship_count} ({internship_months:.1f} months)")
    signals.append(f"work experience: {work_experience_count} ({work_experience_months:.1f} months)")

    # Classification logic
    if work_experience_count == 0 and internship_count == 0:
        return "fresher", "high", signals + ["no internships or work experience"]

    if work_experience_months == 0 and total_months <= FRESHER_MAX_MONTHS:
        confidence = "high" if internship_count <= 1 else "medium"
        return "fresher", confidence, signals

    if total_months <= FRESHER_MAX_MONTHS:
        return "fresher", "medium", signals

    if total_months <= EARLY_CAREER_MAX_MONTHS:
        confidence = "high" if work_experience_count > 0 else "medium"
        return "early_career", confidence, signals

    if total_months <= EXPERIENCED_MAX_MONTHS:
        return "experienced", "high", signals

    return "senior_professional", "high", signals


# ─── Main Entry Point ────────────────────────────────────────────────────────


def analyze_experience(
    parsed_resume: Dict,
    jd_data: Optional[Dict] = None,
    llm_provider: Optional[object] = None,
) -> ExperienceIntelligence:
    """Analyze candidate experience from parsed resume against JD requirements.

    This is the primary entry point for Phase 3 experience analysis.

    Args:
        parsed_resume: Output from resume_parser.parse_resume().
            Expected keys: "internships", "work_experience", "skills"
        jd_data: Output from jd_parser.parse_jd() or jd_intelligence.analyze_jd().
            Expected keys: "required_skills", "preferred_skills",
            "domain_detected"/"primary_domain", "role_title",
            "experience_years"
        llm_provider: Optional LLMProvider (sub-phase 1.22). When provided,
            one cached LLM call enriches the result with `llm_candidate_type`,
            `llm_relevant_experience_months`, `llm_leadership_signals`,
            `llm_impact_metrics`, and `llm_rationale`. When None or backend=
            none, llm_* fields stay None and behavior is byte-identical.

    Returns:
        ExperienceIntelligence with complete analysis.
    """
    # Handle empty input
    if not parsed_resume:
        return ExperienceIntelligence(
            candidate_category="fresher",
            classification_confidence="low",
            classification_signals=["no resume data provided"],
        )

    internships, work_experience = _reclassify_internship_entries(
        parsed_resume.get("internships", []),
        parsed_resume.get("work_experience", []),
    )

    # Build JD keyword set for relevance matching
    jd_keywords: Set[str] = set()
    jd_required_years = 0
    jd_domain = ""
    jd_role = ""

    if jd_data:
        all_jd_skills = (
            jd_data.get("required_skills", [])
            + jd_data.get("preferred_skills", [])
            + jd_data.get("optional_skills", [])
        )
        jd_domain = jd_data.get("primary_domain", jd_data.get("domain_detected", ""))
        jd_role = jd_data.get("role_title", "")
        jd_required_years = jd_data.get("experience_years", 0)
        jd_keywords = _extract_keywords_from_jd(all_jd_skills, jd_domain, jd_role)

    # Analyze internships
    internship_quality, internship_analyses = score_internships(internships, jd_keywords)
    internship_duration = aggregate_durations(internships)

    # Analyze work experience
    work_exp_quality, work_exp_analyses = score_work_experience(
        work_experience, jd_keywords, jd_required_years
    )
    work_exp_duration = aggregate_durations(work_experience)

    # Classify candidate
    category, confidence, signals = classify_candidate(
        internship_months=internship_duration.total_months,
        work_experience_months=work_exp_duration.total_months,
        internship_count=len(internships),
        work_experience_count=len(work_experience),
    )

    # Combined quality score
    total_months = internship_duration.total_months + work_exp_duration.total_months
    if internships and work_experience:
        # Both present: weight work experience more heavily
        combined_quality = 0.4 * internship_quality + 0.6 * work_exp_quality
    elif work_experience:
        combined_quality = work_exp_quality
    elif internships:
        combined_quality = internship_quality
    else:
        combined_quality = 0.0

    # Check if experience meets JD requirement
    meets_requirement = True
    if jd_required_years > 0:
        total_years = total_months / 12.0
        meets_requirement = total_years >= jd_required_years

    # ── Sub-phase 1.22 — LLM enrichment ──────────────────────────────────
    # One cached LLM call per resume × JD. Informational only.
    llm_fields = {}
    if llm_provider is not None:
        llm_fields = _llm_enrich_experience(
            internships=internships,
            work_experience=work_experience,
            jd_data=jd_data,
            baseline_category=category,
            baseline_total_months=total_months,
            llm_provider=llm_provider,
        )

    return ExperienceIntelligence(
        # Classification
        candidate_category=category,
        classification_confidence=confidence,
        classification_signals=signals,

        # Internships
        internship_count=len(internships),
        internship_analyses=[
            {
                "raw_text": a.raw_text[:200],  # Truncate for output
                "duration_months": a.duration.months,
                "duration_classification": a.duration.classification,
                "relevance_score": a.relevance_score,
                "relevance_signals": a.relevance_signals,
                "company_detected": a.company_detected,
            }
            for a in internship_analyses
        ],
        internship_total_months=internship_duration.total_months,
        internship_quality_score=round(internship_quality, 4),

        # Work experience
        work_experience_count=len(work_experience),
        work_experience_analyses=[
            {
                "raw_text": a.raw_text[:200],
                "duration_months": a.duration.months,
                "duration_classification": a.duration.classification,
                "relevance_score": a.relevance_score,
                "relevance_signals": a.relevance_signals,
                "role_detected": a.role_detected,
            }
            for a in work_exp_analyses
        ],
        work_experience_total_months=work_exp_duration.total_months,
        work_experience_quality_score=round(work_exp_quality, 4),

        # Combined
        experience_quality_score=round(combined_quality, 4),
        total_experience_months=round(total_months, 2),

        # JD alignment
        experience_meets_jd_requirement=meets_requirement,
        jd_required_years=jd_required_years,

        # LLM enrichment (informational only)
        llm_candidate_type=llm_fields.get("candidate_type"),
        llm_relevant_experience_months=llm_fields.get("relevant_experience_months"),
        llm_leadership_signals=llm_fields.get("leadership_signals"),
        llm_impact_metrics=llm_fields.get("impact_metrics"),
        llm_rationale=llm_fields.get("rationale"),
    )


# ─── LLM enrichment helper (sub-phase 1.22) ──────────────────────────────────


def _llm_enrich_experience(
    *,
    internships: List[str],
    work_experience: List[str],
    jd_data: Optional[Dict],
    baseline_category: str,
    baseline_total_months: float,
    llm_provider,
) -> Dict:
    """One LLM call summarising candidate experience against the JD.

    Returns a dict with keys matching the llm_* suffixes on
    ExperienceIntelligence. Returns ``{}`` on LLM failure so the engine
    still emits a structurally complete result.
    """
    from app.utils.llm_schemas import ExperienceStructure

    role = (jd_data or {}).get("role_title", "") or ""
    domain = (
        (jd_data or {}).get("primary_domain")
        or (jd_data or {}).get("domain_detected")
        or ""
    )
    req_years = (jd_data or {}).get("experience_years", 0)
    req_skills = ", ".join((jd_data or {}).get("required_skills", [])[:20])

    jd_brief = (
        f"Role: {role}\nDomain: {domain}\nRequires: {req_years} years\n"
        f"Required skills: {req_skills}"
    )
    body = []
    if internships:
        body.append("INTERNSHIPS:")
        body.extend(f"- {e[:400]}" for e in internships[:12])
    if work_experience:
        body.append("\nWORK EXPERIENCE:")
        body.extend(f"- {e[:400]}" for e in work_experience[:12])
    if not body:
        body.append("(no experience entries)")
    body_text = "\n".join(body)

    system_prompt = (
        "You judge candidate experience against a target job description.\n\n"
        "candidate_type: one of fresher/early_career/experienced/senior_professional.\n"
        "relevant_experience_months: months of experience GENUINELY RELEVANT to "
        "the JD (not just total tenure).\n"
        "leadership_signals: phrases from the resume showing leadership, mentorship, "
        "or ownership.\n"
        "impact_metrics: quantified outcomes (e.g. '40% latency reduction', "
        "'served 10M users').\n"
        "rationale: one paragraph explaining your classification + relevance."
    )
    user_prompt = (
        f"JOB DESCRIPTION:\n{jd_brief}\n\n"
        f"BASELINE PARSE (deterministic):\n"
        f"- candidate_category: {baseline_category}\n"
        f"- total_experience_months: {baseline_total_months}\n\n"
        f"CANDIDATE EXPERIENCE:\n{body_text}"
    )

    response = llm_provider.complete_json(
        system=system_prompt, user=user_prompt, schema=ExperienceStructure,
    )
    if response is None:
        return {}
    return {
        "candidate_type": response.candidate_type,
        "relevant_experience_months": int(response.relevant_experience_months),
        "leadership_signals": list(response.leadership_signals),
        "impact_metrics": list(response.impact_metrics),
        "rationale": response.rationale,
    }
