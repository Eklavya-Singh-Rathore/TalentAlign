"""Configuration loader for the TalentAlign backend.

Reads weight_config.json and exposes it as typed Python objects.
This is the beginning of the app/core/ module per the revamp plan.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


_CONFIG_DIR = Path(__file__).resolve().parent
_DEFAULT_WEIGHT_CONFIG_PATH = _CONFIG_DIR / "weight_config.json"


@dataclass
class WeightProfile:
    """A single domain-specific weight profile."""
    skills_weight: float
    projects_weight: float
    internship_weight: float
    experience_weight: float
    academics_weight: float
    achievements_weight: float
    description: str = ""
    version: int = 1

    def total(self) -> float:
        """Sum of all weights (should be ~1.0)."""
        return (
            self.skills_weight
            + self.projects_weight
            + self.internship_weight
            + self.experience_weight
            + self.academics_weight
            + self.achievements_weight
        )

    def validate(self) -> bool:
        """Check that all weights are non-negative and sum to ~1.0."""
        weights = [
            self.skills_weight, self.projects_weight, self.internship_weight,
            self.experience_weight, self.academics_weight, self.achievements_weight,
        ]
        if any(w < 0 for w in weights):
            return False
        return abs(self.total() - 1.0) < 0.01

    def as_dict(self) -> Dict[str, float]:
        """Return weights as a flat dictionary."""
        return {
            "skills_weight": self.skills_weight,
            "projects_weight": self.projects_weight,
            "internship_weight": self.internship_weight,
            "experience_weight": self.experience_weight,
            "academics_weight": self.academics_weight,
            "achievements_weight": self.achievements_weight,
        }


@dataclass
class WeightConfig:
    """Top-level weight configuration."""
    schema_version: str
    default_profile: str
    profiles: Dict[str, WeightProfile]
    adaptive_mode: bool = False
    adaptive_nudge: float = 0.05
    adaptive_low_score_threshold: float = 0.3

    def get_profile(self, domain: str) -> WeightProfile:
        """Get weight profile for a domain, falling back to default."""
        if domain in self.profiles:
            return self.profiles[domain]
        return self.profiles[self.default_profile]

    @property
    def available_domains(self) -> List[str]:
        """List of all available domain profile names."""
        return [k for k in self.profiles.keys() if k != "custom"]


def _parse_profile(name: str, data: dict) -> WeightProfile:
    """Parse a single weight profile from config JSON."""
    metadata = data.get("_metadata", {})
    return WeightProfile(
        skills_weight=float(data.get("skills_weight", 0.3)),
        projects_weight=float(data.get("projects_weight", 0.2)),
        internship_weight=float(data.get("internship_weight", 0.15)),
        experience_weight=float(data.get("experience_weight", 0.15)),
        academics_weight=float(data.get("academics_weight", 0.1)),
        achievements_weight=float(data.get("achievements_weight", 0.1)),
        description=metadata.get("description", ""),
        version=metadata.get("version", 1),
    )


def _resolve_config_path_from_env() -> str:
    """Resolve the weight-config path from the environment.

    Reads the current ``TALENTALIGN_WEIGHT_CONFIG_PATH`` first, then falls
    back to the legacy ``CPPS_WEIGHT_CONFIG_PATH`` (with a one-time
    deprecation warning) for backward compatibility with pre-rename setups.
    Defaults to the bundled config when neither is set.
    """
    new = os.environ.get("TALENTALIGN_WEIGHT_CONFIG_PATH")
    if new:
        return new
    legacy = os.environ.get("CPPS_WEIGHT_CONFIG_PATH")
    if legacy:
        logging.getLogger(__name__).warning(
            "CPPS_WEIGHT_CONFIG_PATH is deprecated; use "
            "TALENTALIGN_WEIGHT_CONFIG_PATH instead."
        )
        return legacy
    return str(_DEFAULT_WEIGHT_CONFIG_PATH)


def load_weight_config(
    config_path: Optional[str] = None,
) -> WeightConfig:
    """Load weight configuration from a JSON file.

    Args:
        config_path: Path to the config JSON file. If None, uses the
            default path (app/core/weight_config.json). Can also be
            overridden via the TALENTALIGN_WEIGHT_CONFIG_PATH env var.

    Returns:
        Parsed WeightConfig object.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        json.JSONDecodeError: If the config file is invalid JSON.
    """
    if config_path is None:
        config_path = _resolve_config_path_from_env()

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Weight config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    profiles = {}
    for name, profile_data in raw.get("profiles", {}).items():
        profiles[name] = _parse_profile(name, profile_data)

    return WeightConfig(
        schema_version=raw.get("schema_version", "1.0"),
        default_profile=raw.get("default_profile", "software_dev"),
        profiles=profiles,
        adaptive_mode=raw.get("adaptive_mode", False),
        adaptive_nudge=float(raw.get("adaptive_nudge", 0.05)),
        adaptive_low_score_threshold=float(
            raw.get("adaptive_low_score_threshold", 0.3)
        ),
    )


# Module-level singleton (lazy loaded)
_cached_config: Optional[WeightConfig] = None


def get_weight_config() -> WeightConfig:
    """Get the weight configuration (cached singleton).

    First call loads from disk; subsequent calls return the cached instance.
    """
    global _cached_config
    if _cached_config is None:
        _cached_config = load_weight_config()
    return _cached_config


def reset_weight_config_cache() -> None:
    """Clear the cached config (useful for testing)."""
    global _cached_config
    _cached_config = None
