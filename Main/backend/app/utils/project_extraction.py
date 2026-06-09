"""Per-project metadata extraction.

Pulls structured signals out of a single project description string:
  - title (the first headline-ish line, with hyphen/dash trims)
  - tech_stack (skills mentioned, normalized through skill_normalization)
  - complexity signals (technical depth markers: distributed, scalable,
    optimized, designed, ML/AI keywords, etc.)
  - impact signals (numeric outcomes, business verbs: reduced X by Y%,
    deployed, shipped, $-amounts, user counts, etc.)

Pure regex/keyword. No ML, no SBERT. Output is consumed by
project_intelligence.analyze_projects() to compute complexity_score,
impact_score, and (with JD context) domain alignment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set

from app.utils.skill_normalization import (
    SKILL_ALIAS_MAP,
    SEMANTIC_SYNONYMS,
    TECH_SIGNAL_TOKENS,
    extract_skills_from_full_text,
    has_technical_signal,
    normalize_phrase,
    normalize_skill,
)


# ─── Complexity signal keywords ──────────────────────────────────────────────
#
# Each tier maps to a weight: higher tier = stronger complexity signal.
# JD-driven weighting (Phase 4) reads the JD's required skills/domain and
# boosts tiers that align with the JD's emphasis.

COMPLEXITY_TIERS: Dict[str, List[str]] = {
    "architecture": [
        # System-design markers
        "distributed", "scalable", "microservices", "micro-services",
        "high availability", "high-availability", "fault tolerant",
        "fault-tolerant", "load balanced", "load-balanced", "real-time",
        "real time", "event-driven", "event driven", "pub-sub", "pubsub",
        "message queue", "message broker", "stream processing",
        "low latency", "low-latency", "high throughput", "high-throughput",
        "horizontally scalable", "concurrent", "concurrency",
        "asynchronous", "async", "multi-threaded", "multithreaded",
    ],
    "ml_ai": [
        # ML/AI advanced markers
        "deep learning", "neural network", "neural networks",
        "transformer", "transformers", "attention mechanism",
        "fine-tuning", "fine tuning", "transfer learning",
        "reinforcement learning", "rlhf", "embedding", "embeddings",
        "vector database", "rag", "retrieval augmented",
        "hyperparameter", "model deployment", "mlops",
        "tensorflow", "pytorch", "keras", "scikit-learn",
        "feature engineering", "model training",
    ],
    "data_engineering": [
        # Data pipeline markers
        "etl", "elt", "data pipeline", "data warehouse", "data lake",
        "spark", "hadoop", "kafka", "airflow", "dbt", "snowflake",
        "databricks", "stream processing", "batch processing",
        "data modeling", "data lakehouse",
    ],
    "infrastructure": [
        # DevOps / infrastructure markers
        "kubernetes", "k8s", "docker", "containerization",
        "ci/cd", "continuous integration", "continuous deployment",
        "terraform", "infrastructure as code", "iac", "ansible",
        "jenkins", "github actions", "gitlab ci",
        "cloud native", "cloud-native", "aws", "gcp", "azure",
        "serverless", "lambda", "cloud functions",
    ],
    "design_verbs": [
        # Role-verbs indicating ownership of the design
        "designed", "architected", "engineered", "built from scratch",
        "led", "owned", "spearheaded", "implemented", "developed",
        "optimized", "refactored", "scaled", "migrated",
    ],
}

# Flatten the tiers into one set for quick membership checks (case-insensitive,
# substring match) and a map of phrase → tier for weighting decisions.
_COMPLEXITY_PHRASE_TIER: Dict[str, str] = {}
for _tier, _phrases in COMPLEXITY_TIERS.items():
    for _phrase in _phrases:
        _COMPLEXITY_PHRASE_TIER[_phrase] = _tier


# ─── Impact signal patterns ──────────────────────────────────────────────────

IMPACT_NUMERIC_PATTERNS: List[re.Pattern] = [
    # Percentage outcomes: "reduced by 30%", "98.21% accuracy", "+15%"
    re.compile(r"\b\d+(?:\.\d+)?\s*%", re.IGNORECASE),
    # Multiplier outcomes: "3x faster", "10x improvement"
    re.compile(r"\b\d+(?:\.\d+)?\s*x\b", re.IGNORECASE),
    # Dollar/currency amounts: "$1M", "$50K", "₹2 crore"
    re.compile(r"[\$£€₹]\s*\d+(?:[\.,]\d+)?\s*(?:k|m|b|million|billion|crore|lakh)?", re.IGNORECASE),
    # Count outcomes: "10,000 users", "1M requests"
    re.compile(r"\b\d{1,3}(?:[,.]?\d{3})+(?:\s*\+)?\s+(?:users|requests|customers|records|transactions|queries|events)", re.IGNORECASE),
    # K/M/B suffix counts: "10K users", "1M+ events"
    re.compile(r"\b\d+(?:\.\d+)?\s*[KkMmBb]\+?\s+(?:users|requests|customers|records|transactions|queries|events)", re.IGNORECASE),
    # Time outcomes: "reduced from 5s to 1s", "3-second response"
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|seconds?|secs?|mins?|minutes?|hours?|days?)\b", re.IGNORECASE),
]

IMPACT_OUTCOME_VERBS: List[str] = [
    "reduced", "increased", "improved", "accelerated", "decreased",
    "boosted", "doubled", "tripled", "optimized", "achieved",
    "delivered", "shipped", "deployed", "launched", "released",
    "automated", "saved", "eliminated", "prevented",
    "scaled to", "grew to", "served", "processed", "handled",
    "won", "ranked", "awarded", "recognized", "selected",
]


# ─── Dataclass ───────────────────────────────────────────────────────────────

@dataclass
class ProjectExtraction:
    """Structured per-project metadata."""
    raw_text: str
    title: str = ""
    tech_stack: List[str] = field(default_factory=list)
    complexity_signals: Dict[str, List[str]] = field(default_factory=dict)
    impact_signals: List[str] = field(default_factory=list)
    word_count: int = 0


# ─── Title extraction ────────────────────────────────────────────────────────

_LEADING_DECOR_RE = re.compile(r"^[\s\-*•●▪■#>]+")
_TRAILING_PUNCT_RE = re.compile(r"[\s\-:;,.]+$")


def extract_project_title(text: str) -> str:
    """Return the most likely project title from a single project entry.

    Heuristics, in priority order:
      1. "Title — description" or "Title - description" (em-dash / hyphen
         after the title, lowercase or mixed-case description)
      2. The first non-empty line if it's short (≤10 words) and starts
         with a capital or contains alphabetic letters.
      3. Empty string if no good candidate found.
    """
    if not text:
        return ""
    # Drop leading bullets / decoration from each line up front.
    lines = [_LEADING_DECOR_RE.sub("", line).strip() for line in text.splitlines()]
    lines = [l for l in lines if l]
    if not lines:
        return ""

    first = lines[0]

    # Strategy 1: "Title - description" / "Title: description"
    # Hyphen/em-dash require whitespace on both sides (so "Node-RED" stays
    # intact); colon allows the more common "Title:" form with no leading
    # whitespace ("VERA: Verifying Remedies").
    m = re.match(r"^(.{2,80}?)(?:\s+[-—]\s+|\s*:\s+)(?=\S)", first)
    if m:
        candidate = m.group(1).strip()
        if 1 <= len(candidate.split()) <= 10:
            return _TRAILING_PUNCT_RE.sub("", candidate)

    # Strategy 2: first line if it's short
    words = first.split()
    if 1 <= len(words) <= 10 and any(c.isalpha() for c in first):
        return _TRAILING_PUNCT_RE.sub("", first)

    # Strategy 3: nothing matches; return empty so callers can decide.
    return ""


# ─── Tech stack extraction ───────────────────────────────────────────────────


def extract_project_tech_stack(text: str, cap: int = 15) -> List[str]:
    """Extract the tech stack mentioned in a single project entry.

    Uses the existing extract_skills_from_full_text helper which already
    handles label-prefix stripping ("Tech Stack: ..."), normalization
    through SKILL_ALIAS_MAP, and has_technical_signal filtering.
    """
    if not text or not text.strip():
        return []
    return extract_skills_from_full_text(text, cap=cap)


# ─── Complexity signal counting ──────────────────────────────────────────────


def count_complexity_signals(text: str) -> Dict[str, List[str]]:
    """Find complexity signal phrases grouped by tier.

    Returns a dict mapping tier name → list of matched phrases.
    Substring matching on lowercased text; preserves the matched
    phrase form so downstream consumers can show evidence.
    """
    result: Dict[str, List[str]] = {tier: [] for tier in COMPLEXITY_TIERS}
    if not text:
        return result
    lowered = text.lower()
    for tier, phrases in COMPLEXITY_TIERS.items():
        seen: Set[str] = set()
        for phrase in phrases:
            if phrase in lowered and phrase not in seen:
                seen.add(phrase)
                result[tier].append(phrase)
    return result


# ─── Impact signal counting ──────────────────────────────────────────────────


def count_impact_signals(text: str) -> List[str]:
    """Find impact-marker substrings in the project text.

    Catches:
      - Numeric outcomes (percentages, multipliers, currency, counts, durations)
      - Outcome verbs (reduced, increased, deployed, ...)

    Returns the matched substrings (lowercased), deduplicated.
    """
    if not text:
        return []
    lowered = text.lower()
    matches: List[str] = []
    seen: Set[str] = set()

    # Numeric patterns
    for pattern in IMPACT_NUMERIC_PATTERNS:
        for m in pattern.finditer(lowered):
            s = m.group(0).strip()
            if s and s not in seen:
                seen.add(s)
                matches.append(s)

    # Outcome verbs
    for verb in IMPACT_OUTCOME_VERBS:
        if re.search(rf"\b{re.escape(verb)}\b", lowered):
            if verb not in seen:
                seen.add(verb)
                matches.append(verb)

    return matches


# ─── Combined extraction ─────────────────────────────────────────────────────


def extract_project(text: str) -> ProjectExtraction:
    """Run all extractors on a single project entry."""
    text = text or ""
    return ProjectExtraction(
        raw_text=text,
        title=extract_project_title(text),
        tech_stack=extract_project_tech_stack(text),
        complexity_signals=count_complexity_signals(text),
        impact_signals=count_impact_signals(text),
        word_count=len(text.split()),
    )
