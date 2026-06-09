"""Project Relevance Engine — Phase 4 orchestrator.

Evaluates each candidate project against the JD across four axes:
  - similarity        — embedding-based cosine similarity (SBERT or TF-IDF)
  - complexity        — heuristic tier counts with JD-driven weighting
  - impact            — numeric/outcome-verb signal count (objective)
  - domain_alignment  — tech-stack ∩ JD-skill set overlap

Each project gets a `final_score` (weighted blend) and a `rank`. The
output object also surfaces best/average scores and aggregate signals.

Pipeline (matches the plan's Section 7 execution flow):
    Project Extraction
    → Tech Stack Extraction
    → Embedding Generation
    → JD Embedding Generation
    → Similarity Calculation
    → Complexity Scoring
    → Impact Scoring
    → Ranking
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Set

from app.utils.embeddings import EmbeddingProvider, get_embedding_provider
from app.utils.project_extraction import (
    COMPLEXITY_TIERS,
    ProjectExtraction,
    extract_project,
)
from app.utils.skill_normalization import normalize_skill, normalize_phrase


# A bullet marker at the start of a line indicates a continuation of the
# preceding project, not a new one. Pre-normalization (Phase 1 text_cleaning)
# converts Unicode bullets to "- " so this list is intentionally short.
_BULLET_MARKERS = ("-", "*", "•", "●", "▪", "■")

# Recognizes lines that introduce a tech stack rather than a new project:
# "Tech: ...", "Tech Stack: ...", "Technologies: ...", "Tools: ...", "Stack: ..."
_TECH_STACK_PREFIX_RE = re.compile(
    r"^\s*(?:tech\s*stack|technologies|tech|tools|stack)\s*[:|\-]",
    re.IGNORECASE,
)


_TITLE_LINK_MARKER_RE = re.compile(r"\((?:link|url|github|repo|code)\)", re.IGNORECASE)
_TITLE_SEPARATOR_RE = re.compile(r"\s[-—|]\s")
_TITLE_STOPWORDS = {
    "a", "an", "and", "of", "the", "to", "for", "with", "in", "on", "at",
    "by", "or", "as", "is", "via",
}


def _looks_like_real_title(line: str) -> bool:
    """Discriminate real project titles from PDF-wrap continuation fragments.

    A real title is signaled by at least one of:
      - A title/description separator (" - ", " — ", " | ")
      - A parenthesized link marker ("(LINK)", "(URL)", "(GitHub)")
      - Title Case across most non-stopword words

    Continuation fragments (e.g. "classification-ready format" — a
    sentence wrapped onto a new line from the bullet above) typically
    start with lowercase letters and don't carry these markers.
    """
    if _TITLE_SEPARATOR_RE.search(line):
        return True
    if _TITLE_LINK_MARKER_RE.search(line):
        return True
    words = line.split()
    if not words:
        return False
    if not words[0][0].isupper():
        return False
    # 1-2 word title (e.g. "VERA", "Personal Blog") — accept if uppercase-starting
    if len(words) <= 2:
        return True
    # 3+ words: most non-stopword tokens must be Title-Cased.
    significant = [w for w in words if w.lower().strip(".,;:()") not in _TITLE_STOPWORDS]
    if not significant:
        return False
    title_cased = sum(1 for w in significant if w[0].isupper())
    return title_cased / len(significant) >= 0.7


def _is_title_line(line: str) -> bool:
    """Heuristic: does this line look like a project title (not a bullet)?

    A title-like line:
      - Has content on its first physical line (multi-line entries supported)
      - Doesn't start with a bullet marker
      - Doesn't start with a tech-stack prefix
      - Is reasonably short (≤ 14 words on the first line)
      - Has at least one alphabetic character
      - Passes _looks_like_real_title (separator / link / Title Case)
    """
    stripped = line.strip()
    if not stripped:
        return False
    # For multi-line strings (e.g. test fixtures), only inspect the first line.
    first_line = stripped.split("\n", 1)[0].strip()
    if not first_line:
        return False
    if first_line[0] in _BULLET_MARKERS:
        return False
    if _TECH_STACK_PREFIX_RE.match(first_line):
        return False
    if len(first_line.split()) > 14:
        return False
    if not any(c.isalpha() for c in first_line):
        return False
    return _looks_like_real_title(first_line)


def _group_project_lines(entries: List[str]) -> List[str]:
    """Group flat resume-project lines into coherent project blocks.

    resume_parser returns each line of the Projects section as its own
    entry. A real "project" is usually a title line followed by several
    bullet lines and an optional tech-stack line. This helper detects
    title lines and concatenates the bullets/tech lines that follow them.

    Conservative behavior: if NO title-like line is detected anywhere,
    we treat each entry as its own project (preserves backward-compat
    with pre-grouped inputs and our test fixtures).
    """
    if not entries:
        return []

    has_any_title = any(_is_title_line(e) for e in entries)
    if not has_any_title:
        # Caller already passed coherent project strings (e.g., test fixtures);
        # don't try to re-group.
        return list(entries)

    grouped: List[List[str]] = []
    for entry in entries:
        if _is_title_line(entry):
            grouped.append([entry])
        else:
            if not grouped:
                # Orphan continuation before any title — start a synthetic group.
                grouped.append([entry])
            else:
                grouped[-1].append(entry)

    return ["\n".join(group) for group in grouped]


# ─── Scoring constants ───────────────────────────────────────────────────────

# Final-score component weights (sum to 1.0).
FINAL_SCORE_WEIGHTS: Dict[str, float] = {
    "similarity": 0.40,
    "domain_alignment": 0.25,
    "complexity": 0.20,
    "impact": 0.15,
}

# Complexity tier base weights (before JD-driven adjustment).
COMPLEXITY_TIER_WEIGHTS: Dict[str, float] = {
    "architecture": 0.30,
    "ml_ai": 0.25,
    "data_engineering": 0.20,
    "infrastructure": 0.15,
    "design_verbs": 0.10,
}

# JD domain → boosted complexity tier(s). When the JD primary_domain is X,
# the listed complexity tier(s) get a 1.5x weight in the complexity score.
JD_DOMAIN_TIER_BOOSTS: Dict[str, List[str]] = {
    "data_science": ["ml_ai", "data_engineering"],
    "software_dev": ["architecture", "design_verbs"],
    "devops": ["infrastructure", "architecture"],
    "cybersecurity": ["infrastructure", "architecture"],
    "product_management": ["design_verbs"],
    "design": ["design_verbs"],
    "business": ["design_verbs"],
    "freshers": ["design_verbs"],
}

# Caps that prevent tier counts from runaway when a project mentions many
# keywords from the same tier.
TIER_COUNT_CAP = 4
IMPACT_COUNT_CAP = 6


# ─── Dataclasses ─────────────────────────────────────────────────────────────


@dataclass
class ProjectAnalysis:
    """Per-project analysis result."""
    raw_text: str
    title: str
    tech_stack: List[str]

    # Score axes (all 0.0–1.0)
    similarity_score: float
    complexity_score: float
    impact_score: float
    domain_alignment_score: float
    final_score: float

    # Evidence
    complexity_signals: Dict[str, List[str]]
    impact_signals: List[str]
    matched_jd_skills: List[str]

    # Position in the ranked list (1 = best)
    rank: int = 0

    # ── LLM enrichment (sub-phase 1.18) ───────────────────────────────────
    # Optional, default None. Populated only when an LLM provider is passed
    # to `analyze_projects`. INFORMATIONAL ONLY — never fed back into the
    # matcher (hallucination guard: see test_no_hallucination_pollution.py).
    llm_relevance: Optional[float] = None
    llm_skills_inferred: Optional[List[str]] = None
    llm_rationale: Optional[str] = None


@dataclass
class ProjectIntelligence:
    """Top-level output for analyze_projects()."""
    project_count: int = 0
    ranked_projects: List[Dict] = field(default_factory=list)

    # Aggregate signals
    best_score: float = 0.0
    average_score: float = 0.0
    coverage_score: float = 0.0  # how broadly projects span JD keywords

    # JD context echoed for traceability
    jd_role: str = ""
    jd_domain: str = ""
    jd_required_skills: List[str] = field(default_factory=list)

    # Metadata
    embedding_backend: str = ""

    # ── LLM enrichment (sub-phase 1.18) ───────────────────────────────────
    llm_top_strengths: Optional[List[str]] = None
    llm_top_gaps: Optional[List[str]] = None

    def to_dict(self) -> Dict:
        return asdict(self)


# ─── JD keyword extraction (shared helper) ──────────────────────────────────


def _build_jd_skill_set(jd_data: Optional[Dict]) -> Set[str]:
    """Flatten JD skill buckets into a normalized set for overlap matching."""
    if not jd_data:
        return set()
    all_skills = (
        jd_data.get("required_skills", [])
        + jd_data.get("preferred_skills", [])
        + jd_data.get("optional_skills", [])
    )
    result: Set[str] = set()
    for skill in all_skills:
        n = normalize_skill(normalize_phrase(skill))
        if n and len(n) > 1:
            result.add(n)
    return result


def _build_jd_corpus(jd_data: Optional[Dict]) -> str:
    """Build a representative text string for the JD to embed against.

    Falls back gracefully if jd_data lacks fields.
    """
    if not jd_data:
        return ""
    parts: List[str] = []
    role = jd_data.get("role_title") or ""
    if role and role != "not_specified":
        parts.append(role)
    domain = jd_data.get("primary_domain") or jd_data.get("domain_detected") or ""
    if domain and domain != "freshers":
        parts.append(domain.replace("_", " "))
    for bucket in ("required_skills", "preferred_skills", "optional_skills"):
        items = jd_data.get(bucket, [])
        if items:
            parts.extend(items)
    clean_text = jd_data.get("clean_text") or jd_data.get("raw_text") or ""
    if clean_text:
        parts.append(clean_text[:1000])  # cap so we don't dominate the vocab
    return ". ".join(parts).strip()


# ─── Score computation ──────────────────────────────────────────────────────


def _score_complexity(
    complexity_signals: Dict[str, List[str]],
    boosted_tiers: Set[str],
) -> float:
    """Compute complexity_score in [0, 1] using JD-driven tier weights.

    For each tier, the score contribution is:
        weight × min(matched_count / TIER_COUNT_CAP, 1.0)
    Boosted tiers get a 1.5× multiplier on their weight.
    """
    score = 0.0
    total_weight = 0.0
    for tier, base_weight in COMPLEXITY_TIER_WEIGHTS.items():
        weight = base_weight * (1.5 if tier in boosted_tiers else 1.0)
        total_weight += weight
        matched = len(complexity_signals.get(tier, []))
        tier_score = min(matched / float(TIER_COUNT_CAP), 1.0)
        score += weight * tier_score
    if total_weight == 0:
        return 0.0
    return min(round(score / total_weight, 4), 1.0)


def _score_impact(impact_signals: List[str]) -> float:
    """Impact score in [0, 1] = min(count / IMPACT_COUNT_CAP, 1.0)."""
    if not impact_signals:
        return 0.0
    return min(round(len(impact_signals) / float(IMPACT_COUNT_CAP), 4), 1.0)


def _score_domain_alignment(
    project_tech_stack: List[str],
    jd_skill_set: Set[str],
) -> tuple[float, List[str]]:
    """Domain alignment = |project_tech ∩ jd_skills| / |jd_skills|.

    Returns (score, matched_skills).
    """
    if not jd_skill_set or not project_tech_stack:
        return 0.0, []
    project_norm = {normalize_skill(normalize_phrase(s)) for s in project_tech_stack}
    project_norm.discard("")
    matched = sorted(project_norm & jd_skill_set)
    if not jd_skill_set:
        return 0.0, matched
    score = len(matched) / max(len(jd_skill_set), 1)
    # Boost: even 2–3 matched is meaningful. Cap at 1.0.
    return min(round(score * 2.0, 4), 1.0), matched


def _compute_final_score(
    similarity: float,
    domain_alignment: float,
    complexity: float,
    impact: float,
) -> float:
    """Weighted blend of the four axes, clamped to [0, 1]."""
    raw = (
        FINAL_SCORE_WEIGHTS["similarity"] * similarity
        + FINAL_SCORE_WEIGHTS["domain_alignment"] * domain_alignment
        + FINAL_SCORE_WEIGHTS["complexity"] * complexity
        + FINAL_SCORE_WEIGHTS["impact"] * impact
    )
    return round(min(max(raw, 0.0), 1.0), 4)


# ─── Main entry point ───────────────────────────────────────────────────────


def analyze_projects(
    projects: List[str],
    jd_data: Optional[Dict] = None,
    embedding_provider: Optional[EmbeddingProvider] = None,
    llm_provider: Optional[object] = None,
) -> ProjectIntelligence:
    """Analyze candidate projects against a JD.

    Args:
        projects: Raw project entry strings (from parsed_resume["projects"]).
        jd_data: Optional JD data. May be the output of
                 jd_intelligence.analyze_jd().to_dict() or jd_parser.parse_jd().
                 Used for similarity, domain alignment, and complexity weighting.
        embedding_provider: Optional override (mainly for tests).
        llm_provider: Optional LLMProvider (sub-phase 1.19). When provided,
            ONE batched LLM call enriches every project with `llm_relevance`,
            `llm_skills_inferred`, `llm_rationale` and the analysis with
            `llm_top_strengths` / `llm_top_gaps`. When None or backend=none,
            the llm_* fields stay None and behavior is byte-identical to
            baseline.

    Returns:
        ProjectIntelligence with per-project analysis, rankings, and aggregates.
    """
    if not projects:
        return ProjectIntelligence(
            project_count=0,
            ranked_projects=[],
            embedding_backend=(embedding_provider or get_embedding_provider()).backend,
            jd_role=(jd_data or {}).get("role_title", ""),
            jd_domain=(jd_data or {}).get("primary_domain", "") or (jd_data or {}).get("domain_detected", ""),
            jd_required_skills=list((jd_data or {}).get("required_skills", [])),
        )

    provider = embedding_provider or get_embedding_provider()

    # Step 0: Group flat resume-project lines into coherent project blocks
    # (resume_parser returns bullets as separate entries; we re-cluster them
    # under their preceding title line).
    projects = _group_project_lines(projects)

    # Step 1: Extract per-project metadata
    extractions: List[ProjectExtraction] = [extract_project(p) for p in projects]

    # Step 2: Compute similarities (embed projects + JD jointly for TF-IDF)
    jd_corpus = _build_jd_corpus(jd_data)
    has_jd = bool(jd_corpus.strip())
    if has_jd:
        proj_embs, jd_embs = provider.encode_pair(projects, [jd_corpus])
        sim_matrix = provider.cosine_similarity(proj_embs, jd_embs)
        similarities = [float(sim_matrix[i, 0]) for i in range(len(projects))]
        # Clamp similarity to [0, 1] (cosine can go negative for SBERT).
        similarities = [max(0.0, min(1.0, s)) for s in similarities]
    else:
        similarities = [0.0] * len(projects)

    # Step 3: JD context for domain/complexity weighting
    jd_skill_set = _build_jd_skill_set(jd_data)
    jd_domain = (
        (jd_data or {}).get("primary_domain")
        or (jd_data or {}).get("domain_detected")
        or ""
    )
    boosted_tiers: Set[str] = set(JD_DOMAIN_TIER_BOOSTS.get(jd_domain, []))

    # Step 4: Per-project scoring
    analyses: List[ProjectAnalysis] = []
    for idx, extraction in enumerate(extractions):
        complexity = _score_complexity(extraction.complexity_signals, boosted_tiers)
        impact = _score_impact(extraction.impact_signals)
        domain_align, matched = _score_domain_alignment(
            extraction.tech_stack, jd_skill_set
        )
        final = _compute_final_score(
            similarity=similarities[idx],
            domain_alignment=domain_align,
            complexity=complexity,
            impact=impact,
        )
        analyses.append(ProjectAnalysis(
            raw_text=extraction.raw_text,
            title=extraction.title or extraction.raw_text[:60],
            tech_stack=extraction.tech_stack,
            similarity_score=round(similarities[idx], 4),
            complexity_score=complexity,
            impact_score=impact,
            domain_alignment_score=domain_align,
            final_score=final,
            complexity_signals={k: v for k, v in extraction.complexity_signals.items() if v},
            impact_signals=extraction.impact_signals,
            matched_jd_skills=matched,
        ))

    # Step 4.5: (sub-phase 1.19) LLM enrichment. ONE batched call covering
    # ALL projects. Aligned by position with `analyses`. Informational only;
    # never reaches the matcher.
    llm_top_strengths: Optional[List[str]] = None
    llm_top_gaps: Optional[List[str]] = None
    if llm_provider is not None and analyses:
        proj_payload = [
            {"title": a.title, "text": a.raw_text[:1500]} for a in analyses
        ]
        jd_brief = _build_jd_brief_for_llm(jd_data)
        enrichment = _llm_enrich_projects(proj_payload, jd_brief, llm_provider)
        if enrichment is not None:
            for a, item in zip(analyses, enrichment.get("projects", [])):
                a.llm_relevance = item.get("llm_relevance")
                a.llm_skills_inferred = item.get("llm_skills_inferred")
                a.llm_rationale = item.get("llm_rationale")
            llm_top_strengths = enrichment.get("top_strengths")
            llm_top_gaps = enrichment.get("top_gaps")

    # Step 5: Rank by final_score (descending)
    ranked = sorted(analyses, key=lambda a: a.final_score, reverse=True)
    for i, a in enumerate(ranked):
        a.rank = i + 1

    # Step 6: Aggregates
    if ranked:
        best = ranked[0].final_score
        avg = round(sum(a.final_score for a in ranked) / len(ranked), 4)
    else:
        best = 0.0
        avg = 0.0

    # Coverage: union of matched_jd_skills across all projects, normalized
    # by jd_skill_set size. Caller can use this as a "skill-breadth" signal.
    all_matched: Set[str] = set()
    for a in ranked:
        all_matched.update(a.matched_jd_skills)
    coverage = (
        round(len(all_matched) / max(len(jd_skill_set), 1), 4) if jd_skill_set else 0.0
    )

    return ProjectIntelligence(
        project_count=len(projects),
        ranked_projects=[
            {
                "rank": a.rank,
                "title": a.title,
                "raw_text": a.raw_text[:300],
                "tech_stack": a.tech_stack,
                "similarity_score": a.similarity_score,
                "complexity_score": a.complexity_score,
                "impact_score": a.impact_score,
                "domain_alignment_score": a.domain_alignment_score,
                "final_score": a.final_score,
                "complexity_signals": a.complexity_signals,
                "impact_signals": a.impact_signals,
                "matched_jd_skills": a.matched_jd_skills,
                # LLM enrichment (informational only)
                "llm_relevance": a.llm_relevance,
                "llm_skills_inferred": a.llm_skills_inferred,
                "llm_rationale": a.llm_rationale,
            }
            for a in ranked
        ],
        best_score=best,
        average_score=avg,
        coverage_score=coverage,
        jd_role=(jd_data or {}).get("role_title", ""),
        jd_domain=jd_domain,
        jd_required_skills=list((jd_data or {}).get("required_skills", [])),
        embedding_backend=provider.backend,
        llm_top_strengths=llm_top_strengths,
        llm_top_gaps=llm_top_gaps,
    )


# ─── LLM enrichment helpers (sub-phase 1.19) ─────────────────────────────────


def _build_jd_brief_for_llm(jd_data: Optional[Dict]) -> str:
    """Compact JD context the LLM uses for relevance judgments."""
    if not jd_data:
        return "(no JD provided)"
    parts = []
    role = jd_data.get("role_title") or jd_data.get("llm_role_summary") or ""
    if role:
        parts.append(f"Role: {role}")
    domain = jd_data.get("primary_domain") or jd_data.get("domain_detected") or ""
    if domain:
        parts.append(f"Domain: {domain}")
    req = jd_data.get("required_skills") or []
    if req:
        parts.append(f"Required skills: {', '.join(req[:25])}")
    pref = jd_data.get("preferred_skills") or []
    if pref:
        parts.append(f"Preferred: {', '.join(pref[:15])}")
    return "\n".join(parts)


def _llm_enrich_projects(
    proj_payload: List[Dict], jd_brief: str, llm_provider,
) -> Optional[Dict]:
    """One batched LLM call to judge all projects against the JD.

    Returns a dict with keys: ``projects`` (list of per-project dicts),
    ``top_strengths``, ``top_gaps``. Returns ``None`` on any LLM failure
    so the caller leaves the llm_* fields unset.
    """
    from app.utils.llm_schemas import ProjectStructure

    system_prompt = (
        "You judge how relevant each candidate project is to a target job "
        "description.\n\n"
        "For each project, return llm_relevance ∈ [0.0, 1.0] reflecting how "
        "well the project demonstrates skills/experience the JD asks for.\n\n"
        "llm_skills_inferred: list the technical skills the project clearly "
        "demonstrates. This is INFORMATIONAL ONLY and is never used to award "
        "skill matches — do not pad it.\n\n"
        "rationale: one or two sentences explaining the relevance score, "
        "citing specific evidence from the project text.\n\n"
        "At the analysis level, return at most 5 top_strengths and 5 top_gaps "
        "for the candidate as a whole vs. this JD."
    )
    import json as _json
    user_prompt = (
        f"JOB DESCRIPTION:\n{jd_brief}\n\n"
        f"PROJECTS (return one item per input, IN THE SAME ORDER):\n"
        f"{_json.dumps(proj_payload, indent=2)}"
    )

    response = llm_provider.complete_json(
        system=system_prompt, user=user_prompt, schema=ProjectStructure,
    )
    if response is None:
        return None
    return {
        "projects": [
            {
                "llm_relevance": float(p.llm_relevance),
                "llm_skills_inferred": list(p.llm_skills_inferred),
                "llm_rationale": p.rationale,
            }
            for p in response.projects
        ],
        "top_strengths": list(response.top_strengths),
        "top_gaps": list(response.top_gaps),
    }
