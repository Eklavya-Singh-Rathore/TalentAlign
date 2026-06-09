"""Tests for the JD noise filter utility.

Validates that boilerplate sections and inline noise are correctly
removed while preserving technical content.
"""

import pytest

from app.utils.jd_noise_filter import (
    FilteredJD,
    filter_jd_noise,
    _detect_noise_sections,
    _is_technical_heading,
    _classify_heading,
    _strip_heading_decoration,
)


class TestStripHeadingDecoration:
    """Test heading decoration removal."""

    def test_hash_decorations(self):
        assert _strip_heading_decoration("### About Us ###") == "About Us"

    def test_equals_decorations(self):
        assert _strip_heading_decoration("=== Benefits ===") == "Benefits"

    def test_dash_decorations(self):
        assert _strip_heading_decoration("--- Requirements ---") == "Requirements"

    def test_trailing_colon(self):
        assert _strip_heading_decoration("About Us:") == "About Us"

    def test_plain_text(self):
        assert _strip_heading_decoration("Required Skills") == "Required Skills"

    def test_empty(self):
        assert _strip_heading_decoration("") == ""


class TestHeadingClassification:
    """Test noise vs technical heading classification."""

    def test_about_us_is_noise(self):
        assert _classify_heading("About Us") == "company_info"

    def test_benefits_is_noise(self):
        assert _classify_heading("Benefits") == "benefits"

    def test_eeo_is_noise(self):
        assert _classify_heading("Equal Opportunity") == "eeo"

    def test_how_to_apply_is_noise(self):
        assert _classify_heading("How to Apply") == "application"

    def test_disclaimer_is_noise(self):
        assert _classify_heading("Disclaimer") == "disclaimer"

    def test_requirements_is_not_noise(self):
        assert _classify_heading("Requirements") is None

    def test_skills_is_not_noise(self):
        assert _classify_heading("Required Skills") is None

    def test_technical_heading_detected(self):
        assert _is_technical_heading("Requirements") is True
        assert _is_technical_heading("Required Skills") is True
        assert _is_technical_heading("Qualifications") is True
        assert _is_technical_heading("Responsibilities") is True

    def test_non_technical_heading(self):
        assert _is_technical_heading("About Us") is False
        assert _is_technical_heading("Benefits") is False

    def test_about_the_job_is_technical(self):
        """'About the job' is a JD-content marker (LinkedIn-style), not boilerplate."""
        assert _is_technical_heading("About the job") is True
        assert _is_technical_heading("About the role") is True
        # 'About us' must remain noise (not technical)
        assert _classify_heading("About us") == "company_info"

    def test_requirements_and_qualification_combined(self):
        """The combined 'Requirements And Qualification' heading is technical."""
        assert _is_technical_heading("Requirements and Qualification") is True
        assert _is_technical_heading("Requirements and Qualifications") is True


