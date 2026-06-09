"""Dataclasses returned by JD analysis primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SeniorityResult:
    """Result of seniority detection."""
    level: str                    # intern/junior/mid/senior/lead/executive
    confidence: str               # high/medium/low
    signals: List[str] = field(default_factory=list)


@dataclass
class RoleResult:
    """Enhanced role extraction result with confidence."""
    title: str
    confidence: str               # high/medium/low
    extraction_method: str        # heading/pattern/fallback


@dataclass
class DomainScores:
    """Multi-domain detection result."""
    primary: str
    secondary: Optional[str]
    scores: Dict[str, float]      # domain → score (0.0–1.0)


@dataclass
class PrioritizedRequirement:
    """A single skill with its priority ranking."""
    skill: str
    bucket: str                   # required/preferred/optional
    priority: str                 # critical/high/medium/low
    priority_reason: str
    position: int                 # original position in the bucket (0-indexed)
