"""Skill Matcher — layered resume↔JD skill matching.

Ported from Code/app_logic.py (Stage 3: KeyBERT Skill Extraction & Matching).

Key Phase 5 refactors vs. the original:
  - Embeddings go through the Phase 4 EmbeddingProvider abstraction
    (SBERT → TF-IDF → token fallback) instead of a hard SBERT dependency.
  - KeyBERT phrase augmentation is OPTIONAL: a lazy loader returns a model
    only when 'keybert' is installed; otherwise augmentation is skipped and
    matching runs on the structured skill lists from Phases 1–4.

Matching layers (in order):
    exact → alias → synonym (map) → semantic (embedding) → partial → cluster

Threshold constants are centralized at the top of this module so the
Phase 5 optimization steps (P5.1 tighten thresholds) have a single
source of truth.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

from app.utils.embeddings import EmbeddingProvider, get_embedding_provider
from app.utils.skill_normalization import (
    DebugLog,
    clamp_match_score,
    clean_jd_skill_phrases,
    clean_skills,
    compute_adaptive_threshold,
    compute_optimal_top_n,
    compute_token_overlap_ratio,
    compute_weighted_skill_score,
    deduplicate_phrases,
    extract_skills_from_section as core_extract_skills_from_section,
    filter_non_skill_phrases_pos,
    has_technical_signal,
    is_synonym_match,
    is_valid_jd_skill,
    is_valid_skill,
    normalize_phrase,
    normalize_skill,
    normalize_text_for_skills,
    skills_share_cluster,
)

logger = logging.getLogger(__name__)


# ─── Threshold constants (single source of truth — P5.1 tunes these) ────────
#
# These are calibrated for SBERT cosine similarity (the production embedding
# backend). When the EmbeddingProvider falls back to TF-IDF/token, the
# exact/alias/synonym-map layers still work (they are backend-independent),
# but the semantic/partial layers will rarely fire — which is acceptable
# because those layers are recall boosters, not the primary match source.

DEFAULT_MATCH_THRESHOLD = 0.75   # legacy fallback; adaptive thresholds used per-pair
EMBEDDED_SYNONYM_THRESHOLD = 0.84  # cosine ≥ this → treat as synonym-grade match

# ── P5.1 threshold tightening (reduce false positives) ──────────────────────
# Rationale: the partial layer was firing on a single shared common token.
# Example false positive observed on real data:
#   "deep learning" ↔ "learning frameworks"  (token overlap = 1/2 = 0.50)
# Raising the token-overlap floor to 0.60 rejects 1-of-2 token overlaps while
# still accepting genuine subset overlaps like
#   "machine learning" ↔ "machine learning models"  (2/3 = 0.667).
SEMANTIC_PARTIAL_FLOOR = 0.45    # was 0.40 — cosine ≥ this (below adaptive) → partial
PARTIAL_TOKEN_OVERLAP_FLOOR = 0.60  # was 0.50 — token overlap ≥ this → partial
# The cluster-share branch is the loosest matcher (any two skills in the same
# ontology cluster). Require a minimum embedding similarity so semantically
# distant same-cluster skills (e.g. "redis" vs "sql") don't auto-match.
CLUSTER_MIN_SIMILARITY = 0.30

MIN_KEYBERT_SCORE = 0.3
DEFAULT_TOP_N = 30


# ── Sub-phase 1.8 — LLM validation gate constants ──────────────────────────
# The LLM validation tier filters borderline matches in the semantic + partial
# bands where the deterministic matcher's precision is weakest. Other tiers
# (exact, alias, synonym) are NEVER gated — they're high-confidence by
# construction. Constants below are env-overridable so the gate can be tuned
# without code changes.
import os as _os

LLM_VALIDATE_LOW = float(_os.environ.get("TALENTALIGN_LLM_VALIDATE_LOW", "0.45"))
LLM_VALIDATE_HIGH = float(_os.environ.get("TALENTALIGN_LLM_VALIDATE_HIGH", "0.75"))
LLM_VALIDATE_TIERS = tuple(
    _os.environ.get("TALENTALIGN_LLM_VALIDATE_TIERS", "semantic,partial").split(",")
)
# A borderline match is only DROPPED when the LLM rejects it with confidence
# at or above this threshold. Kept as a tunable knob, but defaults to 0.0
# (pure binary decision) because qwen3:8b's self-reported confidence proved
# to be a poor discriminator on the gold set: correctly-rejected false
# positives spanned conf 0.1–0.6, overlapping the wrongly-rejected true
# matches (0.2 / 0.4). Recall is instead protected by the prompt's
# specific-technique directionality rule (see _run_llm_validation_gate).
LLM_REJECT_CONFIDENCE = float(_os.environ.get("TALENTALIGN_LLM_REJECT_CONFIDENCE", "0.0"))


# ─── KeyBERT (optional, lazy) ────────────────────────────────────────────────

_keybert_model = None
_KEYBERT_AVAILABLE: Optional[bool] = None


def get_keybert_model():
    """Lazy-load a KeyBERT model. Returns None if keybert is unavailable.

    Follows the spaCy/SBERT graceful-degradation pattern: a missing
    dependency disables augmentation rather than crashing the pipeline.
    """
    global _keybert_model, _KEYBERT_AVAILABLE
    if _KEYBERT_AVAILABLE is not None:
        return _keybert_model
    try:
        from keybert import KeyBERT  # type: ignore
        from sentence_transformers import SentenceTransformer  # type: ignore
        sbert = SentenceTransformer("all-MiniLM-L6-v2")
        _keybert_model = KeyBERT(model=sbert)
        _KEYBERT_AVAILABLE = True
        logger.info("KeyBERT loaded — JD phrase augmentation enabled.")
    except Exception as exc:
        _KEYBERT_AVAILABLE = False
        _keybert_model = None
        logger.info("KeyBERT unavailable (%s) — phrase augmentation disabled.", exc)
    return _keybert_model


# ─── KeyBERT phrase extraction ───────────────────────────────────────────────


def extract_skill_phrases(text: str, kw=None, top_n: int = DEFAULT_TOP_N) -> List[Tuple[str, float]]:
    """Extract skill phrases using KeyBERT (graceful no-op if kw is None).

    Phase 2 (L12): dynamic top_n scaling. Phase 2 (L4): POS filtering.
    """
    if not text or not text.strip():
        return []
    if kw is None:
        kw = get_keybert_model()
    if kw is None:
        return []  # KeyBERT unavailable → no augmentation
    effective_top_n = compute_optimal_top_n(text, top_n)
    keywords = kw.extract_keywords(
        text, keyphrase_ngram_range=(1, 2), stop_words="english",
        top_n=effective_top_n, use_mmr=True, diversity=0.3,
    )
    filtered = []
    for phrase, score in keywords:
        np_ = normalize_phrase(phrase)
        if not np_ or score < MIN_KEYBERT_SCORE:
            continue
        if not is_valid_skill(np_):
            continue
        np_ = normalize_skill(np_)
        filtered.append((np_, float(score)))
    phrase_list = [p for p, _ in filtered]
    kept_phrases = set(filter_non_skill_phrases_pos(phrase_list))
    filtered = [(p, s) for p, s in filtered if p in kept_phrases]
    return filtered


# ─── JD skill entry building ─────────────────────────────────────────────────

_LEADING_SKILL_VERB_RE = re.compile(
    r"^(?:perform|build|develop|create|write|use|using|manage|support|assist|"
    r"conduct|work with|working with|clean|process|analyze|analyse|implement)\s+"
)


def _normalize_jd_skill_candidate(phrase: str) -> str:
    """Normalize JD skill phrases and remove leading action verbs."""
    candidate = normalize_phrase(phrase)
    previous = None
    while candidate and candidate != previous:
        previous = candidate
        candidate = _LEADING_SKILL_VERB_RE.sub("", candidate).strip()
    return normalize_skill(candidate)


def _decompose_compound_phrases(jd_entries: List[Dict]) -> List[Dict]:
    """Split compound JD phrases into constituent skills for better matching."""
    expanded = list(jd_entries)
    seen = {entry["phrase"] for entry in expanded}
    for entry in list(jd_entries):
        phrase = entry.get("phrase", "")
        words = phrase.split()
        if len(words) < 3:
            continue
        candidates = []
        for i in range(1, len(words)):
            candidates.extend((" ".join(words[:i]), " ".join(words[i:])))
        for sub_phrase in candidates:
            sub = _normalize_jd_skill_candidate(sub_phrase)
            if len(sub) < 3 or sub in seen:
                continue
            if is_valid_jd_skill(sub):
                expanded.append({
                    "phrase": sub, "bucket": entry.get("bucket", "optional"),
                    "derived": True, "parent": phrase,
                })
                seen.add(sub)
    return expanded


def build_jd_skill_entries(parsed_jd: Dict, kw=None, top_n: int = DEFAULT_TOP_N) -> List[Dict]:
    """Build ordered JD skill entries with explicit bucket metadata.

    If kw is None, attempts to lazy-load KeyBERT; if that fails, augmentation
    is skipped and entries come purely from the structured skill buckets.
    """
    entries: List[Dict] = []
    seen = set()
    for bucket in ("required", "preferred", "optional"):
        for skill in parsed_jd.get(f"{bucket}_skills", []):
            phrase = _normalize_jd_skill_candidate(skill)
            if not phrase or not is_valid_jd_skill(phrase) or phrase in seen:
                continue
            entries.append({"phrase": phrase, "bucket": bucket})
            seen.add(phrase)

    if kw is None:
        kw = get_keybert_model()
    if kw is not None:
        jd_text = normalize_text_for_skills(parsed_jd.get("raw_text", ""))
        optional_added = 0
        optional_limit = min(12, max(6, top_n // 3 if top_n else 6))
        for phrase, _score in extract_skill_phrases(jd_text, kw, top_n):
            canonical = _normalize_jd_skill_candidate(phrase)
            if (
                not canonical or
                not is_valid_jd_skill(canonical) or
                not has_technical_signal(canonical) or
                canonical in seen
            ):
                continue
            entries.append({"phrase": canonical, "bucket": "optional"})
            seen.add(canonical)
            optional_added += 1
            if optional_added >= optional_limit:
                break
    return _decompose_compound_phrases(entries)


def extract_jd_skill_phrases(parsed_jd: Dict, kw=None, top_n: int = DEFAULT_TOP_N) -> List[str]:
    """Backward-compatible wrapper returning only the JD phrases."""
    return [entry["phrase"] for entry in build_jd_skill_entries(parsed_jd, kw=kw, top_n=top_n)]


# ─── Match-pair construction ─────────────────────────────────────────────────


def _infer_exact_match_type(resume_phrase: str, jd_phrase: str) -> str:
    resume_raw = normalize_phrase(resume_phrase)
    jd_raw = normalize_phrase(jd_phrase)
    if resume_raw == jd_raw:
        return "exact"
    if normalize_skill(resume_raw) == normalize_skill(jd_raw):
        return "alias"
    return "exact"


def _build_match_pair(
    resume_phrase: str,
    jd_phrase: str,
    jd_bucket: str,
    similarity: float,
    match_type: str,
    token_overlap: float = 0.0,
) -> Dict:
    base_score = max(float(similarity or 0.0), float(token_overlap or 0.0))
    return {
        "resume_phrase": resume_phrase,
        "jd_phrase": jd_phrase,
        "jd_bucket": jd_bucket,
        "similarity": round(float(similarity or 0.0), 4),
        "token_overlap": round(float(token_overlap or 0.0), 4),
        "match_type": match_type,
        "match_score": clamp_match_score(match_type, base_score),
    }


# ─── Core matcher ────────────────────────────────────────────────────────────


def match_skills(
    resume_phrases: List[str],
    jd_entries: List[Dict],
    provider: Optional[EmbeddingProvider] = None,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    debug: Optional[DebugLog] = None,
    llm_provider: Optional[object] = None,
) -> Dict:
    """Layered matching: exact → alias → synonym → semantic → partial → cluster.

    Args:
        resume_phrases: normalized resume skill phrases.
        jd_entries: list of {"phrase", "bucket"} dicts.
        provider: EmbeddingProvider for the semantic layer. Defaults to the
            process-wide provider (SBERT → TF-IDF → token).
        threshold: legacy default threshold (adaptive thresholds used per-pair).
        debug: optional DebugLog to accumulate match evidence.
        llm_provider: Optional LLMProvider (sub-phase 1.10). When provided,
            borderline matches in tiers LLM_VALIDATE_TIERS with similarity in
            [LLM_VALIDATE_LOW, LLM_VALIDATE_HIGH] are sent to the LLM in one
            batched call. Rejected pairs are removed from `matched` and added
            back to `unmatched_in_resume` / `missing_from_resume`. When None
            (default), behavior is byte-identical to the no-LLM baseline.
    """
    provider = provider or get_embedding_provider()

    jd_entries = [
        {
            "phrase": normalize_skill(normalize_phrase(item.get("phrase", ""))),
            "bucket": str(item.get("bucket", "required")).strip().lower() or "required",
        }
        for item in (jd_entries or [])
        if normalize_phrase(item.get("phrase", ""))
    ]
    jd_entries = [item for item in jd_entries if item["phrase"]]
    jd_phrases = [item["phrase"] for item in jd_entries]
    if not resume_phrases or not jd_phrases:
        return {
            "matched": [],
            "unmatched_in_resume": list(resume_phrases),
            "missing_from_resume": list(jd_phrases),
        }

    matched, used_r, used_j = [], set(), set()
    jd_order = sorted(range(len(jd_entries)), key=lambda i: len(jd_entries[i]["phrase"].split()), reverse=True)
    jd_entries = [jd_entries[i] for i in jd_order]
    jd_phrases = [item["phrase"] for item in jd_entries]

    resume_norm = [normalize_skill(normalize_phrase(p)) for p in resume_phrases]
    jd_norm = [normalize_skill(normalize_phrase(p)) for p in jd_phrases]

    # Layer 1: exact / alias
    for j_idx, jp_norm in enumerate(jd_norm):
        for r_idx, rp_norm in enumerate(resume_norm):
            if r_idx in used_r or j_idx in used_j:
                continue
            if rp_norm == jp_norm:
                match_type = _infer_exact_match_type(resume_phrases[r_idx], jd_phrases[j_idx])
                pair = _build_match_pair(
                    resume_phrases[r_idx],
                    jd_phrases[j_idx],
                    jd_entries[j_idx]["bucket"],
                    1.0,
                    match_type,
                )
                matched.append(pair)
                if debug is not None:
                    if match_type == "alias":
                        debug.alias_matches.append(pair)
                    else:
                        debug.exact_matches.append(pair)
                used_r.add(r_idx)
                used_j.add(j_idx)
                break

    # Layer 2: synonym map
    for j_idx, jp in enumerate(jd_phrases):
        if j_idx in used_j:
            continue
        for r_idx, rp in enumerate(resume_phrases):
            if r_idx in used_r:
                continue
            if is_synonym_match(rp, jp):
                pair = _build_match_pair(rp, jp, jd_entries[j_idx]["bucket"], 0.9, "synonym")
                matched.append(pair)
                if debug is not None:
                    debug.synonym_matches.append(pair)
                used_r.add(r_idx)
                used_j.add(j_idx)
                break

    # Layers 3-5: semantic / partial / cluster (embedding-based)
    remaining_r = [i for i in range(len(resume_phrases)) if i not in used_r]
    remaining_j = [i for i in range(len(jd_phrases)) if i not in used_j]
    if remaining_r and remaining_j:
        r_texts = [resume_phrases[i] for i in remaining_r]
        j_texts = [jd_phrases[i] for i in remaining_j]
        resume_emb, jd_emb = provider.encode_pair(r_texts, j_texts)
        cosine_scores = provider.cosine_similarity(resume_emb, jd_emb)
        candidate_pairs = []
        partial_candidates = []
        for ri, r_idx in enumerate(remaining_r):
            for ji, j_idx in enumerate(remaining_j):
                sim = float(cosine_scores[ri][ji])
                adaptive_thr = compute_adaptive_threshold(jd_phrases[j_idx])
                token_overlap = compute_token_overlap_ratio(resume_phrases[r_idx], jd_phrases[j_idx])
                if sim >= EMBEDDED_SYNONYM_THRESHOLD:
                    candidate_pairs.append((
                        2.0 + sim, "synonym", sim, r_idx, j_idx,
                        resume_phrases[r_idx], jd_phrases[j_idx], token_overlap,
                    ))
                elif sim >= adaptive_thr:
                    candidate_pairs.append((
                        1.0 + sim, "semantic", sim, r_idx, j_idx,
                        resume_phrases[r_idx], jd_phrases[j_idx], token_overlap,
                    ))
                elif sim >= SEMANTIC_PARTIAL_FLOOR or token_overlap >= PARTIAL_TOKEN_OVERLAP_FLOOR:
                    partial_candidates.append((
                        max(sim, token_overlap), sim, token_overlap, r_idx, j_idx,
                        resume_phrases[r_idx], jd_phrases[j_idx],
                    ))
                elif sim >= CLUSTER_MIN_SIMILARITY and skills_share_cluster(
                    resume_phrases[r_idx], jd_phrases[j_idx]
                ):
                    partial_candidates.append((
                        0.4, max(sim, 0.35), max(token_overlap, 0.4), r_idx, j_idx,
                        resume_phrases[r_idx], jd_phrases[j_idx],
                    ))
                elif debug is not None:
                    debug.rejected_matches.append({
                        "resume_phrase": resume_phrases[r_idx],
                        "jd_phrase": jd_phrases[j_idx],
                        "similarity": round(sim, 4),
                        "token_overlap": round(token_overlap, 4),
                        "threshold_used": adaptive_thr,
                    })
        candidate_pairs.sort(reverse=True)
        for _priority, candidate_type, sim, r_idx, j_idx, rp, jp, token_overlap in candidate_pairs:
            if r_idx in used_r or j_idx in used_j:
                continue
            pair = _build_match_pair(
                rp, jp, jd_entries[j_idx]["bucket"],
                sim if candidate_type == "semantic" else 0.9,
                candidate_type, token_overlap=token_overlap,
            )
            matched.append(pair)
            if debug is not None:
                if candidate_type == "synonym":
                    debug.synonym_matches.append(pair)
                else:
                    debug.semantic_matches.append(pair)
            used_r.add(r_idx)
            used_j.add(j_idx)

        partial_candidates.sort(reverse=True)
        for _rank, sim, token_overlap, r_idx, j_idx, rp, jp in partial_candidates:
            if r_idx in used_r or j_idx in used_j:
                continue
            pair = _build_match_pair(
                rp, jp, jd_entries[j_idx]["bucket"], sim, "partial",
                token_overlap=token_overlap,
            )
            matched.append(pair)
            if debug is not None:
                debug.partial_matches.append(pair)
            used_r.add(r_idx)
            used_j.add(j_idx)

    # ── Sub-phase 1.10 — LLM validation gate ───────────────────────────────
    # Borderline matches (in LLM_VALIDATE_TIERS + similarity within band) are
    # routed through the LLM. Rejected pairs are dropped from `matched` and
    # their indices freed so the corresponding phrases become unmatched/missing.
    llm_validation: Optional[Dict] = None
    if llm_provider is not None:
        llm_validation, matched, used_r, used_j = _run_llm_validation_gate(
            matched=matched,
            resume_phrases=resume_phrases,
            jd_phrases=jd_phrases,
            used_r=used_r,
            used_j=used_j,
            llm_provider=llm_provider,
        )

    unmatched = [resume_phrases[i] for i in range(len(resume_phrases)) if i not in used_r]
    missing = [jd_phrases[i] for i in range(len(jd_phrases)) if i not in used_j]
    if debug is not None:
        debug.final_missing = list(missing)
        debug.match_type_counts = {
            key: len(value)
            for key, value in {
                "exact": debug.exact_matches,
                "alias": debug.alias_matches,
                "synonym": debug.synonym_matches,
                "semantic": debug.semantic_matches,
                "partial": debug.partial_matches,
            }.items()
            if value
        }
    result = {
        "matched": matched,
        "unmatched_in_resume": unmatched,
        "missing_from_resume": missing,
    }
    if llm_validation is not None:
        result["llm_validation"] = llm_validation
    return result


# ─── Sub-phase 1.10 — LLM validation helper ─────────────────────────────────


def _run_llm_validation_gate(
    *,
    matched: List[Dict],
    resume_phrases: List[str],
    jd_phrases: List[str],
    used_r: set,
    used_j: set,
    llm_provider,
):
    """Validate borderline matches via the LLM. One batched call per analysis.

    For every pair in ``matched`` whose ``match_type`` is in
    ``LLM_VALIDATE_TIERS`` and similarity falls within
    ``[LLM_VALIDATE_LOW, LLM_VALIDATE_HIGH]``, ask the LLM "is this a real
    skill match?". Pairs the LLM rejects are removed from ``matched`` and
    their resume/jd indices freed.

    Returns (llm_validation_payload, new_matched, new_used_r, new_used_j).

    Failure modes (all return matched UNCHANGED and populate skipped_reason
    so callers can see why):
      - llm_provider returned None for the batched request (no_provider /
        cost_cap / timeout / schema_failure / transport_error)
      - no borderline pairs to validate (returns kept=[], rejected=[],
        skipped_reason=None)
    """
    # Local import to avoid circular dependency on llm_schemas at module load.
    from app.utils.llm import (
        LLMRequest,
        SKIP_COST_CAP,
        SKIP_NO_PROVIDER,
        SKIP_SCHEMA_FAILURE,
        SKIP_TIMEOUT,
        SKIP_TRANSPORT_ERROR,
    )
    from app.utils.llm_schemas import MatchValidation

    # Identify borderline pairs.
    borderline_indices: List[int] = []
    for i, m in enumerate(matched):
        if m.get("match_type") not in LLM_VALIDATE_TIERS:
            continue
        sim = float(m.get("similarity", 0.0) or 0.0)
        if LLM_VALIDATE_LOW <= sim <= LLM_VALIDATE_HIGH:
            borderline_indices.append(i)

    if not borderline_indices:
        # Nothing to validate — gate is inert but reported for transparency.
        return (
            {"kept": [], "rejected": [], "skipped_reason": None,
             "candidate_count": 0, "tiers": list(LLM_VALIDATE_TIERS),
             "band": [LLM_VALIDATE_LOW, LLM_VALIDATE_HIGH]},
            matched, used_r, used_j,
        )

    # Build one batched LLM request — all pairs in one user message,
    # one response with one MatchValidationItem per pair_id.
    pairs_payload = []
    for ord_i, mi in enumerate(borderline_indices):
        m = matched[mi]
        pairs_payload.append({
            "pair_id": f"p{ord_i}",
            "resume_skill": m["resume_phrase"],
            "jd_skill": m["jd_phrase"],
            "current_similarity": round(float(m.get("similarity", 0.0) or 0.0), 4),
            "current_match_type": m.get("match_type", ""),
        })

    system_prompt = (
        "You validate whether a candidate's skill genuinely matches a "
        "job-description requirement.\n\n"
        "Return is_valid_match=true if the candidate's skill is the same skill, "
        "a clear alias/synonym, or a specific technique/tool that falls under "
        "the JD requirement's area.\n\n"
        "Return is_valid_match=false when the two phrases share only a generic "
        "word ('model', 'data', 'system', 'methods', 'tools'), are in different "
        "domains, or are too tangentially related to count as a real match.\n\n"
        "Be strict — false positives are worse than false negatives here. "
        "If unsure, return false with low confidence."
    )
    user_prompt = (
        "Validate each pair below. Return one item per pair_id in the same order.\n\n"
        f"{_json_dumps(pairs_payload)}"
    )

    req = LLMRequest(system=system_prompt, user=user_prompt, schema=MatchValidation)
    responses = llm_provider.batch_complete_json([req])
    response: Optional[MatchValidation] = responses[0] if responses else None

    if response is None:
        # Look up why it was skipped (most-recent skip reason wins).
        skip_reason = None
        if hasattr(llm_provider, "usage") and llm_provider.usage is not None:
            skipped = llm_provider.usage.skipped
            for reason in (
                SKIP_NO_PROVIDER, SKIP_COST_CAP, SKIP_TIMEOUT,
                SKIP_SCHEMA_FAILURE, SKIP_TRANSPORT_ERROR,
            ):
                if skipped.get(reason, 0) > 0:
                    skip_reason = reason
                    break
        return (
            {"kept": [], "rejected": [], "skipped_reason": skip_reason,
             "candidate_count": len(borderline_indices),
             "tiers": list(LLM_VALIDATE_TIERS),
             "band": [LLM_VALIDATE_LOW, LLM_VALIDATE_HIGH]},
            matched, used_r, used_j,
        )

    # Align response items by pair_id; missing items default to "kept"
    # (benefit of the doubt — we don't want a malformed item to silently
    # drop a real match).
    verdicts = {item.pair_id: item for item in response.items}

    kept_records: List[Dict] = []
    rejected_records: List[Dict] = []
    rejected_indices: set = set()
    for ord_i, mi in enumerate(borderline_indices):
        pair_id = f"p{ord_i}"
        verdict = verdicts.get(pair_id)
        m = matched[mi]
        if verdict is None:
            # Treat missing verdict as "keep" — safer default.
            kept_records.append({
                "resume_phrase": m["resume_phrase"],
                "jd_phrase": m["jd_phrase"],
                "confidence": None,
                "reason": "no verdict returned by LLM (kept by default)",
            })
            continue
        record = {
            "resume_phrase": m["resume_phrase"],
            "jd_phrase": m["jd_phrase"],
            "confidence": round(float(verdict.confidence), 4),
            "reason": verdict.reason,
        }
        # Drop ONLY on a confident rejection. A low-confidence "invalid"
        # verdict means the LLM is unsure — keep the match to protect recall.
        if (not verdict.is_valid_match) and float(verdict.confidence) >= LLM_REJECT_CONFIDENCE:
            rejected_records.append(record)
            rejected_indices.add(mi)
        else:
            if not verdict.is_valid_match:
                record["kept_despite_low_confidence_reject"] = True
            kept_records.append(record)

    # Free indices used by rejected pairs and rebuild matched list.
    new_matched = [m for i, m in enumerate(matched) if i not in rejected_indices]

    # Recompute used_r/used_j from surviving matches. Pairs reject → resume
    # phrase becomes unmatched, JD phrase becomes missing.
    new_used_r: set = set()
    new_used_j: set = set()
    for m in new_matched:
        try:
            new_used_r.add(resume_phrases.index(m["resume_phrase"]))
        except ValueError:
            pass
        try:
            new_used_j.add(jd_phrases.index(m["jd_phrase"]))
        except ValueError:
            pass

    payload = {
        "kept": kept_records,
        "rejected": rejected_records,
        "skipped_reason": None,
        "candidate_count": len(borderline_indices),
        "tiers": list(LLM_VALIDATE_TIERS),
        "band": [LLM_VALIDATE_LOW, LLM_VALIDATE_HIGH],
    }
    return payload, new_matched, new_used_r, new_used_j


def _json_dumps(obj) -> str:
    """Small wrapper so the import stays local to the helper above."""
    import json
    return json.dumps(obj, indent=2)


# ─── Missing-skill consolidation ─────────────────────────────────────────────


def _consolidate_missing_skills(phrases: List[str]) -> List[str]:
    """Remove phrases that are sub-phrases or token-subsets of others."""
    if not phrases:
        return []
    ordered = sorted(phrases, key=lambda p: len(p.split()), reverse=True)
    kept: List[str] = []
    for phrase in ordered:
        tokens = set(phrase.split())
        redundant = False
        for existing in kept:
            existing_tokens = set(existing.split())
            if phrase in existing or tokens <= existing_tokens:
                redundant = True
                break
        if not redundant:
            kept.append(phrase)
    # Preserve original order
    order_index = {p: i for i, p in enumerate(phrases)}
    return sorted(kept, key=lambda p: order_index.get(p, 0))


def _collapse_derived_matches(jd_entries: List[Dict], matched: List[Dict]):
    """Treat decomposed sub-phrase fragments as matching aids only.

    A fragment match is credited to its parent skill, and scoring/missing are
    reported against the original (non-derived) JD requirements — so fragments
    neither inflate the coverage denominator nor surface as phantom missing
    skills. Returns (counted_entries, remapped_matched, missing_phrases).
    """
    parent_of: Dict[str, str] = {}
    for e in jd_entries:
        if e.get("derived") and e.get("parent"):
            parent_of[normalize_skill(normalize_phrase(e["phrase"]))] = e["parent"]
    counted_entries = [e for e in jd_entries if not e.get("derived")]
    counted_norm = {normalize_skill(normalize_phrase(e["phrase"])) for e in counted_entries}

    remapped: List[Dict] = []
    credited: set = set()
    for pair in matched:
        jp = normalize_skill(normalize_phrase(pair.get("jd_phrase", "")))
        if jp in parent_of:
            parent = parent_of[jp]
            jp = normalize_skill(normalize_phrase(parent))
            pair = {**pair, "jd_phrase": parent}
        if jp not in counted_norm or jp in credited:
            continue
        credited.add(jp)
        remapped.append(pair)
    missing = [
        e["phrase"] for e in counted_entries
        if normalize_skill(normalize_phrase(e["phrase"])) not in credited
    ]
    return counted_entries, remapped, missing


# ─── End-to-end pipeline ─────────────────────────────────────────────────────


def run_skill_extraction_pipeline(
    parsed_resume: Dict,
    parsed_jd: Dict,
    kw=None,
    provider: Optional[EmbeddingProvider] = None,
    top_n: int = DEFAULT_TOP_N,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    debug: Optional[DebugLog] = None,
) -> Dict:
    """Run the full skill extraction and matching pipeline.

    Args mirror the original, except `sbert` is replaced by an optional
    EmbeddingProvider and `kw` (KeyBERT) is optional.
    """
    provider = provider or get_embedding_provider()

    source_map = parsed_resume.get("_skill_sources") or {
        "skills": parsed_resume.get("skills", []),
        "cert_derived": parsed_resume.get("cert_derived_skills", []),
        "projects": core_extract_skills_from_section(parsed_resume.get("projects", [])),
        "internships": core_extract_skills_from_section(parsed_resume.get("internships", [])),
        "work_experience": core_extract_skills_from_section(parsed_resume.get("work_experience", [])),
        "fallback_full_text": [],
    }

    raw_input = []
    source_counts = {}
    for source_name in (
        "skills", "cert_derived", "projects", "internships",
        "work_experience", "fallback_full_text",
    ):
        source_skills = list(source_map.get(source_name, []))
        source_counts[source_name] = len(source_skills)
        raw_input.extend(source_skills)

    resume_source_skills = clean_skills(deduplicate_phrases(raw_input), cap=None)
    if debug is not None:
        debug.filtered_resume_skills = list(resume_source_skills)
        debug.raw_resume_skills = list(raw_input)
        debug.resume_skill_source_counts = dict(source_counts)
        debug.empty_resume_sections = list(parsed_resume.get("_empty_sections", []))
        if parsed_resume.get("_empty_sections"):
            debug.note(f"Empty resume sections: {', '.join(parsed_resume['_empty_sections'])}")
        if source_counts.get("fallback_full_text", 0) > 0:
            debug.note("Full-text fallback skill extraction was applied.")
    resume_skills_text = ", ".join(resume_source_skills)

    jd_entries = build_jd_skill_entries(parsed_jd, kw=kw, top_n=top_n)
    raw_jd_phrases = [entry["phrase"] for entry in jd_entries]
    if debug is not None:
        debug.jd_skills_raw = list(raw_jd_phrases)
        debug.required_skills = list(parsed_jd.get("required_skills", []))
        debug.preferred_skills = list(parsed_jd.get("preferred_skills", []))
        debug.optional_skills = list(parsed_jd.get("optional_skills", []))
        debug.rejected_jd_phrases = list(parsed_jd.get("_rejected_skill_candidates", []))
    jd_phrases = deduplicate_phrases(clean_jd_skill_phrases(raw_jd_phrases, cap=60))
    if debug is not None:
        debug.jd_skills_filtered = list(jd_phrases)

    resume_keyword_results = extract_skill_phrases(
        normalize_text_for_skills(resume_skills_text), kw, top_n
    )
    resume_keybert_phrases = [p for p, s in resume_keyword_results]
    resume_phrases = deduplicate_phrases(resume_source_skills + resume_keybert_phrases)
    if debug is not None:
        debug.normalized_resume_skills = list(resume_phrases)

    match_result = match_skills(resume_phrases, jd_entries, provider, threshold, debug=debug)
    # Derived sub-phrase fragments are matching aids only: credit fragment
    # matches to their parent and score/report against the original requirements.
    counted_entries, remapped_matched, computed_missing = _collapse_derived_matches(
        jd_entries, match_result["matched"]
    )
    match_result["matched"] = remapped_matched
    skills_detail = compute_weighted_skill_score(
        jd_entries=counted_entries,
        matched_pairs=remapped_matched,
        total_resume_phrases=len(resume_phrases),
    )
    if debug is not None:
        debug.jd_bucket_counts = dict(skills_detail.get("jd_bucket_counts", {}))
        debug.match_type_counts = dict(skills_detail.get("match_type_counts", {}))
        debug.skills_score_S_sk = float(skills_detail.get("score", 0.0))
        debug.weighted_jd_total = float(skills_detail.get("weighted_jd_total", 0.0))
        debug.weighted_match_total = float(skills_detail.get("weighted_match_total", 0.0))
        debug.weighted_jd_coverage = float(skills_detail.get("weighted_jd_coverage", 0.0))
        debug.avg_match_confidence = float(skills_detail.get("avg_match_confidence", 0.0))
        debug.resume_pool_coverage = float(skills_detail.get("resume_pool_coverage", 0.0))

    # Post-match consolidation of missing skills (over the original requirements
    # only — derived fragments were already collapsed out above).
    valid_missing = [m for m in computed_missing if is_valid_jd_skill(m) and len(m.split()) <= 3]
    deduped_missing = deduplicate_phrases(valid_missing)
    consolidated_missing = _consolidate_missing_skills(deduped_missing)
    match_result["missing_from_resume"] = consolidated_missing[:12]

    return {
        "resume_skill_phrases": resume_phrases,
        "jd_skill_phrases": jd_phrases,
        "jd_skill_entries": counted_entries,
        "matched": match_result["matched"],
        "unmatched_in_resume": match_result["unmatched_in_resume"],
        "missing_from_resume": match_result["missing_from_resume"],
        "summary": {
            "total_resume_phrases": len(resume_phrases),
            "total_jd_phrases": skills_detail["total_jd_count"],
            "total_matched": skills_detail["matched_count"],
            "total_missing": len(match_result["missing_from_resume"]),
            "skills_score_S_sk": skills_detail["score"],
            "match_threshold_used": threshold,
            "weighted_jd_total": skills_detail["weighted_jd_total"],
            "weighted_match_total": skills_detail["weighted_match_total"],
            "weighted_jd_coverage": skills_detail["weighted_jd_coverage"],
            "avg_match_confidence": skills_detail["avg_match_confidence"],
            "resume_pool_coverage": skills_detail["resume_pool_coverage"],
            "matched_resume_phrases": skills_detail["matched_resume_phrases"],
            "resume_skill_source_counts": source_counts,
            "jd_bucket_counts": skills_detail.get("jd_bucket_counts", {}),
            "match_type_counts": skills_detail.get("match_type_counts", {}),
            "score_component_weights": skills_detail.get("score_component_weights", {}),
            "embedding_backend": provider.backend,
        },
    }
