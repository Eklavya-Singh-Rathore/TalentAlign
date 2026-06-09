"""Gap-impact estimation + improvement simulation.

Ported from the legacy Code/app_logic.py (Stages 6–7). Given the 6 component
scores, the effective weights, and the skill-match report, it:
  - identifies skill gaps (missing JD skills) and component gaps,
  - estimates the placement-score uplift of fixing each,
  - simulates "what-if" improvements (add a skill / improve a component),
  - reports ranked improvements with current→predicted score + delta, and a
    combined top-N improvement potential.
"""

from __future__ import annotations

from typing import Dict, List

from app.services.scoring_engine import COMPONENTS, NON_SKILL_COMPONENTS, compute_composite_score
from app.utils.skill_normalization import (
    compute_weighted_skill_score,
    normalize_phrase,
    normalize_skill,
)

TOP_N_IMPROVEMENTS = 3  # legacy DEFAULT_TOP_N for the combined-improvement simulation


# ─── Gap identification ──────────────────────────────────────────────────────


def identify_skill_gaps(missing_skills: List[str]) -> List[Dict]:
    return [{"factor": s, "component": "Skills", "score_key": "S_sk"} for s in missing_skills]


def identify_component_gaps(scores: Dict[str, float], mask: Dict[str, bool]) -> List[Dict]:
    component_mask_keys = {
        "S_pr": "projects", "S_in": "internships",
        "S_we": "work_experience", "S_ac": "academics", "S_ah": "achievements",
    }
    gaps = []
    for score_key, display_name, _weight_key in NON_SKILL_COMPONENTS:
        if not mask.get(component_mask_keys.get(score_key, ""), True):
            continue
        current = float(scores[score_key])
        if current < 1.0:
            factor = f"Improve {display_name}" if current > 0 else f"No {display_name}"
            gaps.append({
                "factor": factor, "component": display_name,
                "score_key": score_key, "gap_magnitude": round(1.0 - current, 6),
            })
    return gaps


def _simulate_skill_score_details(skill_match_report: Dict, added_skills: List[str]) -> Dict:
    """Recompute weighted S_sk after hypothetically adding exact missing-skill matches."""
    current_resume = list(skill_match_report.get("resume_skill_phrases", []))
    current_matched = list(skill_match_report.get("matched", []))
    jd_entries = list(skill_match_report.get("jd_skill_entries", []))
    existing_resume = {normalize_skill(normalize_phrase(i)) for i in current_resume}
    existing_jd_matches = {
        (normalize_skill(normalize_phrase(i.get("jd_phrase", ""))),
         str(i.get("jd_bucket", "required")).strip().lower() or "required")
        for i in current_matched
    }
    jd_bucket_lookup = {
        normalize_skill(normalize_phrase(i.get("phrase", ""))):
            str(i.get("bucket", "required")).strip().lower() or "required"
        for i in jd_entries
    }
    for skill in added_skills:
        normalized = normalize_skill(normalize_phrase(skill))
        if not normalized:
            continue
        if normalized not in existing_resume:
            current_resume.append(normalized)
            existing_resume.add(normalized)
        bucket = jd_bucket_lookup.get(normalized, "required")
        if (normalized, bucket) not in existing_jd_matches:
            current_matched.append({
                "resume_phrase": normalized, "jd_phrase": normalized,
                "jd_bucket": bucket, "similarity": 1.0, "token_overlap": 1.0,
                "match_type": "exact", "match_score": 1.0,
            })
            existing_jd_matches.add((normalized, bucket))
    return compute_weighted_skill_score(
        jd_entries=jd_entries, matched_pairs=current_matched,
        total_resume_phrases=len(current_resume),
    )


def compute_skill_gap_impacts(
    skill_gaps: List[Dict], skill_match_report: Dict,
    current_skill_score: float, w_sk: float,
) -> List[Dict]:
    results = []
    for gap in skill_gaps:
        new_score = _simulate_skill_score_details(skill_match_report, [gap["factor"]])["score"]
        impact = round(max(0.0, w_sk * (new_score - current_skill_score)), 6)
        results.append({
            "factor": gap["factor"], "component": gap["component"],
            "impact": impact, "impact_pct": f"{impact * 100:.1f}%",
        })
    return results


