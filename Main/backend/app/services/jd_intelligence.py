"""JD Intelligence Engine — Phase 2 orchestrator.

Coordinates all JD analysis features into a single structured output.
This is the top-level entry point for Phase 2 JD processing.

Pipeline:
    Raw JD → Noise Filter → parse_jd → Seniority Detection →
    Requirement Prioritization → Enhanced Role/Domain → Structured Output

The existing parse_jd() function is called internally and its output
is enriched with the new Phase 2 intelligence features. parse_jd()
itself remains unchanged for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

from app.services.jd_parser import (
    detect_seniority,
    detect_domain_multi,
    extract_role_title_enhanced,
    parse_jd,
    prioritize_requirements,
    DomainScores,
    PrioritizedRequirement,
    RoleResult,
    SeniorityResult,
)
from app.utils.jd_noise_filter import filter_jd_noise, FilteredJD


@dataclass
class JDIntelligence:
    """Complete structured output from the JD Intelligence Engine.

    This is the primary output type for Phase 2 JD analysis. It wraps
    the parse_jd() output and adds seniority, prioritization, multi-domain
    scoring, role confidence, and noise filtering metadata.
    """

    # ── Cleaned input ──────────────────────────────────────────────────────
    clean_text: str
    noise_sections_removed: List[str] = field(default_factory=list)
    noise_ratio: float = 0.0

    # ── Role & domain ──────────────────────────────────────────────────────
    role_title: str = "not_specified"
    role_confidence: str = "low"
    role_extraction_method: str = "fallback"
    primary_domain: str = "freshers"
    secondary_domain: Optional[str] = None
    domain_scores: Dict[str, float] = field(default_factory=dict)

    # ── Seniority ──────────────────────────────────────────────────────────
    seniority_level: str = "mid"
    seniority_confidence: str = "low"
    seniority_signals: List[str] = field(default_factory=list)

    # ── Skills ─────────────────────────────────────────────────────────────
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    optional_skills: List[str] = field(default_factory=list)

    # ── Prioritized requirements ───────────────────────────────────────────
    prioritized_requirements: List[Dict] = field(default_factory=list)

    # ── Education & experience ─────────────────────────────────────────────
    experience_years: int = 0
    education_level: str = "not_specified"

    # ── Rules ──────────────────────────────────────────────────────────────
    rules: Dict[str, bool] = field(default_factory=dict)

    # ── LLM enrichment (sub-phase 1.15) ────────────────────────────────────
    # All Optional and default None so behavior is byte-identical to the
    # pre-LLM baseline when no `llm_provider` is passed to `analyze_jd`.
    # These fields are INFORMATIONAL ONLY and never feed back into the
    # matcher / scoring engine (enforced by the hallucination guard test).
    llm_role_summary: Optional[str] = None
    llm_responsibilities: Optional[List[str]] = None
    llm_seniority: Optional[str] = None
    llm_confidence: Optional[float] = None
    llm_excluded_noise: Optional[List[str]] = None

    # ── Debug/metadata ─────────────────────────────────────────────────────
    _rejected_skill_candidates: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize to a plain dictionary."""
        return asdict(self)


