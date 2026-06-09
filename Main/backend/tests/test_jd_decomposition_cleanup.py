"""Tests for the JD-decomposition noise cleanup.

Root fixes that stop fragment leakage into the missing-skills / recommendation
paths:
  - split on mid-phrase enumeration markers ("databases like mysql")
  - strip a stray trailing single letter ("web apis s" from malformed source)
  - reject standalone academic-degree abbreviations ("b.tech")
"""

from __future__ import annotations

import os

from app.services.jd_parser import (
    _extract_candidates_from_text,
    _normalize_skill_phrase,
    parse_jd,
)
from app.utils.file_handling import extract_text_from_docx
from app.utils.skill_normalization import is_valid_jd_skill

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestEnumerationSplit:
    def test_like_splits_category_and_example(self):
        cands = _extract_candidates_from_text("databases like mysql")
        assert "mysql" in cands
        assert "databases like mysql" not in cands

    def test_such_as_recovers_example(self):
        cands = _extract_candidates_from_text("ml frameworks such as tensorflow, pytorch")
        assert "tensorflow" in cands and "pytorch" in cands
        assert all("such as" not in c for c in cands)

    def test_including_splits(self):
        cands = _extract_candidates_from_text("cloud platforms including aws and azure")
        assert "aws" in cands and "azure" in cands


class TestTrailingStrayLetter:
    def test_strips_trailing_single_letter(self):
        assert _normalize_skill_phrase("web apis s") == "web apis"

    def test_preserves_c_and_r(self):
        assert _normalize_skill_phrase("objective c") == "objective c"
        assert _normalize_skill_phrase("statistical computing r") == "statistical computing r"


class TestDegreeRejection:
    def test_rejects_degree_abbreviations(self):
        for deg in ["b.tech", "m.tech", "b.e", "b.sc", "mca", "mba", "phd"]:
            assert is_valid_jd_skill(deg) is False, deg

    def test_keeps_real_skills(self):
        for sk in ["python", "tensorflow", "mysql", "machine learning"]:
            assert is_valid_jd_skill(sk) is True, sk


class TestJD1NoLeakedFragments:
    def test_jd1_fragments_removed_real_skill_kept(self):
        jd = parse_jd(extract_text_from_docx(os.path.join(FIXTURES, "JD_1.docx")))
        all_skills = (
            jd["required_skills"] + jd["preferred_skills"] + jd["optional_skills"]
        )
        assert "databases like mysql" not in all_skills
        assert "b.tech" not in all_skills
        assert "mysql" in jd["required_skills"]


class TestDerivedFlagCollapse:
    """Decomposed fragments are matching aids only: credited to their parent,
    excluded from the denominator and missing list."""

    def test_fragment_match_credits_parent_and_no_phantom_missing(self):
        from app.services.skill_matcher import _collapse_derived_matches
        jd_entries = [
            {"phrase": "machine learning frameworks", "bucket": "required"},
            {"phrase": "machine", "bucket": "required", "derived": True, "parent": "machine learning frameworks"},
            {"phrase": "learning frameworks", "bucket": "required", "derived": True, "parent": "machine learning frameworks"},
            {"phrase": "java", "bucket": "required"},
        ]
        matched = [
            {"resume_phrase": "machine learning", "jd_phrase": "machine", "jd_bucket": "required", "similarity": 0.9, "match_type": "partial"},
            {"resume_phrase": "java", "jd_phrase": "java", "jd_bucket": "required", "similarity": 1.0, "match_type": "exact"},
        ]
        counted, remapped, missing = _collapse_derived_matches(jd_entries, matched)
        assert {e["phrase"] for e in counted} == {"machine learning frameworks", "java"}
        assert {p["jd_phrase"] for p in remapped} == {"machine learning frameworks", "java"}
        # Fragment match credited the parent → no phantom fragments in missing.
        assert missing == []


class TestAggressiveNoiseFilter:
    """Aggressive denylist filter drops business/soft prose but keeps legitimate
    technical/domain skills that carry no obvious tech token."""

    def test_rejects_business_prose(self):
        for noise in ["team members", "internal partners", "from concept",
                      "codes of conduct", "best practices", "innovation mindset",
                      "technical curiosity", "analytical reasoning",
                      "compliance obligations", "their internal architecture",
                      "assist in building"]:
            assert is_valid_jd_skill(noise) is False, noise

    def test_keeps_legitimate_technical_skills(self):
        for skill in ["naive bayes", "decision forests", "credit card",
                      "machine learning frameworks", "data visualization tools",
                      "software architecture", "spring boot", "mysql"]:
            assert is_valid_jd_skill(skill) is True, skill
