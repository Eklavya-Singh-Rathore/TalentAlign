"""MW-ESE component + composite scoring engine.

Ported from the legacy Code/app_logic.py (Stages 4–5: component scoring +
weight aggregation) into the TalentAlign backend. Computes the 6 weighted
components and the JD-adjusted composite "placement score" the prototype UI
displayed.

Adaptations vs. the legacy:
  - SBERT calls go through the Phase-4 EmbeddingProvider (SBERT → TF-IDF →
    token), not a hard sentence-transformers dependency.
  - Domain weight profiles come from app.core.config (weight_config.json).
  - Duration extraction reuses app.utils.duration_extraction.

The 6 components (MW-ESE): Skills, Projects, Internships, Work Experience,
Academics, Achievements/Certifications. Work Experience and Academics are
JD-gated (only scored when the JD requires them); their freed weight is
redistributed across the active components ("effective score").
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from app.core.config import get_weight_config
from app.utils.duration_extraction import (
    aggregate_durations,
    count_roles,
    extract_duration_months,
)
from app.utils.embeddings import EmbeddingProvider, get_embedding_provider
from app.utils.skill_normalization import (
    compute_weighted_skill_score,
    has_technical_signal,
)


# ─── Constants (ported verbatim) ─────────────────────────────────────────────

# (score_key, display_name, weight_key)
COMPONENTS: Tuple[Tuple[str, str, str], ...] = (
    ("S_sk", "Skills", "skills_weight"),
    ("S_pr", "Projects", "projects_weight"),
    ("S_in", "Internships", "internship_weight"),
    ("S_we", "Work Experience", "experience_weight"),
    ("S_ac", "Academics", "academics_weight"),
    ("S_ah", "Achievements_Certifications", "achievements_weight"),
)
NON_SKILL_COMPONENTS = COMPONENTS[1:]
REQUIRED_WEIGHT_KEYS = tuple(c[2] for c in COMPONENTS)
WEIGHT_SUM_TOLERANCE = 1e-6

# Match-level bands on the normalized DISPLAY scale (0-100), recalibrated against
# the 54-pair baseline (see normalize_display_score).
MATCH_LEVELS = [
    (85.0, "EXCELLENT"),
    (70.0, "GOOD"),
    (50.0, "MODERATE"),
    (30.0, "BELOW AVERAGE"),
    (0.0, "POOR"),
]

# Display-normalization anchors: (raw composite 0-1, display 0-100). Calibrated
# against the 54-pair baseline so the realistic ~0.20-0.55 raw band spreads into
# an intuitive ~35-80 display range. Monotonic; the raw composite is retained in
# the payload (composite_score / placement_score_fraction).
_DISPLAY_ANCHORS = [
    (0.0, 0.0), (0.15, 25.0), (0.30, 50.0), (0.45, 68.0), (0.60, 85.0), (1.0, 100.0),
]

DURATION_FACTORS = {"short": 0.7, "medium": 0.85, "long": 1.0}

# Proposal 4: internships count toward a professional-experience requirement at
# half credit — a fresher's internships partially satisfy experience, while
# professional work remains the higher-value signal.
INTERNSHIP_EXPERIENCE_DISCOUNT = 0.5

ACHIEVEMENT_PATTERNS = {
    "hackathon": {"score": 0.2, "keywords": ["hackathon", "hack-a-thon", "makeathon"]},
    "publication": {"score": 0.2, "keywords": ["publish", "publication", "paper", "journal", "conference paper", "ieee", "acm"]},
    "competitive_coding": {"score": 0.15, "keywords": ["competitive coding", "competitive programming", "codeforces", "codechef", "leetcode", "icpc"]},
    "other_awards": {"score": 0.15, "keywords": ["award", "winner", "1st place", "2nd place", "3rd place", "gold medal", "silver medal", "scholarship", "merit", "honor", "distinction"]},
}

_COMPONENT_MASK_KEYS = {
    "S_sk": "skills", "S_pr": "projects", "S_in": "internships",
    "S_we": "work_experience", "S_ac": "academics", "S_ah": "achievements",
}


# ─── Embedding helper ────────────────────────────────────────────────────────


def _max_similarity_to_jd(
    items: Sequence[str], jd_text: str, provider: EmbeddingProvider
) -> float:
    """Max cosine similarity of any item to the JD text (clamped ≥ 0)."""
    items = [i for i in items if i and i.strip()]
    if not items or not jd_text.strip():
        return 0.0
    item_emb, jd_emb = provider.encode_pair(list(items), [jd_text])
    sim = provider.cosine_similarity(item_emb, jd_emb)  # shape (n, 1)
    best = 0.0
    for row in sim:
        v = float(row[0])
        if v > best:
            best = v
    return max(best, 0.0)


def _similarities_to_jd(
    items: Sequence[str], jd_text: str, provider: EmbeddingProvider
) -> List[float]:
    items = [i for i in items if i and i.strip()]
    if not items or not jd_text.strip():
        return []
    item_emb, jd_emb = provider.encode_pair(list(items), [jd_text])
    sim = provider.cosine_similarity(item_emb, jd_emb)
    return [float(row[0]) for row in sim]


# ─── Component scorers ───────────────────────────────────────────────────────


def compute_skills_score(match_report: Dict) -> Dict:
    """Authoritative weighted skill-score detail (from the match report)."""
    if not match_report or "summary" not in match_report:
        base = compute_weighted_skill_score([], [], 0)
        base["missing_skills"] = []
        return base

    summary = match_report.get("summary", {})
    missing = match_report.get("missing_from_resume", [])
    if "weighted_jd_total" in summary and "match_type_counts" in summary:
        return {
            "score": float(summary.get("skills_score_S_sk", 0.0)),
            "matched_count": int(summary.get("total_matched", 0)),
            "total_jd_count": int(summary.get("total_jd_phrases", 0)),
            "weighted_jd_total": float(summary.get("weighted_jd_total", 0.0)),
            "weighted_match_total": float(summary.get("weighted_match_total", 0.0)),
            "weighted_jd_coverage": float(summary.get("weighted_jd_coverage", 0.0)),
            "avg_match_confidence": float(summary.get("avg_match_confidence", 0.0)),
            "resume_pool_coverage": float(summary.get("resume_pool_coverage", 0.0)),
            "matched_resume_phrases": int(summary.get("matched_resume_phrases", 0)),
            "total_resume_phrases": int(summary.get("total_resume_phrases", 0)),
            "jd_bucket_counts": dict(summary.get("jd_bucket_counts", {})),
            "match_type_counts": dict(summary.get("match_type_counts", {})),
            "score_component_weights": dict(summary.get("score_component_weights", {})),
            "missing_skills": missing,
        }

    result = compute_weighted_skill_score(
        jd_entries=match_report.get("jd_skill_entries", []),
        matched_pairs=match_report.get("matched", []),
        total_resume_phrases=len(match_report.get("resume_skill_phrases", [])),
    )
    result["missing_skills"] = missing
    return result


def compute_projects_score(projects: List[str], jd_text: str, provider: EmbeddingProvider) -> float:
    """S_pr = count_score (50%) + best semantic alignment (50%)."""
    if not projects or not jd_text:
        return 0.0
    count_score = min(len(projects) / 3, 1.0) * 0.5
    semantic_score = _max_similarity_to_jd(projects, jd_text, provider) * 0.5
    return max(min(round(count_score + semantic_score, 4), 1.0), 0.0)


def _duration_factor(months: Optional[float]) -> float:
    if months is None:
        return DURATION_FACTORS["short"]
    if months < 3:
        return DURATION_FACTORS["short"]
    if months <= 6:
        return DURATION_FACTORS["medium"]
    return DURATION_FACTORS["long"]


def compute_internship_score(internships: List[str], jd_text: str, provider: EmbeddingProvider) -> float:
    """S_in = count(40%) + relevance(30%) + duration_factor(30%); 0 when empty.

    Count is *role-based* (date-anchored), so a single internship's title + bullet
    lines count once instead of saturating the tally at the entry-line level.
    """
    if not internships or not jd_text:
        return 0.0
    count_score = min(count_roles(internships) / 2, 1.0) * 0.4
    relevance_score = _max_similarity_to_jd(internships, jd_text, provider) * 0.3
    durations = [extract_duration_months(d).months for d in internships]
    best_duration = max((d for d in durations if d is not None), default=None)
    duration_score = _duration_factor(best_duration) * 0.3
    return min(round(count_score + relevance_score + duration_score, 4), 1.0)


def compute_work_exp_score(
    work_experience: List[str], required_years: int,
    internships: Optional[List[str]] = None,
) -> float:
    """S_we with an internship→experience bridge (Proposal 4).

    Professional work counts fully; internship time counts at a discount
    (``INTERNSHIP_EXPERIENCE_DISCOUNT``), so a fresher's internships partially
    satisfy an experience requirement while professional experience stays the
    higher-value signal. Durations come from ``aggregate_durations`` (date ranges
    + explicit mentions), so dated "Mon YYYY - Mon YYYY" tenures are counted
    (the previous regex only caught literal "N years/months").
    """
    internships = internships or []
    work_months = aggregate_durations(work_experience).total_months if work_experience else 0.0
    intern_months = aggregate_durations(internships).total_months if internships else 0.0
    effective_years = (work_months + INTERNSHIP_EXPERIENCE_DISCOUNT * intern_months) / 12.0
    if effective_years <= 0:
        return 0.0
    if required_years <= 0:
        return 1.0
    return min(round(effective_years / required_years, 4), 1.0)


def compute_academic_score(education: List[str]) -> float:
    """S_ac = normalized GPA/CGPA/percentage, with degree-level fallback."""
    if not education:
        return 0.0
    best = None
    has_degree = False
    for entry in education:
        entry_lower = entry.lower()
        if re.search(
            r"\b(?:b\.?tech|m\.?tech|b\.?e|m\.?e|bachelor|master|b\.?sc|m\.?sc|mba|mca|bca|phd)\b",
            entry_lower,
        ):
            has_degree = True
        cgpa = re.search(r"cgpa\s*[:\-]?\s*(\d+\.?\d*)\s*(?:/\s*(\d+))?", entry_lower)
        if cgpa:
            val = float(cgpa.group(1))
            scale = float(cgpa.group(2)) if cgpa.group(2) else 10.0
            n = val / scale if scale > 0 else 0.0
            best = n if best is None or n > best else best
            continue
        gpa = re.search(r"\bgpa\s*[:\-]?\s*(\d+\.?\d*)\s*(?:/\s*(\d+\.?\d*))?", entry_lower)
        if gpa:
            val = float(gpa.group(1))
            scale = float(gpa.group(2)) if gpa.group(2) else 4.0
            n = val / scale if scale > 0 else 0.0
            best = n if best is None or n > best else best
            continue
        pct = re.search(r"(?:percentage|marks|score)\s*[:\-]?\s*(\d+\.?\d*)\s*%?", entry_lower)
        if pct:
            n = float(pct.group(1)) / 100.0
            best = n if best is None or n > best else best
            continue
        sp = re.search(r"(\d{2,3})\s*%", entry_lower)
        if sp:
            n = float(sp.group(1)) / 100.0
            best = n if best is None or n > best else best
    if best is not None:
        return round(min(max(best, 0.0), 1.0), 4)
    return 0.6 if has_degree else 0.0


def compute_achievements_score(
    achievements: Optional[List[str]] = None,
    certifications: Optional[List[str]] = None,
    missing_skills: Optional[List[str]] = None,
    jd_text: str = "",
    provider: Optional[EmbeddingProvider] = None,
) -> Dict:
    """S_ah = achievement categories (≤0.7) + certifications (≤0.5), cap 1.0."""
    achievements = achievements or []
    certifications = certifications or []
    missing_skills = missing_skills or []

    total = 0.0
    matched_categories = set()
    for entry in achievements:
        entry_lower = entry.lower()
        for category, config in ACHIEVEMENT_PATTERNS.items():
            if category in matched_categories:
                continue
            if any(kw in entry_lower for kw in config["keywords"]):
                matched_categories.add(category)
                total += config["score"]

    cert_score = 0.0
    if certifications:
        if provider is not None and jd_text:
            for sim in _similarities_to_jd(certifications, jd_text, provider):
                if sim >= 0.5:
                    cert_score += 0.15
                elif sim >= 0.3:
                    cert_score += 0.10
                else:
                    cert_score += 0.05
        else:
            cert_score = len(certifications) * 0.1
        cert_score = min(cert_score, 0.5)
    total += cert_score

    # Only recommend certifications for plausibly certifiable (technical) skills;
    # soft/conceptual gaps (e.g. "analytical reasoning", "innovation mindset")
    # shouldn't yield a "get a certification in X" suggestion.
    certifiable = [s for s in missing_skills if has_technical_signal(s)]
    suggested_certs = [f"Obtain certification in '{s}'" for s in certifiable[:3]]

    score = min(round(total, 4), 1.0)
    if not achievements and not certifications:
        score = 0.0
    return {
        "score": score,
        "achievement_categories": sorted(matched_categories),
        "certification_count": len(certifications),
        "suggested_certifications": suggested_certs,
    }


def compute_all_scores(
    parsed_resume: Dict, parsed_jd: Dict, skill_match_report: Dict,
    provider: Optional[EmbeddingProvider] = None,
) -> Dict[str, object]:
    """Compute all 6 MW-ESE component scores (JD-gated for WE & Academics)."""
    provider = provider or get_embedding_provider()
    jd_text = parsed_jd.get("raw_text", "")
    jd_rules = parsed_jd.get("rules", {})

    skills_result = compute_skills_score(skill_match_report)
    skills_result["matched_pairs"] = skill_match_report.get("matched", [])

    s_pr = compute_projects_score(parsed_resume.get("projects", []), jd_text, provider)
    s_in = compute_internship_score(parsed_resume.get("internships", []), jd_text, provider)

    s_we = (
        compute_work_exp_score(parsed_resume.get("work_experience", []),
                               int(parsed_jd.get("experience_years", 0)),
                               internships=parsed_resume.get("internships", []))
        if jd_rules.get("requires_experience", False) else 0.0
    )
    s_ac = (
        compute_academic_score(parsed_resume.get("education", []))
        if jd_rules.get("requires_academics", False) else 0.0
    )
    achievements_result = compute_achievements_score(
        achievements=parsed_resume.get("achievements", []),
        certifications=parsed_resume.get("certifications", []),
        missing_skills=skills_result.get("missing_skills", []),
        jd_text=jd_text, provider=provider,
    )

    return {
        "S_sk": skills_result["score"],
        "S_pr": s_pr, "S_in": s_in, "S_we": s_we, "S_ac": s_ac,
        "S_ah": achievements_result["score"],
        "_skills_detail": skills_result,
        "_achievements_detail": achievements_result,
        "_jd_rules": jd_rules,
    }


# ─── Weight aggregation / composite ──────────────────────────────────────────


def _weights_for_domain(domain: Optional[str], custom_weights: Optional[Dict]) -> Tuple[str, Dict[str, float]]:
    if custom_weights:
        validate_weights(custom_weights)
        return "custom", dict(custom_weights)
    cfg = get_weight_config()
    profile = cfg.get_profile(str(domain).strip() if domain else "")
    name = domain if (domain in cfg.profiles) else cfg.default_profile
    weights = profile.as_dict()
    validate_weights(weights)
    return name, weights


def validate_weights(weights: Dict[str, float]) -> bool:
    total = 0.0
    for key in REQUIRED_WEIGHT_KEYS:
        if key not in weights:
            raise ValueError(f"Missing weight: {key}")
        val = float(weights[key])
        if val < 0.0:
            raise ValueError(f"{key} must be non-negative.")
        total += val
    if abs(total - 1.0) > 1e-2:
        raise ValueError(f"Weights must sum to ~1.0, got {total:.6f}.")
    return True


def compute_composite_score(scores: Dict[str, float], weights: Dict[str, float]) -> float:
    total = 0.0
    for score_key, _name, weight_key in COMPONENTS:
        s_val = float(scores[score_key]) if isinstance(scores[score_key], (int, float)) else 0.0
        total += float(weights[weight_key]) * s_val
    return round(total, 6)


def build_relevance_mask(parsed_jd: Dict, parsed_resume: Dict) -> Dict[str, bool]:
    rules = parsed_jd.get("rules", {})
    # Achievements/Certifications is dynamically activated (Proposal 2): when the
    # resume has neither achievements nor certifications the component is marked
    # inactive and its weight is redistributed across the active components,
    # rather than dragging the composite down with a guaranteed 0. When at least
    # one is present, it scores with the existing capped contribution logic.
    # Guard: if the JD *explicitly* requires achievements, keep the component
    # active even when absent, so the gap is a legitimate (scored-0) penalty
    # instead of being redistributed away.
    has_achievements_or_certs = bool(
        parsed_resume.get("achievements") or parsed_resume.get("certifications")
    )
    requires_achievements = bool(rules.get("requires_achievements", False))
    return {
        "skills": True, "projects": True, "internships": True,
        "work_experience": bool(rules.get("requires_experience", False)),
        "academics": bool(rules.get("requires_academics", False)),
        "achievements": has_achievements_or_certs or requires_achievements,
    }


def compute_effective_score(
    scores: Dict[str, float], weights: Dict[str, float], mask: Dict[str, bool],
) -> Tuple[float, Dict[str, float], List[Dict]]:
    """Effective JD-adjusted score with weight renormalization over active components."""
    active_weight_sum = 0.0
    excluded = []
    for score_key, name, weight_key in COMPONENTS:
        if mask.get(_COMPONENT_MASK_KEYS[score_key], True):
            active_weight_sum += float(weights[weight_key])
        else:
            excluded.append({"component": name, "reason": "Not required by JD"})
    if active_weight_sum <= 0:
        active_weight_sum = 1.0

    renorm_weights = {}
    effective_total = 0.0
    for score_key, name, weight_key in COMPONENTS:
        if mask.get(_COMPONENT_MASK_KEYS[score_key], True):
            w_prime = float(weights[weight_key]) / active_weight_sum
            renorm_weights[weight_key] = round(w_prime, 6)
            s_val = float(scores[score_key]) if isinstance(scores[score_key], (int, float)) else 0.0
            effective_total += w_prime * s_val
        else:
            renorm_weights[weight_key] = 0.0
    return round(effective_total, 6), renorm_weights, excluded


def generate_breakdown_table(
    scores: Dict[str, float], effective_weights: Dict[str, float], mask: Dict[str, bool],
) -> List[Dict]:
    """All 6 components with renormalized weight + achieved contribution."""
    breakdown = []
    for score_key, component_name, weight_key in COMPONENTS:
        is_active = mask.get(_COMPONENT_MASK_KEYS[score_key], True)
        ew = float(effective_weights[weight_key]) if is_active else 0.0
        s = float(scores[score_key]) if (is_active and isinstance(scores[score_key], (int, float))) else 0.0
        breakdown.append({
            "component": component_name,
            "weight": round(ew, 4),
            "component_score": round(s, 4),
            "score_achieved": round(ew * s, 6),
            "pct_contribution": round(ew * s * 100, 2),
            "active": is_active,
        })
    return breakdown


def aggregate_scores_pipeline(
    scores: Dict[str, float], domain: Optional[str] = None,
    custom_weights: Optional[Dict] = None,
    parsed_jd: Optional[Dict] = None, parsed_resume: Optional[Dict] = None,
) -> Dict:
    """Weighted aggregation → effective JD-adjusted composite score + breakdown."""
    profile_name, weights = _weights_for_domain(domain, custom_weights)
    mask = build_relevance_mask(parsed_jd or {}, parsed_resume or {})
    effective_score, effective_weights, excluded = compute_effective_score(scores, weights, mask)
    breakdown = generate_breakdown_table(scores, effective_weights, mask)
    display_score = normalize_display_score(effective_score)
    return {
        "composite_score": effective_score,
        "composite_score_pct": round(effective_score * 100, 2),
        "display_score": display_score,
        "match_level": get_match_level(display_score),
        "breakdown": breakdown,
        "weight_profile_used": profile_name,
        "weights": weights,
        "effective_weights": effective_weights,
        "relevance_mask": mask,
        "excluded_components": excluded,
    }


def normalize_display_score(raw01: float) -> float:
    """Map the raw composite (0-1) to a 0-100 display score via a fixed,
    documented, monotonic piecewise-linear curve (``_DISPLAY_ANCHORS``).

    Preserves ranking; the raw composite is retained separately in the payload.
    Calibrated against the 54-pair baseline (revisit the anchors if the score
    distribution shifts materially).
    """
    r = max(0.0, min(1.0, float(raw01)))
    for (x0, y0), (x1, y1) in zip(_DISPLAY_ANCHORS, _DISPLAY_ANCHORS[1:]):
        if r <= x1:
            t = (r - x0) / (x1 - x0) if x1 > x0 else 0.0
            return round(y0 + t * (y1 - y0), 2)
    return 100.0


def get_match_level(display_score: float) -> str:
    """Match-level label from the normalized DISPLAY score (0-100)."""
    for threshold, label in MATCH_LEVELS:
        if display_score >= threshold:
            return label
    return "POOR"