def compute_component_gap_impacts(component_gaps: List[Dict], weights: Dict[str, float]) -> List[Dict]:
    weight_lookup = {c[0]: c[2] for c in COMPONENTS}
    results = []
    for gap in component_gaps:
        wk = weight_lookup[gap["score_key"]]
        impact = round(float(weights[wk]) * gap["gap_magnitude"], 6)
        results.append({
            "factor": gap["factor"], "component": gap["component"],
            "impact": impact, "impact_pct": f"{impact * 100:.1f}%",
        })
    return results


def rank_gaps(all_impacts: List[Dict]) -> List[Dict]:
    sorted_gaps = sorted(all_impacts, key=lambda x: x["impact"], reverse=True)
    return [{"rank": i + 1, **g} for i, g in enumerate(sorted_gaps)]


def estimate_gap_impacts_pipeline(
    scores: Dict[str, float], weights: Dict[str, float],
    skill_match_report: Dict, jd_required_skills: List[str], mask: Dict[str, bool],
) -> Dict:
    missing = skill_match_report.get("missing_from_resume", [])
    s_gaps = identify_skill_gaps(missing)
    c_gaps = identify_component_gaps(scores, mask)
    w_sk = float(weights.get("skills_weight", 0.35))
    s_impacts = compute_skill_gap_impacts(
        s_gaps, skill_match_report=skill_match_report,
        current_skill_score=float(scores.get("S_sk", 0.0)), w_sk=w_sk,
    )
    c_impacts = compute_component_gap_impacts(c_gaps, weights)
    ranked = rank_gaps(s_impacts + c_impacts)
    ranked = [g for g in ranked if g["impact"] > 0]
    for i, g in enumerate(ranked):
        g["rank"] = i + 1
    recoverable = round(sum(g["impact"] for g in ranked), 6)
    current = compute_composite_score(scores, weights)
    return {
        "ranked_gaps": ranked,
        "total_recoverable": recoverable,
        "total_recoverable_pct": round(recoverable * 100, 2),
        "current_score": current,
        "current_score_pct": round(current * 100, 2),
    }


# ─── Improvement simulation ──────────────────────────────────────────────────


def simulate_add_skill(
    skill: str, current_scores: Dict[str, float], weights: Dict[str, float],
    current_total: float, skill_match_report: Dict,
) -> Dict:
    current_s_sk = float(current_scores["S_sk"])
    new_s_sk = _simulate_skill_score_details(skill_match_report, [skill])["score"]
    w_sk = float(weights["skills_weight"])
    delta = round(w_sk * (new_s_sk - current_s_sk), 6)
    new_total = round(current_total + delta, 6)
    return {
        "improvement": f"Add {skill}", "component": "Skills",
        "current_S_i": round(current_s_sk, 4), "new_S_i": round(new_s_sk, 4),
        "current_score": round(current_total * 100, 2),
        "new_score": round(new_total * 100, 2), "delta": round(delta * 100, 2),
    }


def simulate_improve_component(
    component_name: str, score_key: str, new_value: float,
    current_scores: Dict[str, float], weights: Dict[str, float], current_total: float,
) -> Dict:
    weight_key = next((wk for sk, _n, wk in COMPONENTS if sk == score_key), None)
    current_s_i = float(current_scores[score_key])
    new_s_i = min(float(new_value), 1.0)
    w_i = float(weights[weight_key])
    delta = round(w_i * (new_s_i - current_s_i), 6)
    new_total = round(current_total + delta, 6)
    return {
        "improvement": f"Improve {component_name}", "component": component_name,
        "current_S_i": round(current_s_i, 4), "new_S_i": round(new_s_i, 4),
        "current_score": round(current_total * 100, 2),
        "new_score": round(new_total * 100, 2), "delta": round(delta * 100, 2),
    }


