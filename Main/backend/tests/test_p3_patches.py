"""Regression tests for the Phase 1-3 extraction patches (P3patch.A-D).

These lock in the fixes surfaced by the 3x9 comprehensive evaluation:
  A — JD skill-section extraction stops mining responsibility/values prose.
  B — role extraction rejects imperative/requirement lines; requires a role noun.
  C — domain normalization no longer penalizes longer keyword lists.
  D — resume skill hygiene drops URLs and job titles.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.jd_intelligence import analyze_jd
from app.services.jd_parser import extract_role_title_enhanced, parse_jd
from app.services.resume_parser import parse_resume
from app.utils.file_handling import extract_text_from_docx
from app.utils.skill_normalization import is_valid_jd_skill, is_valid_skill

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# ─── P3patch.A — JD skill-section extraction ─────────────────────────────────


class TestSkillValidityFilters:
    def test_rejects_verb_led_responsibility_phrases(self):
        for bad in (
            "improve operational efficiency", "identify potential risks",
            "performing data cleaning", "ensure compliance", "managing risk",
            "supporting professional development",
        ):
            assert not is_valid_jd_skill(bad), bad

    def test_rejects_value_fragments(self):
        for bad in ("be authentic", "e energise", "to meet the needs"):
            assert not is_valid_jd_skill(bad), bad

    def test_keeps_real_skills(self):
        for good in ("python", "sql", "machine learning", "data visualization",
                     "logistic regression", "neural networks"):
            assert is_valid_jd_skill(good), good


class TestJD9Extraction:
    """The Barclays JD-9 was the critical failure: responsibility/values prose
    leaked into required_skills. After the patch it must contain real skills
    and none of the value/responsibility noise."""

    @pytest.fixture(scope="class")
    def jd9(self):
        return parse_jd(extract_text_from_docx(str(FIXTURES / "JD-9.docx")))

    def test_real_skills_present(self, jd9):
        allskills = " ".join(jd9["required_skills"] + jd9["preferred_skills"]).lower()
        assert "python" in allskills
        assert "sql" in allskills

    def test_noise_absent(self, jd9):
        joined = " ".join(jd9["required_skills"]).lower()
        for noise in ("be authentic", "energise", "operational efficiency",
                      "professional development", "potential risks"):
            assert noise not in joined, f"noise leaked: {noise}"

    def test_clean_jds_not_regressed(self):
        # JD_1 (clean) should still extract its core ML skills.
        jd1 = parse_jd(extract_text_from_docx(str(FIXTURES / "JD_1.docx")))
        joined = " ".join(jd1["required_skills"]).lower()
        assert "pytorch" in joined and "scikit-learn" in joined


# ─── P3patch.B — role extraction ─────────────────────────────────────────────


class TestRoleExtraction:
    def test_rejects_imperative_line(self):
        r = extract_role_title_enhanced(
            "Job description\nWrite well designed, testable, efficient code\nMore text"
        )
        assert "write" not in r.title.lower()

    def test_rejects_requirement_stem(self):
        r = extract_role_title_enhanced(
            "Job description\nProficient in Python, SAS, SQL\nMore text"
        )
        assert "proficient" not in r.title.lower()

    def test_rejects_header_without_role_noun(self):
        r = extract_role_title_enhanced(
            "Job description\nDevelopment Implementation\nMore text"
        )
        # "Development Implementation" has no role noun → not a heading title.
        assert r.title != "Development Implementation"

    def test_keeps_genuine_title_with_role_noun(self):
        r = extract_role_title_enhanced("Senior Backend Engineer\n\nRequirements:\n- Python")
        assert r.title == "Senior Backend Engineer"
        assert r.confidence == "high"

    def test_jd7_jd9_roles_reasonable(self):
        jd7 = analyze_jd(extract_text_from_docx(str(FIXTURES / "JD-7.docx")))
        jd9 = analyze_jd(extract_text_from_docx(str(FIXTURES / "JD-9.docx")))
        assert "developer" in jd7.role_title.lower()  # Java Developer
        assert "analyst" in jd9.role_title.lower()     # Business/Decision Analyst


# ─── P3patch.C — domain detection ────────────────────────────────────────────


class TestDomainDetection:
    def test_jd6_is_software_dev(self):
        jd6 = analyze_jd(extract_text_from_docx(str(FIXTURES / "JD-6.docx")))
        assert jd6.primary_domain == "software_dev"

    def test_jd5_still_software_dev(self):
        # Guards the normalization regression (JD_5 flipped to 'design' when
        # software_dev's keyword list grew under the old count/len normalization).
        jd5 = analyze_jd(extract_text_from_docx(str(FIXTURES / "JD_5.docx")))
        assert jd5.primary_domain == "software_dev"

    def test_data_science_jds_unchanged(self):
        for name in ("JD_1", "JD_3", "JD_4"):
            jd = analyze_jd(extract_text_from_docx(str(FIXTURES / f"{name}.docx")))
            assert jd.primary_domain == "data_science", name


# ─── P3patch.D — resume skill hygiene ────────────────────────────────────────


class TestResumeSkillHygiene:
    def test_url_rejected(self):
        assert not is_valid_skill("linkedin.com")
        assert not is_valid_skill("github.com")
        assert not is_valid_skill("www.example.com")

    def test_tech_extensions_preserved(self):
        assert is_valid_skill("node.js")
        assert is_valid_skill("react.js")
        assert is_valid_skill("asp.net")
        assert is_valid_skill("socket.io")

    def test_job_titles_rejected(self):
        for title in ("data analyst", "data science consultant", "ml engineer",
                      "software developer", "project manager"):
            assert not is_valid_skill(title), title

    def test_ing_skills_preserved(self):
        # -ing forms are skills, not roles
        assert is_valid_skill("data engineering")
        assert is_valid_skill("software engineering")

    def test_ananya_resume_clean(self):
        r = parse_resume(str(FIXTURES / "Ananya_Joshi_Resume.pdf"))
        joined = " ".join(r["skills"]).lower()
        assert "linkedin.com" not in joined
        assert "data analyst" not in r["skills"]
        assert "data science consultant" not in r["skills"]
        # Real skills retained
        assert "python" in r["skills"]
        assert "sql" in r["skills"]