class TestFilterJdNoise:
    """Test the main filter_jd_noise function."""

    def test_empty_input(self):
        result = filter_jd_noise("")
        assert result.clean_text == ""
        assert result.removed_sections == []
        assert result.noise_ratio == 0.0

    def test_none_input(self):
        result = filter_jd_noise(None)
        assert result.clean_text == ""

    def test_no_noise_jd(self):
        """A JD with no boilerplate should be returned unchanged."""
        jd = """Software Engineer

Requirements:
- Python
- JavaScript
- SQL

Preferred:
- Docker experience
- Cloud platform knowledge
"""
        result = filter_jd_noise(jd)
        assert "Python" in result.clean_text
        assert "JavaScript" in result.clean_text
        assert result.noise_ratio < 0.05
        assert len(result.removed_sections) == 0

    def test_about_us_removed(self):
        """The 'About Us' section should be stripped."""
        jd = """Software Engineer

Requirements:
- Python
- SQL

About Us
We are a great company founded in 2010.
We have offices in 20 countries.
Our mission is to change the world.
"""
        result = filter_jd_noise(jd)
        assert "Python" in result.clean_text
        assert "SQL" in result.clean_text
        assert "founded in 2010" not in result.clean_text
        assert "offices in 20 countries" not in result.clean_text
        assert any("company_info" in s for s in result.removed_sections)

    def test_benefits_removed(self):
        """The 'Benefits' section should be stripped."""
        jd = """Data Analyst

Required Skills:
- SQL
- Python

Benefits
- Health insurance
- 401(k) matching
- Unlimited PTO
"""
        result = filter_jd_noise(jd)
        assert "SQL" in result.clean_text
        assert "Health insurance" not in result.clean_text
        assert any("benefits" in s for s in result.removed_sections)

    def test_eeo_removed(self):
        """EEO section should be stripped."""
        jd = """Developer

Requirements:
- JavaScript
- React

Equal Opportunity
We are an equal opportunity employer.
All qualified applicants will receive consideration.
"""
        result = filter_jd_noise(jd)
        assert "JavaScript" in result.clean_text
        assert "equal opportunity employer" not in result.clean_text

    def test_inline_noise_removed(self):
        """Inline EEO sentences should be removed even outside sections."""
        jd = """Developer

Requirements:
- Python
- SQL
We are an equal opportunity employer.
All qualified applicants will receive consideration for employment.
"""
        result = filter_jd_noise(jd)
        assert "Python" in result.clean_text
        assert "equal opportunity employer" not in result.clean_text

    def test_technical_sections_preserved(self):
        """Technical sections must NEVER be removed."""
        jd = """Requirements
- Python 3.x
- PostgreSQL
- Docker

Qualifications
- Bachelor's degree in CS
- 3+ years experience

About Us
We are a startup.
"""
        result = filter_jd_noise(jd)
        assert "Python 3.x" in result.clean_text
        assert "PostgreSQL" in result.clean_text
        assert "Docker" in result.clean_text
        assert "Bachelor's degree" in result.clean_text
        # About Us should be removed
        assert "We are a startup" not in result.clean_text

    def test_multiple_noise_sections(self):
        """Multiple noise sections should all be removed."""
        jd = """Engineer

Requirements:
- Java
- Spring Boot

About Us
Great company.

Benefits
- Insurance
- PTO

How to Apply
Send your resume.
"""
        result = filter_jd_noise(jd)
        assert "Java" in result.clean_text
        assert "Great company" not in result.clean_text
        assert "Insurance" not in result.clean_text
        assert "Send your resume" not in result.clean_text
        assert len(result.removed_sections) >= 3

    def test_noise_ratio_calculated(self):
        """Noise ratio should reflect the fraction of text removed."""
        jd = """Engineer

Requirements:
- Python

About Us
This is a very long about us section that takes up a lot of space.
We have many employees and offices around the world.
Our mission is very important and we are very passionate about it.
"""
        result = filter_jd_noise(jd)
        assert result.noise_ratio > 0.0
        assert result.noise_ratio < 1.0
        assert result.original_length > result.clean_length

    def test_all_noise_jd(self):
        """A JD that is entirely boilerplate."""
        jd = """About Us
We are a company.

Benefits
- Insurance
- PTO

Equal Opportunity
We are an equal opportunity employer.
"""
        result = filter_jd_noise(jd)
        assert result.noise_ratio > 0.5


class TestDetectNoiseSections:
    """Test the internal section detection logic."""

    def test_noise_section_boundaries(self):
        """Noise section should start at heading and end at next heading."""
        text = """Requirements:
- Python
- SQL

About Us
We are great.
We do cool things.

Required Skills:
- JavaScript
"""
        sections = _detect_noise_sections(text)
        assert len(sections) == 1
        assert sections[0].category == "company_info"
        # The noise section should NOT include "Required Skills" content
        lines = text.split("\n")
        noise_lines = lines[sections[0].start_line:sections[0].end_line]
        noise_text = "\n".join(noise_lines)
        assert "JavaScript" not in noise_text
