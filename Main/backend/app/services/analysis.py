"""Unified end-to-end analysis orchestrator.

Runs the complete TalentAlign pipeline for one resume × JD pair and returns a
single structured payload containing every output the system supports — the
contract the Phase 4 UI will consume and the manual-testing report renders.

Pipeline:
    parse_resume → analyze_jd (+LLM) → skill matching (+optional LLM gate)
    → 6-component MW-ESE scoring → weighted composite (placement score)
    → gap-impact estimation → improvement simulation → recommendations
    → experience/project intelligence (+LLM) → explainability (+LLM)

Pass ``llm_provider`` to enable LLM validation + enrichment; omit it for a
fully deterministic run (byte-identical to the no-LLM baseline).
"""

from __future__ import annotations

from typing import Dict, Optional

from app.services.experience_intelligence import (
    analyze_experience,
    reconcile_internship_work_experience,
)
from app.services.explainability import assemble_explanation
from app.services.improvement_engine import (
    estimate_gap_impacts_pipeline,
    simulate_improvements_pipeline,
)
from app.services.jd_intelligence import analyze_jd
from app.services.jd_parser import parse_jd
from app.services.project_intelligence import analyze_projects
from app.services.recommendation_engine import build_recommendations
from app.services.resume_parser import parse_resume
from app.services.scoring_engine import aggregate_scores_pipeline, compute_all_scores
from app.services.skill_matcher import match_skills, run_skill_extraction_pipeline
from app.utils.embeddings import EmbeddingProvider, get_embedding_provider
from app.utils.skill_normalization import DebugLog


