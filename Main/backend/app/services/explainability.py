"""Sub-phase 1.24 — Explainability data layer.

Aggregates ``llm_*`` fields from the four engines into a single
``LLMExplanation`` payload that the UI (Phase 4) renders directly.

This layer does **not** affect scores — it's strictly read-side. It can
optionally make ONE final LLM call to generate a polished overall summary
and next-steps list, but the engine-level rationales / strengths / gaps
already populated by sub-phases 1.B / 1.D are surfaced as-is.

Inputs:
  * `jd_intel`: ``JDIntelligence`` (from ``analyze_jd``)
  * `exp_intel`: ``ExperienceIntelligence`` (from ``analyze_experience``)
  * `proj_intel`: ``ProjectIntelligence`` (from ``analyze_projects``)
  * `match_result`: dict from ``match_skills`` (with optional `llm_validation`)
  * `llm_provider`: optional ``LLMProvider`` for the polishing call.

The polishing call is gated like every other LLM call — when the provider
returns None (cost-cap / timeout / unreachable), ``overall_summary`` and
``next_steps`` simply stay None and the rest of the payload is unaffected.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LLMExplanation:
    """Single payload powering the Phase 4 explainability views."""

    # ── Polished top-level (optional LLM polishing call) ───────────────────
    overall_summary: Optional[str] = None
    next_steps: Optional[List[str]] = None

    # ── Aggregated strengths / gaps (from project enrichment + polish) ─────
    top_strengths: List[str] = field(default_factory=list)
    top_gaps: List[str] = field(default_factory=list)

    # ── JD context ─────────────────────────────────────────────────────────
    jd_role: Optional[str] = None
    jd_role_confidence: Optional[str] = None         # high/medium/low
    jd_responsibilities: Optional[List[str]] = None
    jd_excluded_noise: Optional[List[str]] = None
    jd_seniority_llm: Optional[str] = None
    jd_seniority_baseline: Optional[str] = None
    jd_llm_confidence: Optional[float] = None

    # ── Experience context ─────────────────────────────────────────────────
    candidate_type_baseline: Optional[str] = None
    candidate_type_llm: Optional[str] = None
    relevant_experience_months: Optional[int] = None
    total_experience_months: Optional[float] = None
    experience_rationale: Optional[str] = None
    leadership_signals: List[str] = field(default_factory=list)
    impact_metrics: List[str] = field(default_factory=list)

    # ── Project context (top N by final_score) ─────────────────────────────
    top_projects: List[Dict[str, Any]] = field(default_factory=list)

    # ── Match validation transparency (sub-phase 1.10 → here) ──────────────
    matches_validated_kept: int = 0
    matches_validated_rejected: int = 0
    validation_skipped_reason: Optional[str] = None
    rejected_pairs: List[Dict[str, Any]] = field(default_factory=list)
    kept_pairs: List[Dict[str, Any]] = field(default_factory=list)

    # ── Metadata ──────────────────────────────────────────────────────────
    embedding_backend: Optional[str] = None
    llm_polishing_used: bool = False
    missing_skills: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)


def assemble_explanation(
    *,
    jd_intel=None,
    exp_intel=None,
    proj_intel=None,
    match_result: Optional[Dict] = None,
    llm_provider: Optional[object] = None,
    top_n_projects: int = 3,
    missing_skills: Optional[List[str]] = None,
) -> LLMExplanation:
    """Build the explainability payload by aggregating engine outputs.

    All arguments are optional — missing engines simply leave their slots empty.
    The function NEVER mutates the inputs.

    When ``llm_provider`` is provided, runs ONE final cached call against the
    ``Explanation`` schema to generate ``overall_summary`` and ``next_steps``.
    Falls back to engine-level top_strengths / top_gaps when the call fails.
    """
    expl = LLMExplanation()
    expl.missing_skills = missing_skills or []

    # ── JD context ────────────────────────────────────────────────────────
    if jd_intel is not None:
        expl.jd_role = getattr(jd_intel, "role_title", None)
        expl.jd_role_confidence = getattr(jd_intel, "role_confidence", None)
        expl.jd_responsibilities = getattr(jd_intel, "llm_responsibilities", None)
        expl.jd_excluded_noise = getattr(jd_intel, "llm_excluded_noise", None)
        expl.jd_seniority_baseline = getattr(jd_intel, "seniority_level", None)
        expl.jd_seniority_llm = getattr(jd_intel, "llm_seniority", None)
        expl.jd_llm_confidence = getattr(jd_intel, "llm_confidence", None)

    # ── Experience context ────────────────────────────────────────────────
    if exp_intel is not None:
        expl.candidate_type_baseline = getattr(exp_intel, "candidate_category", None)
        expl.candidate_type_llm = getattr(exp_intel, "llm_candidate_type", None)
        expl.relevant_experience_months = getattr(
            exp_intel, "llm_relevant_experience_months", None,
        )
        expl.total_experience_months = getattr(exp_intel, "total_experience_months", None)
        expl.experience_rationale = getattr(exp_intel, "llm_rationale", None)
        expl.leadership_signals = list(
            getattr(exp_intel, "llm_leadership_signals", None) or []
        )
        expl.impact_metrics = list(
            getattr(exp_intel, "llm_impact_metrics", None) or []
        )

    # ── Project context ───────────────────────────────────────────────────
    if proj_intel is not None:
        expl.embedding_backend = getattr(proj_intel, "embedding_backend", None)
        # Top N projects with their llm_rationale + scores.
        ranked = list(getattr(proj_intel, "ranked_projects", []) or [])
        for p in ranked[:top_n_projects]:
            expl.top_projects.append({
                "rank": p.get("rank"),
                "title": p.get("title"),
                "final_score": p.get("final_score"),
                "similarity_score": p.get("similarity_score"),
                "llm_relevance": p.get("llm_relevance"),
                "llm_rationale": p.get("llm_rationale"),
                "matched_jd_skills": p.get("matched_jd_skills", []),
            })
        # Strengths / gaps default to project-level aggregates.
        expl.top_strengths = list(
            getattr(proj_intel, "llm_top_strengths", None) or []
        )
        expl.top_gaps = list(
            getattr(proj_intel, "llm_top_gaps", None) or []
        )

    # ── Match validation transparency ─────────────────────────────────────
    if match_result is not None:
        validation = match_result.get("llm_validation")
        if validation:
            expl.matches_validated_kept = len(validation.get("kept", []))
            expl.matches_validated_rejected = len(validation.get("rejected", []))
            expl.validation_skipped_reason = validation.get("skipped_reason")
            expl.kept_pairs = list(validation.get("kept", []))
            expl.rejected_pairs = list(validation.get("rejected", []))

    # ── Optional polishing LLM call ───────────────────────────────────────
    if llm_provider is not None:
        polished = _llm_polish_explanation(expl, llm_provider)
        if polished is not None:
            expl.overall_summary = polished.get("overall_summary")
            expl.next_steps = polished.get("next_steps")
            # Polish call may suggest different top strengths / gaps; prefer
            # them when present (they consolidate across all engines).
            if polished.get("top_strengths"):
                expl.top_strengths = polished["top_strengths"]
            if polished.get("top_gaps"):
                expl.top_gaps = polished["top_gaps"]
            expl.llm_polishing_used = True

    return expl


def _llm_polish_explanation(
    expl: LLMExplanation, llm_provider,
) -> Optional[Dict]:
    """One LLM call to produce a polished overall_summary + next_steps.

    Returns a dict matching ``Explanation`` schema fields, or ``None`` on
    LLM failure.
    """
    from app.utils.llm_schemas import Explanation

    # Build a compact briefing from the already-aggregated fields.
    brief_lines = []
    if expl.jd_role:
        brief_lines.append(f"JD Role: {expl.jd_role}")
    if expl.candidate_type_baseline:
        brief_lines.append(
            f"Candidate category (baseline): {expl.candidate_type_baseline}"
        )
    if expl.candidate_type_llm:
        brief_lines.append(
            f"Candidate category (LLM): {expl.candidate_type_llm}"
        )
    if expl.experience_rationale:
        brief_lines.append(f"Experience rationale: {expl.experience_rationale}")
    if expl.top_strengths:
        brief_lines.append("Project-derived strengths: " + "; ".join(expl.top_strengths))
    if expl.top_gaps:
        brief_lines.append("Project-derived gaps: " + "; ".join(expl.top_gaps))
    if expl.missing_skills:
        brief_lines.append("SBERT-detected missing skills: " + ", ".join(expl.missing_skills))
    if expl.matches_validated_rejected:
        brief_lines.append(
            f"LLM rejected {expl.matches_validated_rejected} borderline matches; "
            f"kept {expl.matches_validated_kept}"
        )
    if expl.top_projects:
        brief_lines.append("Top projects:")
        for p in expl.top_projects:
            rat = (p.get("llm_rationale") or "")[:200]
            brief_lines.append(f"  - {p.get('title', '')}: {rat}")

    system_prompt = (
        "You write a candidate ↔ JD fit explanation for an analyst dashboard.\n\n"
        "overall_summary: 2-3 sentences on fit (acknowledge both strengths and "
        "gaps; avoid hyperbole).\n"
        "top_strengths: at most 5 bullets, consolidated across all evidence below.\n"
        "top_gaps: at most 5 bullets. Instead of simply listing raw SBERT-detected missing skills, "
        "explain them in recruiter-friendly sentences. For example, rather than listing 'FastAPI, PostgreSQL, AWS', "
        "write: 'The candidate demonstrates strong backend development fundamentals but lacks direct evidence of production experience with FastAPI and PostgreSQL. Cloud deployment experience using AWS is also not clearly represented, creating a gap against the target role requirements.'\n"
        "next_steps: 3-5 concrete, actionable items the candidate could do "
        "next (skills to learn, projects to build, certifications).\n"
        "Stay grounded in the evidence — do not invent skills or experience."
    )
    user_prompt = "EVIDENCE:\n" + "\n".join(brief_lines)

    response = llm_provider.complete_json(
        system=system_prompt, user=user_prompt, schema=Explanation,
    )
    if response is None:
        return None
    return {
        "overall_summary": response.overall_summary,
        "top_strengths": list(response.top_strengths),
        "top_gaps": list(response.top_gaps),
        "next_steps": list(response.next_steps),
    }