def analyze_jd(text: str, llm_provider: Optional[object] = None) -> JDIntelligence:
    """Analyze a job description through the full JD Intelligence Engine.

    This is the primary entry point for Phase 2 JD processing.

    Pipeline:
    1. Filter noise (boilerplate removal)
    2. Parse JD (Phase 1 parse_jd for skills, experience, education)
    3. Enhanced role extraction (with confidence)
    4. Enhanced domain detection (multi-domain scoring)
    5. Seniority detection
    6. Requirement prioritization
    7. (Sub-phase 1.16) Optional LLM enrichment — populates llm_* fields.
    8. Assemble structured output

    Args:
        text: Raw job description text.
        llm_provider: Optional LLMProvider. When provided, one cached LLM
            call enriches the result with `llm_role_summary`,
            `llm_responsibilities`, `llm_seniority`, `llm_confidence`, and
            `llm_excluded_noise`. When None or backend='none', the llm_*
            fields stay None and behavior is byte-identical to baseline.

    Returns:
        JDIntelligence object with complete analysis.
    """
    # Handle empty/invalid input
    if not isinstance(text, str) or not text.strip():
        return JDIntelligence(clean_text="")

    # Step 1: Noise filtering
    filtered: FilteredJD = filter_jd_noise(text)
    clean_text = filtered.clean_text

    # Step 2: Parse JD (Phase 1 baseline — runs on clean text)
    parsed = parse_jd(clean_text)

    # Step 3: Enhanced role extraction (on clean text)
    role_result: RoleResult = extract_role_title_enhanced(clean_text)

    # Step 4: Enhanced domain detection (on clean text)
    domain_result: DomainScores = detect_domain_multi(clean_text)

    # Step 5: Seniority detection
    seniority_result: SeniorityResult = detect_seniority(
        text=clean_text,
        experience_years=parsed["experience_years"],
        role_title=role_result.title,
    )

    # Step 6: Requirement prioritization
    skills_data = {
        "required_skills": parsed["required_skills"],
        "preferred_skills": parsed["preferred_skills"],
        "optional_skills": parsed.get("optional_skills", []),
    }
    prioritized: List[PrioritizedRequirement] = prioritize_requirements(
        skills_data=skills_data,
        seniority_level=seniority_result.level,
    )

    # Step 7: LLM enrichment (sub-phase 1.16). One cached call per JD;
    # informational fields only — never feeds the matcher.
    llm_fields = _llm_enrich_jd(clean_text, llm_provider) if llm_provider is not None else {}

    # Step 8: Assemble structured output
    return JDIntelligence(
        # Cleaned input
        clean_text=clean_text,
        noise_sections_removed=filtered.removed_sections,
        noise_ratio=filtered.noise_ratio,

        # Role & domain
        role_title=role_result.title,
        role_confidence=role_result.confidence,
        role_extraction_method=role_result.extraction_method,
        primary_domain=domain_result.primary,
        secondary_domain=domain_result.secondary,
        domain_scores=domain_result.scores,

        # Seniority
        seniority_level=seniority_result.level,
        seniority_confidence=seniority_result.confidence,
        seniority_signals=seniority_result.signals,

        # Skills
        required_skills=parsed["required_skills"],
        preferred_skills=parsed["preferred_skills"],
        optional_skills=parsed.get("optional_skills", []),

        # Prioritized requirements
        prioritized_requirements=[
            {
                "skill": req.skill,
                "bucket": req.bucket,
                "priority": req.priority,
                "priority_reason": req.priority_reason,
                "position": req.position,
            }
            for req in prioritized
        ],

        # Education & experience
        experience_years=parsed["experience_years"],
        education_level=parsed["education_level"],

        # Rules
        rules=parsed.get("rules", {}),

        # LLM enrichment (informational only)
        llm_role_summary=llm_fields.get("role_summary"),
        llm_responsibilities=llm_fields.get("responsibilities"),
        llm_seniority=llm_fields.get("seniority"),
        llm_confidence=llm_fields.get("confidence"),
        llm_excluded_noise=llm_fields.get("excluded_noise"),

        # Debug metadata
        _rejected_skill_candidates=parsed.get("_rejected_skill_candidates", []),
    )


# ─── LLM enrichment helper (sub-phase 1.16) ──────────────────────────────────


def _llm_enrich_jd(clean_text: str, llm_provider) -> Dict:
    """Run one LLM call to enrich JD analysis with structured intelligence.

    Returns a dict with keys matching the llm_* field suffixes on
    JDIntelligence. Returns an empty dict on any LLM failure (provider
    `none`, cost cap, timeout, schema failure) so the engine still produces
    a structurally complete result.
    """
    from app.utils.llm_schemas import JDStructure

    system_prompt = (
        "You are a JD analyst extracting structured intelligence from a job "
        "description.\n\n"
        "For required_skills_clean and preferred_skills_clean: list ONLY real "
        "technical skills / tools / frameworks mentioned. Do NOT include "
        "company-domain phrases like 'internal partners', 'financial crimes', "
        "'best practices', 'strong communication' — those go in excluded_noise.\n\n"
        "For responsibilities: extract at most 8 concise responsibility bullets.\n"
        "For seniority: one of intern/junior/mid/senior/lead/executive.\n"
        "For role_summary: the canonical job title (e.g. 'Senior Backend Engineer'), "
        "or 'not_specified' if no clear title.\n\n"
        "Set confidence to your self-assessed reliability (0.0-1.0)."
    )
    user_prompt = f"Job description text:\n\n{clean_text[:6000]}"

    response = llm_provider.complete_json(
        system=system_prompt, user=user_prompt, schema=JDStructure,
    )
    if response is None:
        return {}
    return {
        "role_summary": response.role_summary,
        "responsibilities": list(response.responsibilities),
        "seniority": response.seniority,
        "confidence": float(response.confidence),
        "excluded_noise": list(response.excluded_noise),
    }