def analyze_resume_jd(
    resume_file: str,
    jd_text: str,
    *,
    provider: Optional[EmbeddingProvider] = None,
    llm_provider: Optional[object] = None,
    debug: bool = True,
) -> Dict:
    """Run the full pipeline and return the complete structured payload."""
    if not isinstance(jd_text, str) or not jd_text.strip():
        raise ValueError("JD text must be a non-empty string.")
    provider = provider or get_embedding_provider()
    dbg = DebugLog() if debug else None

    # ── Parsing & JD intelligence ────────────────────────────────────────────
    parsed_resume = parse_resume(resume_file)
    # Single source of truth (Fix #1): reconcile intern-titled entries the parser
    # routed into work_experience under a shared "Experience" header, so the
    # scoring engine and experience intelligence operate on identical lists.
    parsed_resume["internships"], parsed_resume["work_experience"] = (
        reconcile_internship_work_experience(parsed_resume)
    )
    parsed_resume["_empty_sections"] = [
        k for k in ("skills", "projects", "certifications", "internships",
                    "work_experience", "education", "achievements")
        if not parsed_resume.get(k)
    ]
    jd_intel = analyze_jd(jd_text, llm_provider=llm_provider)
    parsed_jd = parse_jd(jd_text)  # dict the scoring/matching path expects
    domain = parsed_jd.get("domain_detected", "freshers")

    # ── Skill extraction + matching ──────────────────────────────────────────
    match_report = run_skill_extraction_pipeline(
        parsed_resume, parsed_jd, kw=None, provider=provider, debug=dbg
    )
    # Optional LLM validation gate (re-run matcher with the LLM on the same inputs)
    llm_validation = None
    if llm_provider is not None:
        gated = match_skills(
            match_report["resume_skill_phrases"], match_report["jd_skill_entries"],
            provider=provider, llm_provider=llm_provider,
        )
        llm_validation = gated.get("llm_validation")
        # Reflect the gate's decisions in the report used downstream.
        match_report["matched"] = gated["matched"]
        match_report["missing_from_resume"] = gated["missing_from_resume"]
        match_report["unmatched_in_resume"] = gated["unmatched_in_resume"]

    # ── Component scoring + composite ────────────────────────────────────────
    scores = compute_all_scores(parsed_resume, parsed_jd, match_report, provider=provider)
    aggregation = aggregate_scores_pipeline(
        scores, domain=domain, parsed_jd=parsed_jd, parsed_resume=parsed_resume
    )
    eff_weights = aggregation["effective_weights"]
    mask = aggregation["relevance_mask"]

    # ── Gap impact + improvement simulation + recommendations ────────────────
    jd_required = parsed_jd.get("required_skills", [])
    gap = estimate_gap_impacts_pipeline(scores, eff_weights, match_report, jd_required, mask)
    sims = simulate_improvements_pipeline(scores, eff_weights, gap, match_report, jd_required)
    recommendations = build_recommendations(parsed_jd, scores, mask)

    # ── Experience + project intelligence (+LLM enrichment) ──────────────────
    jd_dict = jd_intel.to_dict()
    experience = analyze_experience(parsed_resume, jd_dict, llm_provider=llm_provider)
    projects = analyze_projects(
        parsed_resume.get("projects", []), jd_dict,
        embedding_provider=provider, llm_provider=llm_provider,
    )

    # ── Explainability ───────────────────────────────────────────────────────
    explanation = assemble_explanation(
        jd_intel=jd_intel, exp_intel=experience, proj_intel=projects,
        match_result={"llm_validation": llm_validation} if llm_validation else match_report,
        llm_provider=llm_provider,
        missing_skills=match_report.get("missing_from_resume", []),
    )

    skills_detail = scores.get("_skills_detail", {})
    summary = match_report.get("summary", {})

    payload: Dict = {
        # 1 — Placement score
        "placement_score": aggregation["display_score"],
        "placement_score_raw_pct": aggregation["composite_score_pct"],
        "placement_score_fraction": aggregation["composite_score"],
        "match_level": aggregation["match_level"],

        # 2 — Domain & role
        "domain_detected": domain,
        "role_title": parsed_jd.get("role_title", "not_specified"),
        "llm_role_summary": jd_intel.llm_role_summary,
        "seniority_level": jd_intel.seniority_level,
        "llm_seniority": jd_intel.llm_seniority,

        # 3 — Component breakdown (6 MW-ESE)
        "component_breakdown": aggregation["breakdown"],
        "excluded_components": aggregation["excluded_components"],
        "weight_profile_used": aggregation["weight_profile_used"],
        "weights": aggregation["weights"],
        "effective_weights": eff_weights,
        "component_scores": {k: v for k, v in scores.items() if not k.startswith("_")},

        # 4 — Skills analysis
        "skills_analysis": {
            "total_jd_skills": summary.get("total_jd_phrases", 0),
            "matched_count": summary.get("total_matched", 0),
            "missing_skills": match_report.get("missing_from_resume", []),
            "skill_coverage_pct": round(skills_detail.get("weighted_jd_coverage", 0.0) * 100, 2),
            "match_details": match_report.get("matched", []),
            "skills_score_S_sk": skills_detail.get("score", 0.0),
        },

        # 5 — Improvement suggestions
        "improvement_suggestions": [
            {
                "rank": s.get("rank"), "improvement": s["improvement"],
                "current_score": s["current_score"], "predicted_score": s["new_score"],
                "delta_gain": s["delta"],
            }
            for s in sims.get("ranked_simulations", [])
        ],
        "combined_improvement": sims.get("combined_result", {}),
        "gap_analysis": {
            "ranked_gaps": gap.get("ranked_gaps", []),
            "total_recoverable_pct": gap.get("total_recoverable_pct", 0.0),
        },

        # 6 — Recommendations
        "recommendations": explanation.next_steps if (llm_provider and getattr(llm_provider, "backend", "none") != "none" and explanation.next_steps) else recommendations,

        # 7 — Resume extraction validation
        "resume_extraction": {
            "sections_present": [
                k for k in ("skills", "projects", "certifications", "internships",
                            "work_experience", "education", "achievements")
                if parsed_resume.get(k)
            ],
            "empty_sections": parsed_resume.get("_empty_sections", []),
            "skills": parsed_resume.get("skills", []),
            "certifications": parsed_resume.get("certifications", []),
            "projects": parsed_resume.get("projects", []),
            "internships": parsed_resume.get("internships", []),
            "work_experience": parsed_resume.get("work_experience", []),
            "education": parsed_resume.get("education", []),
            "achievements": parsed_resume.get("achievements", []),
            "skill_sources": parsed_resume.get("_skill_sources", {}),
        },

        # 8 — JD extraction validation
        "jd_extraction": {
            "required_skills": parsed_jd.get("required_skills", []),
            "preferred_skills": parsed_jd.get("preferred_skills", []),
            "optional_skills": parsed_jd.get("optional_skills", []),
            "domain_detected": domain,
            "primary_domain": jd_intel.primary_domain,
            "secondary_domain": jd_intel.secondary_domain,
            "role_title": parsed_jd.get("role_title", "not_specified"),
            "experience_years": parsed_jd.get("experience_years", 0),
            "education_level": parsed_jd.get("education_level", "not_specified"),
            "rules": parsed_jd.get("rules", {}),
            "llm_excluded_noise": jd_intel.llm_excluded_noise,
            "llm_responsibilities": jd_intel.llm_responsibilities,
        },

        # 9 — Matching transparency (by match type)
        "matching_transparency": _matches_by_type(match_report.get("matched", [])),

        # 10 — Debug / validation
        "debug": {
            "resume_skill_count": summary.get("total_resume_phrases", 0),
            "jd_skill_count": summary.get("total_jd_phrases", 0),
            "match_type_counts": summary.get("match_type_counts", {}),
            "weighted_jd_coverage": summary.get("weighted_jd_coverage", 0.0),
            "avg_match_confidence": summary.get("avg_match_confidence", 0.0),
            "resume_pool_coverage": summary.get("resume_pool_coverage", 0.0),
            "final_skill_score": skills_detail.get("score", 0.0),
            "jd_bucket_counts": summary.get("jd_bucket_counts", {}),
            "resume_skill_source_counts": summary.get("resume_skill_source_counts", {}),
            "rejected_jd_candidates": parsed_jd.get("_rejected_skill_candidates", []),
            "llm_validation": llm_validation,
            "embedding_backend": summary.get("embedding_backend", provider.backend),
            "llm_backend": getattr(llm_provider, "backend", "none") if llm_provider else "none",
            "full_debug_log": dbg.to_dict() if dbg is not None else None,
        },

        # 11 — Final output summary
        "final_summary": {
            "overall_assessment": explanation.overall_summary
                or f"{aggregation['match_level']} fit ({aggregation['display_score']}%).",
            "candidate_category": experience.candidate_category,
            "strengths": explanation.top_strengths,
            "weaknesses": explanation.top_gaps,
            "key_missing_requirements": match_report.get("missing_from_resume", [])[:8],
            "recommended_next_actions": explanation.next_steps or recommendations,
        },

        # Auxiliary intelligence (full objects for deep inspection)
        "experience_intelligence": experience.to_dict(),
        "project_intelligence": projects.to_dict(),
        "explainability": explanation.to_dict(),
    }
    return payload


def _matches_by_type(matched: list) -> Dict[str, list]:
    buckets: Dict[str, list] = {
        "exact": [], "alias": [], "synonym": [], "semantic": [], "partial": [], "cluster": [],
    }
    for m in matched:
        mt = m.get("match_type", "")
        buckets.setdefault(mt, [])
        buckets[mt].append({
            "resume_phrase": m.get("resume_phrase"),
            "jd_phrase": m.get("jd_phrase"),
            "similarity": m.get("similarity"),
            "match_score": m.get("match_score"),
        })
    return buckets
