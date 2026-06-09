"""Sub-phase 1.2 — schemas round-trip a sample payload for every endpoint."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.utils.llm_schemas import (
    Explanation,
    ExperienceStructure,
    JDStructure,
    MatchValidation,
    MatchValidationItem,
    ProjectRelevance,
    ProjectStructure,
    SCHEMA_REGISTRY,
)


class TestJDStructure:
    def test_minimal_round_trip(self):
        m = JDStructure(
            role_summary="Senior Backend Engineer",
            seniority="senior",
            confidence=0.82,
        )
        assert m.role_summary == "Senior Backend Engineer"
        assert m.responsibilities == []
        # JSON round-trip
        again = JDStructure.model_validate_json(m.model_dump_json())
        assert again == m

    def test_confidence_bounded(self):
        with pytest.raises(ValidationError):
            JDStructure(role_summary="X", seniority="mid", confidence=1.5)
        with pytest.raises(ValidationError):
            JDStructure(role_summary="X", seniority="mid", confidence=-0.1)

    def test_extra_fields_ignored(self):
        m = JDStructure(role_summary="X", seniority="mid", confidence=0.5, extra_field="nope")
        assert not hasattr(m, "extra_field")


class TestExperienceStructure:
    def test_round_trip(self):
        m = ExperienceStructure(
            candidate_type="early_career",
            relevant_experience_months=18,
            rationale="Two relevant internships totalling 18 months on data pipelines.",
        )
        assert m.relevant_experience_months == 18

    def test_months_nonnegative(self):
        with pytest.raises(ValidationError):
            ExperienceStructure(
                candidate_type="fresher", relevant_experience_months=-1, rationale="x"
            )


class TestProjectStructure:
    def test_batched_projects(self):
        m = ProjectStructure(
            projects=[
                ProjectRelevance(
                    project_title="Resume scorer",
                    llm_relevance=0.81,
                    rationale="Direct overlap with the JD's ML stack.",
                ),
                ProjectRelevance(
                    project_title="Auto-router",
                    llm_relevance=0.42,
                    rationale="Partial overlap on NLP terms.",
                ),
            ],
            top_strengths=["ML stack alignment"],
            top_gaps=["No prod deployment experience"],
        )
        assert len(m.projects) == 2
        assert m.projects[0].llm_relevance == 0.81

    def test_relevance_bounded(self):
        with pytest.raises(ValidationError):
            ProjectRelevance(project_title="X", llm_relevance=2.0, rationale="x")


class TestMatchValidation:
    def test_items_round_trip(self):
        m = MatchValidation(
            items=[
                MatchValidationItem(pair_id="p1", is_valid_match=True, confidence=0.9,
                                    reason="Direct equivalence."),
                MatchValidationItem(pair_id="p2", is_valid_match=False, confidence=0.7,
                                    reason="Different domains."),
            ]
        )
        assert len(m.items) == 2
        assert m.items[0].is_valid_match is True


class TestExplanation:
    def test_round_trip(self):
        m = Explanation(
            overall_summary="Strong ML alignment; missing leadership signals.",
            top_strengths=["Python/ML stack"],
            top_gaps=["No team-lead experience"],
            next_steps=["Add 1–2 leadership bullets"],
        )
        assert m.overall_summary.startswith("Strong")


class TestSchemaRegistry:
    def test_all_schemas_registered(self):
        # If we add a schema and forget the registry, this fails loudly.
        expected = {
            "JDStructure", "ExperienceStructure", "ProjectStructure",
            "MatchValidation", "Explanation",
        }
        assert set(SCHEMA_REGISTRY) == expected
