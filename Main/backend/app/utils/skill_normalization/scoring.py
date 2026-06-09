"""Skill scoring + debug log.

DebugLog accumulates per-pipeline transparency; the two scoring functions
implement the P7.1 coverage-weighted hybrid score the engine consumes.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List

from .constants import JD_BUCKET_WEIGHTS, SKILL_SCORE_COMPONENT_WEIGHTS
from .text import normalize_phrase, normalize_skill


# ---------------------------------------------------------------------------
# L9 — Debug & transparency layer
# ---------------------------------------------------------------------------

@dataclass
class DebugLog:
    """Structured debug log accumulated through the skill-extraction pipeline."""
    raw_resume_skills: List[str] = field(default_factory=list)
    filtered_resume_skills: List[str] = field(default_factory=list)
    normalized_resume_skills: List[str] = field(default_factory=list)
    jd_skills_raw: List[str] = field(default_factory=list)
    jd_skills_filtered: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    preferred_skills: List[str] = field(default_factory=list)
    optional_skills: List[str] = field(default_factory=list)
    rejected_jd_phrases: List[Dict] = field(default_factory=list)
    exact_matches: List[Dict] = field(default_factory=list)
    alias_matches: List[Dict] = field(default_factory=list)
    semantic_matches: List[Dict] = field(default_factory=list)
    synonym_matches: List[Dict] = field(default_factory=list)
    partial_matches: List[Dict] = field(default_factory=list)
    rejected_matches: List[Dict] = field(default_factory=list)
    final_missing: List[str] = field(default_factory=list)
    resume_skill_source_counts: Dict[str, int] = field(default_factory=dict)
    jd_bucket_counts: Dict[str, int] = field(default_factory=dict)
    match_type_counts: Dict[str, int] = field(default_factory=dict)
    skills_score_S_sk: float = 0.0
    weighted_jd_total: float = 0.0
    weighted_match_total: float = 0.0
    weighted_jd_coverage: float = 0.0
    avg_match_confidence: float = 0.0
    resume_pool_coverage: float = 0.0
    empty_resume_sections: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def note(self, message: str) -> None:
        self.notes.append(message)

    def to_dict(self) -> Dict:
        return {
            "raw_resume_skills": list(self.raw_resume_skills),
            "filtered_resume_skills": list(self.filtered_resume_skills),
            "normalized_resume_skills": list(self.normalized_resume_skills),
            "jd_skills_raw": list(self.jd_skills_raw),
            "jd_skills_filtered": list(self.jd_skills_filtered),
            "raw_jd_skills": list(self.jd_skills_raw),
            "filtered_jd_skills": list(self.jd_skills_filtered),
            "required_skills": list(self.required_skills),
            "preferred_skills": list(self.preferred_skills),
            "optional_skills": list(self.optional_skills),
            "rejected_jd_phrases": list(self.rejected_jd_phrases),
            "exact_matches": list(self.exact_matches),
            "alias_matches": list(self.alias_matches),
            "semantic_matches": list(self.semantic_matches),
            "synonym_matches": list(self.synonym_matches),
            "partial_matches": list(self.partial_matches),
            "rejected_matches": list(self.rejected_matches),
            "final_missing": list(self.final_missing),
            "resume_skill_source_counts": dict(self.resume_skill_source_counts),
            "jd_bucket_counts": dict(self.jd_bucket_counts),
            "match_type_counts": dict(self.match_type_counts),
            "skills_score_S_sk": float(self.skills_score_S_sk),
            "weighted_jd_total": float(self.weighted_jd_total),
            "weighted_match_total": float(self.weighted_match_total),
            "weighted_jd_coverage": float(self.weighted_jd_coverage),
            "avg_match_confidence": float(self.avg_match_confidence),
            "resume_pool_coverage": float(self.resume_pool_coverage),
            "empty_resume_sections": list(self.empty_resume_sections),
            "notes": list(self.notes),
        }


# ---------------------------------------------------------------------------
# L12 — Dynamic top_n tuning (Phase 2)
# ---------------------------------------------------------------------------

def compute_optimal_top_n(text: str, requested_top_n: int = 30) -> int:
    """Scale KeyBERT top_n with text complexity (unique-word proxy)."""
    if not text or not text.strip():
        return 3
    words = text.split()
    word_count = len(words)
    unique_words = len(set(w.lower() for w in words))
    if unique_words < 20:
        optimal = 5
    elif unique_words < 50:
        optimal = 15
    else:
        optimal = min(30, unique_words // 3)
    return max(3, min(optimal, requested_top_n, max(3, word_count // 4)))


def compute_phrase_specificity_weight(phrase: str) -> float:
    """Weight JD phrases by specificity so longer phrases matter slightly more."""
    word_count = len(normalize_phrase(phrase).split())
    if word_count <= 1:
        return 1.0
    if word_count == 2:
        return 1.25
    return 1.5


def compute_weighted_skill_score(
    jd_entries: Iterable[Dict],
    matched_pairs: Iterable[Dict],
    total_resume_phrases: int,
) -> Dict:
    """Compute the root-PDF weighted skill score and compatibility metrics."""
    jd_list: List[Dict] = []
    for entry in jd_entries or []:
        phrase = normalize_skill(normalize_phrase(entry.get("phrase", "")))
        bucket = str(entry.get("bucket", "required")).strip().lower() or "required"
        if not phrase or bucket not in JD_BUCKET_WEIGHTS:
            continue
        jd_list.append({"phrase": phrase, "bucket": bucket})

    matched_list = list(matched_pairs or [])
    total_weight = round(sum(JD_BUCKET_WEIGHTS[item["bucket"]] for item in jd_list), 6)
    matched_weight = 0.0
    matched_resume_phrases = 0
    confidences: List[float] = []
    seen_resume = set()
    match_type_counts: Counter = Counter()
    bucket_counts: Counter = Counter(item["bucket"] for item in jd_list)

    unmatched_by_phrase: Counter = Counter((item["phrase"], item["bucket"]) for item in jd_list)
    for pair in matched_list:
        jd_phrase = normalize_skill(normalize_phrase(pair.get("jd_phrase", "")))
        bucket = str(pair.get("jd_bucket", "required")).strip().lower() or "required"
        key = (jd_phrase, bucket)
        if not jd_phrase or key not in unmatched_by_phrase or unmatched_by_phrase[key] <= 0:
            continue
        unmatched_by_phrase[key] -= 1
        matched_weight += JD_BUCKET_WEIGHTS.get(bucket, 1.0)
        confidences.append(max(0.0, min(float(pair.get("similarity", 0.0) or 0.0), 1.0)))
        match_type = str(pair.get("match_type", "semantic")).strip().lower() or "semantic"
        match_type_counts[match_type] += 1
        resume_phrase = normalize_skill(normalize_phrase(pair.get("resume_phrase", "")))
        if resume_phrase and resume_phrase not in seen_resume:
            seen_resume.add(resume_phrase)
            matched_resume_phrases += 1

    # avg_match_confidence: mean confidence over the MATCHED pairs only.
    # Reported for transparency (it describes the quality of matches that
    # happened) but NOT used directly in the score — see P7.1 note below.
    avg_match_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # ── P7.1 fix: coverage-weighted confidence ──────────────────────────────
    # The old score used avg_match_confidence directly, so a single perfect
    # match on a large JD produced confidence 1.0 and floored the score near
    # the 0.35 component weight regardless of how little of the JD was covered
    # (e.g. 1/29 phrases matched still scored ~0.365). Averaging the summed
    # confidences over the TOTAL JD phrase count instead (unmatched phrases
    # contribute 0 confidence) makes the confidence term scale with coverage,
    # removing the false floor.
    coverage_weighted_confidence = (
        sum(confidences) / float(len(jd_list)) if jd_list else 0.0
    )
    resume_pool_coverage = (
        matched_resume_phrases / float(total_resume_phrases)
        if total_resume_phrases > 0 else 0.0
    )
    weighted_jd_coverage = (matched_weight / total_weight) if total_weight else 0.0
    score = (
        SKILL_SCORE_COMPONENT_WEIGHTS["weighted_jd_coverage"] * weighted_jd_coverage +
        SKILL_SCORE_COMPONENT_WEIGHTS["avg_match_confidence"] * coverage_weighted_confidence +
        SKILL_SCORE_COMPONENT_WEIGHTS["resume_pool_coverage"] * resume_pool_coverage
    )

    return {
        "score": round(min(max(score, 0.0), 1.0), 4),
        "matched_count": len(matched_list),
        "total_jd_count": len(jd_list),
        "weighted_jd_total": round(total_weight, 4),
        "weighted_match_total": round(matched_weight, 4),
        "weighted_jd_coverage": round(weighted_jd_coverage, 4),
        "avg_match_confidence": round(avg_match_confidence, 4),
        "matched_resume_phrases": matched_resume_phrases,
        "total_resume_phrases": int(total_resume_phrases),
        "resume_pool_coverage": round(resume_pool_coverage, 4),
        "jd_bucket_counts": {bucket: int(bucket_counts.get(bucket, 0)) for bucket in JD_BUCKET_WEIGHTS},
        "match_type_counts": dict(match_type_counts),
        "score_component_weights": dict(SKILL_SCORE_COMPONENT_WEIGHTS),
    }


def compute_hybrid_skill_score(
    jd_phrases: Iterable[str],
    matched_pairs: Iterable[Dict],
    total_resume_phrases: int,
) -> Dict[str, float]:
    """Compute the authoritative hybrid skills score."""
    jd_list = [normalize_skill(normalize_phrase(item)) for item in jd_phrases or [] if normalize_phrase(item)]
    matched_list = list(matched_pairs or [])

    total_jd_weight = round(sum(compute_phrase_specificity_weight(item) for item in jd_list), 6)
    matched_jd_weight = 0.0
    matched_resume_phrases = 0
    confidences: List[float] = []
    seen_jd: Counter = Counter()
    seen_resume = set()

    for pair in matched_list:
        jd_phrase = normalize_skill(normalize_phrase(pair.get("jd_phrase", "")))
        resume_phrase = normalize_skill(normalize_phrase(pair.get("resume_phrase", "")))
        if not jd_phrase or jd_phrase not in jd_list:
            continue
        if seen_jd[jd_phrase] >= jd_list.count(jd_phrase):
            continue
        seen_jd[jd_phrase] += 1
        matched_jd_weight += compute_phrase_specificity_weight(jd_phrase)
        confidence = float(pair.get("similarity", 0.0) or 0.0)
        confidences.append(max(0.0, min(confidence, 1.0)))
        if resume_phrase and resume_phrase not in seen_resume:
            seen_resume.add(resume_phrase)
            matched_resume_phrases += 1

    weighted_jd_coverage = matched_jd_weight / total_jd_weight if total_jd_weight else 0.0
    avg_match_confidence = sum(confidences) / len(confidences) if confidences else 0.0
    # P7.1 fix (see compute_weighted_skill_score): coverage-weighted confidence
    # averages over total JD phrases, not matched pairs, to remove the floor.
    coverage_weighted_confidence = (
        sum(confidences) / float(len(jd_list)) if jd_list else 0.0
    )
    resume_pool_coverage = (
        matched_resume_phrases / float(total_resume_phrases)
        if total_resume_phrases > 0 else 0.0
    )
    score = (
        SKILL_SCORE_COMPONENT_WEIGHTS["weighted_jd_coverage"] * weighted_jd_coverage +
        SKILL_SCORE_COMPONENT_WEIGHTS["avg_match_confidence"] * coverage_weighted_confidence +
        SKILL_SCORE_COMPONENT_WEIGHTS["resume_pool_coverage"] * resume_pool_coverage
    )

    return {
        "score": round(min(score, 1.0), 4),
        "matched_count": len(matched_list),
        "total_jd_count": len(jd_list),
        "weighted_jd_total": round(total_jd_weight, 4),
        "weighted_match_total": round(matched_jd_weight, 4),
        "weighted_jd_coverage": round(weighted_jd_coverage, 4),
        "avg_match_confidence": round(avg_match_confidence, 4),
        "matched_resume_phrases": matched_resume_phrases,
        "total_resume_phrases": int(total_resume_phrases),
        "resume_pool_coverage": round(resume_pool_coverage, 4),
    }
