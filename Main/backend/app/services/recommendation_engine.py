"""Actionable recommendation generation.

Ported from the legacy Code/app_logic.py::_build_recommendations. Produces
actionable, JD-aware recommendations (internship / projects / work experience
/ certifications) — deliberately NOT raw "learn skill X" items (those live in
the improvement-simulation layer).
"""

from __future__ import annotations

from typing import Dict, List, Optional


def build_recommendations(
    parsed_jd: Dict,
    scores: Optional[Dict] = None,
    mask: Optional[Dict] = None,
) -> List[str]:
    """Generate actionable text recommendations from component scores + JD mask."""
    mask = mask or {}
    recs: List[str] = []
    domain = parsed_jd.get("domain_detected", parsed_jd.get("primary_domain", "your field"))
    domain = str(domain).replace("_", " ")
    role = parsed_jd.get("role_title", "target role")

    ach_detail = scores.get("_achievements_detail", {}) if scores else {}

    # Internship (only if active in mask and score is zero)
    if mask.get("internships", True) and scores and float(scores.get("S_in", 0)) == 0.0:
        recs.append(f"Complete an internship in {domain}")

    # Projects
    if scores and float(scores.get("S_pr", 0)) < 0.7:
        recs.append(f"Build 1-2 projects aligned with {role}")

    # Work experience (only if JD requires it)
    if mask.get("work_experience", False) and scores and float(scores.get("S_we", 0)) < 0.5:
        recs.append(f"Gain work experience in {domain}")

    # Certifications (from missing-skill suggestions)
    for suggestion in ach_detail.get("suggested_certifications", [])[:3]:
        if suggestion not in recs:
            recs.append(suggestion)

    return recs
