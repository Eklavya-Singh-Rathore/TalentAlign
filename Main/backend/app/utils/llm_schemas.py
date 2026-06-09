"""Pydantic v2 response schemas for every LLM endpoint (sub-phase 1.2).

Every LLM call validates its response against one of these schemas. The
JSON-Schema form of each is injected into the system prompt so the model
knows the exact shape to return. Validation failures trigger one reformat
retry inside ``LLMProvider.complete_json``; if the retry also fails the
call returns ``None`` and the pipeline degrades gracefully.

Schemas live in a single file so schema drift is easy to diff. Field names
mirror the new ``llm_*`` fields planned for the engine dataclasses, so
populating an engine's enrichment fields is `model.field_name` directly.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, ConfigDict


class _Strict(BaseModel):
    """Base for strict JSON validation — extra keys silently ignored."""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


# ─── 1. JD structuring (sub-phase 1.16) ──────────────────────────────────────


class JDStructure(_Strict):
    """LLM's structured understanding of a job description.

    Populates the new ``llm_*`` fields on ``JDIntelligence``.
    """
    role_summary: str = Field(description="One-line role title in title case, or 'not_specified'.")
    seniority: str = Field(description="One of: intern/junior/mid/senior/lead/executive.")
    responsibilities: List[str] = Field(
        default_factory=list,
        description="Concise responsibility bullets (≤8). Extracted, not invented.",
    )
    required_skills_clean: List[str] = Field(
        default_factory=list,
        description="Required skills after stripping prose noise. Informational only — never fed to the matcher.",
    )
    preferred_skills_clean: List[str] = Field(default_factory=list)
    excluded_noise: List[str] = Field(
        default_factory=list,
        description="Phrases pulled from the JD that are NOT real skills (e.g. 'internal partners', 'best practices').",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Self-reported confidence 0.0–1.0.")


# ─── 2. Experience structuring (sub-phase 1.22) ──────────────────────────────


class ExperienceStructure(_Strict):
    """LLM's structured understanding of resume experience vs JD requirements."""
    candidate_type: str = Field(description="One of: fresher/early_career/experienced/senior_professional.")
    relevant_experience_months: int = Field(
        ge=0,
        description="Months of experience genuinely relevant to the JD (not just total tenure).",
    )
    leadership_signals: List[str] = Field(default_factory=list)
    impact_metrics: List[str] = Field(
        default_factory=list,
        description="Quantified outcomes extracted from the resume (e.g. '40% latency reduction').",
    )
    rationale: str = Field(description="One paragraph explaining the classification + relevance.")


# ─── 3. Project structuring (sub-phase 1.19) ─────────────────────────────────


class ProjectRelevance(_Strict):
    """LLM judgment for one project against the JD."""
    project_title: str
    llm_relevance: float = Field(ge=0.0, le=1.0)
    llm_skills_inferred: List[str] = Field(
        default_factory=list,
        description="Skills inferred from the project description. Informational only — never fed to the matcher.",
    )
    rationale: str


class ProjectStructure(_Strict):
    """Batched LLM response for all projects in one analysis."""
    projects: List[ProjectRelevance]
    top_strengths: List[str] = Field(default_factory=list)
    top_gaps: List[str] = Field(default_factory=list)


# ─── 4. Match validation (sub-phase 1.9) ─────────────────────────────────────


class MatchValidationItem(_Strict):
    """One verdict on an ambiguous resume↔JD skill pair."""
    pair_id: str = Field(description="Caller-provided opaque ID echoed back so results align.")
    is_valid_match: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(description="One sentence justification, ≤140 chars.")


class MatchValidation(_Strict):
    """Batched validation response — one entry per submitted pair."""
    items: List[MatchValidationItem]


# ─── 5. Explanation (sub-phase 1.24) ─────────────────────────────────────────


class Explanation(_Strict):
    """Human-readable summary for the UI explainability panel."""
    overall_summary: str = Field(description="2–3 sentences on candidate ↔ JD fit.")
    top_strengths: List[str] = Field(default_factory=list)
    top_gaps: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


# ─── Convenience: schema name → class ────────────────────────────────────────


SCHEMA_REGISTRY = {
    "JDStructure": JDStructure,
    "ExperienceStructure": ExperienceStructure,
    "ProjectStructure": ProjectStructure,
    "MatchValidation": MatchValidation,
    "Explanation": Explanation,
}