def simulate_all_improvements(
    ranked_gaps: List[Dict], current_scores: Dict[str, float],
    weights: Dict[str, float], current_total: float, skill_match_report: Dict,
) -> List[Dict]:
    sims = []
    for gap in ranked_gaps:
        component = gap["component"]
        if component == "Skills":
            sims.append(simulate_add_skill(
                gap["factor"], current_scores, weights, current_total, skill_match_report))
        else:
            score_key = next((sk for sk, dn, _wk in COMPONENTS if dn == component), None)
            if score_key:
                sims.append(simulate_improve_component(
                    component, score_key, 1.0, current_scores, weights, current_total))
    return sims


def rank_improvements(simulations: List[Dict]) -> List[Dict]:
    sorted_sims = sorted(simulations, key=lambda x: x["delta"], reverse=True)
    return [{"rank": i + 1, **s} for i, s in enumerate(sorted_sims)]


def simulate_combined(
    top_n_improvements: List[Dict], current_scores: Dict[str, float],
    weights: Dict[str, float], current_total: float, skill_match_report: Dict,
) -> Dict:
    if not top_n_improvements:
        return {
            "improvements_applied": [], "current_score": round(current_total * 100, 2),
            "combined_new_score": round(current_total * 100, 2), "combined_delta": 0.0,
        }
    new_scores = dict(current_scores)
    added_skills, applied = [], []
    for sim in top_n_improvements:
        applied.append(sim["improvement"])
        if sim["component"] == "Skills":
            added_skills.append(sim["improvement"].replace("Add ", "", 1))
        else:
            for sk, dn, _wk in COMPONENTS:
                if dn == sim["component"]:
                    new_scores[sk] = sim["new_S_i"]
                    break
    if added_skills:
        new_scores["S_sk"] = _simulate_skill_score_details(skill_match_report, added_skills)["score"]
    combined_total = compute_composite_score(new_scores, weights)
    return {
        "improvements_applied": applied, "current_score": round(current_total * 100, 2),
        "combined_new_score": round(combined_total * 100, 2),
        "combined_delta": round((combined_total - current_total) * 100, 2),
    }


def _deduplicate_skill_simulations(ranked: List[Dict]) -> List[Dict]:
    kept: List[Dict] = []
    for sim in ranked:
        if sim["component"] != "Skills":
            kept.append(sim)
            continue
        skill = sim["improvement"].replace("Add ", "", 1)
        skill_tokens = set(skill.split())
        redundant = False
        for existing in kept:
            if existing["component"] != "Skills":
                continue
            existing_skill = existing["improvement"].replace("Add ", "", 1)
            existing_tokens = set(existing_skill.split())
            union_set = skill_tokens | existing_tokens
            overlap = len(skill_tokens & existing_tokens) / len(union_set) if union_set else 0
            if overlap >= 0.5 and abs(sim["delta"] - existing["delta"]) < 0.15:
                redundant = True
                break
        if not redundant:
            kept.append(sim)
    return kept


def simulate_improvements_pipeline(
    scores: Dict[str, float], weights: Dict[str, float],
    gap_analysis: Dict, skill_match_report: Dict,
    jd_required_skills: List[str], top_n: int = TOP_N_IMPROVEMENTS,
) -> Dict:
    current_total = float(gap_analysis.get("current_score", 0.0))
    ranked_gaps = gap_analysis.get("ranked_gaps", [])
    if not ranked_gaps:
        return {
            "ranked_simulations": [],
            "combined_result": {
                "improvements_applied": [], "current_score": round(current_total * 100, 2),
                "combined_new_score": round(current_total * 100, 2), "combined_delta": 0.0,
            },
            "current_score": current_total, "current_score_pct": round(current_total * 100, 2),
        }
    all_sims = simulate_all_improvements(ranked_gaps, scores, weights, current_total, skill_match_report)
    ranked = rank_improvements(all_sims)
    ranked = [s for s in ranked if s["delta"] > 0]
    ranked = _deduplicate_skill_simulations(ranked)
    for i, s in enumerate(ranked):
        s["rank"] = i + 1
    actual_top_n = min(top_n, len(ranked))
    combined = simulate_combined(ranked[:actual_top_n], scores, weights, current_total, skill_match_report)
    return {
        "ranked_simulations": ranked, "combined_result": combined,
        "current_score": current_total, "current_score_pct": round(current_total * 100, 2),
    }
