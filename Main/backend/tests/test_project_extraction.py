"""Tests for project_extraction utility (Phase 4 P4.1)."""

from __future__ import annotations

import pytest

from app.utils.project_extraction import (
    COMPLEXITY_TIERS,
    count_complexity_signals,
    count_impact_signals,
    extract_project,
    extract_project_tech_stack,
    extract_project_title,
)
from tests.fixtures.sample_projects import (
    DATA_ENG_PROJECT,
    DEVOPS_PROJECT,
    EMPTY_PROJECT,
    HOBBY_PROJECT,
    MINIMAL_PROJECT,
    ML_PROJECT,
    WEB_PROJECT,
)


class TestExtractProjectTitle:
    def test_title_with_dash(self):
        assert extract_project_title("VERA - Verifying Remedies\nDetails here") == "VERA"

    def test_title_with_em_dash(self):
        assert extract_project_title("VERA — Verifying Remedies\nDetails") == "VERA"

    def test_title_with_colon(self):
        assert extract_project_title("VERA: Verifying Remedies\nDetails") == "VERA"

    def test_title_short_line(self):
        assert extract_project_title("Personal Travel Blog\nUsed WordPress") == "Personal Travel Blog"

    def test_empty_input(self):
        assert extract_project_title("") == ""

    def test_only_long_line(self):
        text = "This is a very long line that goes on and on and on and probably is not a title at all because it exceeds the 10 word maximum"
        # ≥11 words → returned empty
        assert extract_project_title(text) == ""


class TestExtractProjectTechStack:
    def test_extracts_from_ml_project(self):
        stack = extract_project_tech_stack(ML_PROJECT)
        assert "scikit-learn" in stack
        assert "pandas" in stack

    def test_extracts_from_devops_project(self):
        stack = extract_project_tech_stack(DEVOPS_PROJECT)
        # 'amazon web services' is the normalized form of 'aws'
        assert any("amazon web services" in s or "aws" in s for s in stack)
        assert "kafka" in stack

    def test_empty(self):
        assert extract_project_tech_stack("") == []


class TestCountComplexitySignals:
    def test_ml_project_hits_ml_tier(self):
        result = count_complexity_signals(ML_PROJECT)
        assert result["ml_ai"]
        assert result["design_verbs"]

    def test_devops_project_hits_architecture_and_infrastructure(self):
        result = count_complexity_signals(DEVOPS_PROJECT)
        assert result["architecture"]
        assert result["infrastructure"]
        assert "kubernetes" in result["infrastructure"]
        assert "microservices" in result["architecture"]

    def test_hobby_project_hits_nothing(self):
        result = count_complexity_signals(HOBBY_PROJECT)
        assert all(not v for v in result.values())

    def test_returns_all_tiers(self):
        """Every tier must appear in the result dict even if empty."""
        result = count_complexity_signals("")
        assert set(result.keys()) == set(COMPLEXITY_TIERS.keys())


class TestCountImpactSignals:
    def test_percentage_outcomes(self):
        signals = count_impact_signals("Achieved 96.1% accuracy and reduced latency by 40%")
        assert any("96.1%" in s for s in signals)
        assert any("40%" in s for s in signals)
        assert "reduced" in signals
        assert "achieved" in signals

    def test_outcome_verbs(self):
        signals = count_impact_signals("Deployed the service and shipped to production")
        assert "deployed" in signals
        assert "shipped" in signals

    def test_no_impact(self):
        assert count_impact_signals("Used WordPress for blog") == []

    def test_user_counts(self):
        signals = count_impact_signals("Served 10K+ users and processed 1M+ requests")
        # Each numeric pattern hit at least once
        assert len(signals) >= 1

    def test_empty(self):
        assert count_impact_signals("") == []


class TestExtractProjectIntegration:
    """End-to-end extract_project() on all fixtures."""

    def test_ml_project(self):
        p = extract_project(ML_PROJECT)
        assert p.title == "VERA"
        assert "scikit-learn" in p.tech_stack
        assert p.complexity_signals["ml_ai"]
        assert "96.1%" in " ".join(p.impact_signals)

    def test_devops_project(self):
        p = extract_project(DEVOPS_PROJECT)
        assert p.complexity_signals["architecture"]
        assert p.complexity_signals["infrastructure"]
        assert "40%" in " ".join(p.impact_signals)

    def test_web_project(self):
        p = extract_project(WEB_PROJECT)
        assert "node.js" in p.tech_stack or "react" in p.tech_stack

    def test_hobby_project(self):
        p = extract_project(HOBBY_PROJECT)
        # Hobby project should have minimal signal
        all_complexity = sum(len(v) for v in p.complexity_signals.values())
        assert all_complexity == 0
        assert len(p.impact_signals) == 0

    def test_minimal_project(self):
        p = extract_project(MINIMAL_PROJECT)
        assert p.title  # at least non-empty
        # Should not crash

    def test_empty_project(self):
        p = extract_project(EMPTY_PROJECT)
        assert p.title == ""
        assert p.tech_stack == []
        assert p.impact_signals == []
