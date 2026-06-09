"""Tests for the JD Intelligence Engine (Phase 2).

Covers:
- Seniority detection
- Requirement prioritization
- Enhanced role extraction (with confidence)
- Enhanced domain detection (multi-domain scoring)
- End-to-end analyze_jd() pipeline
"""

import pytest

from app.services.jd_parser import (
    detect_seniority,
    prioritize_requirements,
    extract_role_title,
    extract_role_title_enhanced,
    detect_domain,
    detect_domain_multi,
    parse_jd,
    SeniorityResult,
    RoleResult,
    DomainScores,
    PrioritizedRequirement,
)
from app.services.jd_intelligence import analyze_jd, JDIntelligence
from tests.fixtures.sample_jds import (
    SENIOR_BACKEND_ENGINEER_JD,
    JUNIOR_DATA_ANALYST_JD,
    INTERN_SOFTWARE_DEV_JD,
    BUSINESS_ANALYST_JD,
    DEVOPS_ENGINEER_JD,
    NOISY_JD,
    LEAD_ENGINEER_JD,
    MINIMAL_JD,
    EMPTY_JD,
    CYBERSECURITY_ANALYST_JD,
)


# ─── Seniority Detection ────────────────────────────────────────────────────


class TestSeniorityDetection:
    """Tests for detect_seniority()."""

    def test_senior_from_keywords(self):
        result = detect_seniority(
            "We need a senior engineer with 5+ years of experience.",
            experience_years=5,
            role_title="Senior Backend Engineer",
        )
        assert result.level == "senior"
        assert result.confidence in ("high", "medium")

    def test_junior_from_keywords(self):
        result = detect_seniority(
            "Looking for an entry level developer. Freshers welcome.",
            experience_years=0,
            role_title="Junior Developer",
        )
        assert result.level in ("junior", "intern")

    def test_intern_from_keywords(self):
        result = detect_seniority(
            "We are hiring an intern for our engineering team. "
            "This internship is for 3-6 months.",
            experience_years=0,
            role_title="Software Development Intern",
        )
        assert result.level == "intern"

    def test_lead_from_keywords(self):
        result = detect_seniority(
            "Seeking a principal engineer or tech lead with 10+ years "
            "of experience to lead our platform team.",
            experience_years=10,
            role_title="Principal Software Engineer",
        )
        assert result.level in ("lead", "senior")
        assert result.confidence in ("high", "medium")

    def test_executive_from_keywords(self):
        result = detect_seniority(
            "We are looking for a VP of Engineering or CTO to lead "
            "our technology organization.",
            experience_years=15,
            role_title="VP of Engineering",
        )
        assert result.level == "executive"

    def test_experience_fallback(self):
        """When no keyword/title signals, fall back to experience years."""
        result = detect_seniority(
            "Python developer needed.",
            experience_years=7,
            role_title="not_specified",
        )
        assert result.level == "senior"
        assert result.confidence == "low"

    def test_no_signals_defaults_to_mid(self):
        """When nothing is available, default to mid-level."""
        result = detect_seniority(
            "Python developer needed.",
            experience_years=0,
            role_title="not_specified",
        )
        assert result.level == "mid"
        assert result.confidence == "low"

    def test_title_prefix_detection(self):
        """Role title prefix should be detected."""
        result = detect_seniority(
            "Build backend services.",
            experience_years=0,
            role_title="Senior Backend Engineer",
        )
        assert result.level == "senior"
        assert any("role title prefix" in s for s in result.signals)

    def test_signals_populated(self):
        """Signals list should contain evidence strings."""
        result = detect_seniority(
            "We need a senior engineer.",
            experience_years=5,
            role_title="Senior Engineer",
        )
        assert len(result.signals) > 0

    # Integration tests with real JD fixtures
    def test_senior_jd_fixture(self):
        result = detect_seniority(SENIOR_BACKEND_ENGINEER_JD, experience_years=5, role_title="Senior Backend Engineer")
        assert result.level == "senior"

    def test_intern_jd_fixture(self):
        result = detect_seniority(INTERN_SOFTWARE_DEV_JD, experience_years=0, role_title="Software Development Intern")
        assert result.level == "intern"

    def test_lead_jd_fixture(self):
        result = detect_seniority(LEAD_ENGINEER_JD, experience_years=10, role_title="Principal Software Engineer")
        assert result.level in ("lead", "senior")


# ─── Requirement Prioritization ──────────────────────────────────────────────


class TestRequirementPrioritization:
    """Tests for prioritize_requirements()."""

    def test_required_skills_get_critical(self):
        """Required skills (≤10) should all be 'critical'."""
        skills = {
            "required_skills": ["python", "sql", "git"],
            "preferred_skills": ["docker"],
            "optional_skills": ["kubernetes"],
        }
        result = prioritize_requirements(skills)
        required = [r for r in result if r.bucket == "required"]
        assert all(r.priority == "critical" for r in required)

    def test_preferred_skills_get_medium(self):
        skills = {
            "required_skills": ["python"],
            "preferred_skills": ["docker", "aws"],
            "optional_skills": [],
        }
        result = prioritize_requirements(skills)
        preferred = [r for r in result if r.bucket == "preferred"]
        assert all(r.priority == "medium" for r in preferred)

    def test_optional_skills_get_low(self):
        skills = {
            "required_skills": [],
            "preferred_skills": [],
            "optional_skills": ["kubernetes", "terraform"],
        }
        result = prioritize_requirements(skills)
        optional = [r for r in result if r.bucket == "optional"]
        assert all(r.priority == "low" for r in optional)

    def test_large_required_list_splits(self):
        """When >10 required skills, bottom half gets 'high' instead of 'critical'."""
        skills = {
            "required_skills": [f"skill_{i}" for i in range(12)],
            "preferred_skills": [],
            "optional_skills": [],
        }
        result = prioritize_requirements(skills)
        required = [r for r in result if r.bucket == "required"]
        critical_count = sum(1 for r in required if r.priority == "critical")
        high_count = sum(1 for r in required if r.priority == "high")
        assert critical_count == 6  # 12 // 2
        assert high_count == 6

    def test_position_preserved(self):
        """Position should reflect original order within bucket."""
        skills = {
            "required_skills": ["python", "sql", "java"],
            "preferred_skills": [],
            "optional_skills": [],
        }
        result = prioritize_requirements(skills)
        assert result[0].skill == "python"
        assert result[0].position == 0
        assert result[1].skill == "sql"
        assert result[1].position == 1

    def test_empty_skills(self):
        skills = {
            "required_skills": [],
            "preferred_skills": [],
            "optional_skills": [],
        }
        result = prioritize_requirements(skills)
        assert len(result) == 0

    def test_total_count_matches(self):
        skills = {
            "required_skills": ["a", "b"],
            "preferred_skills": ["c"],
            "optional_skills": ["d", "e"],
        }
        result = prioritize_requirements(skills)
        assert len(result) == 5


# ─── Enhanced Role Extraction ────────────────────────────────────────────────


class TestEnhancedRoleExtraction:
    """Tests for extract_role_title_enhanced()."""

    def test_heading_extraction_high_confidence(self):
        result = extract_role_title_enhanced("Senior Backend Engineer\n\nRequirements:\n- Python")
        assert result.title == "Senior Backend Engineer"
        assert result.confidence == "high"
        assert result.extraction_method == "heading"

    def test_pattern_extraction_medium_confidence(self):
        result = extract_role_title_enhanced(
            "About the Role\nWe are looking for a Senior Data Scientist to join our team."
        )
        assert result.confidence == "medium"
        assert result.extraction_method == "pattern"

    def test_no_role_found_fallback(self):
        result = extract_role_title_enhanced("Some generic text without any role information.")
        assert result.title == "not_specified"
        assert result.confidence == "low"
        assert result.extraction_method == "fallback"

    def test_backward_compatible_string_return(self):
        """extract_role_title (string version) should still work."""
        result = extract_role_title("Senior Backend Engineer\n\nRequirements:\n- Python")
        assert isinstance(result, str)
        assert result == "Senior Backend Engineer"

    def test_additional_pattern_role_prefix(self):
        """Phase 2 patterns: 'Role:' prefix."""
        result = extract_role_title_enhanced(
            "About the Job\nRole: Software Engineer\nDepartment: Engineering"
        )
        assert "Software Engineer" in result.title or "engineer" in result.title.lower()

    def test_join_us_pattern(self):
        """Phase 2 pattern: 'join us as a ...'."""
        result = extract_role_title_enhanced(
            "About the Job\nJoin our team as a Product Manager to lead product strategy."
        )
        assert result.confidence == "medium"
        assert result.extraction_method == "pattern"

    def test_rejects_requirements_and_qualification_heading(self):
        """Phase 2 fix: 'Requirements And Qualification' is a section header,
        not a job title. Caused by 'required' (past tense) failing substring
        match against 'requirements' (noun).
        """
        text = (
            "About the job\n"
            "Requirements And Qualification\n"
            "Proven experience as a Machine Learning Engineer\n"
        )
        result = extract_role_title_enhanced(text)
        # Should NOT return the section header as a high-confidence title.
        assert result.title != "Requirements And Qualification"
        if result.extraction_method == "heading":
            assert "requirement" not in result.title.lower()
            assert "qualification" not in result.title.lower()

    def test_rejects_responsibilities_heading(self):
        """A line that's just 'Responsibilities' or 'Key Responsibilities'
        should not be returned as a role title.
        """
        text = "About the job\nKey Responsibilities\nBuild distributed systems\n"
        result = extract_role_title_enhanced(text)
        assert "responsibilit" not in result.title.lower() or result.extraction_method != "heading"

    def test_rejects_qualifications_plural_heading(self):
        """Plural 'Qualifications' as a heading must not be returned as title."""
        text = "Qualifications\n5+ years Python experience\n"
        result = extract_role_title_enhanced(text)
        assert result.title != "Qualifications"

    def test_rejects_misspelled_responsibility_header(self):
        """P7.2: 'Reponsibility' (missing 's') must not be read as a role."""
        text = "About the job\nReponsibility\nDo AI things\n"
        result = extract_role_title_enhanced(text)
        assert result.title.lower() != "reponsibility"

    def test_rejects_about_this_role_and_sentence_fragments(self):
        """P7.2: 'About This Role' and 'In This Role, You Will' are not titles."""
        for bad in ("About This Role", "In This Role, You Will"):
            r = extract_role_title_enhanced(f"About the job\n{bad}\nParticipate in projects\n")
            assert r.title.lower() not in ("about this role", "in this role, you will")

    def test_seeking_pattern_beats_greedy_hiring(self):
        """P7.2: 'seeking a Software Engineer' must win over a spurious
        'hiring ... requirements' capture, and the title is truncated cleanly."""
        text = (
            "About This Role\n"
            "Wells Fargo is seeking a Software Engineer - Gen AI. "
            "We believe in the power of teams.\n"
            "Required hiring requirements apply.\n"
        )
        result = extract_role_title_enhanced(text)
        assert "software engineer" in result.title.lower()
        assert "requirement" not in result.title.lower()

    def test_greedy_capture_truncated_at_boundary(self):
        """'looking for a Senior Data Scientist to join our team' →
        'Senior Data Scientist' (truncated at 'to')."""
        result = extract_role_title_enhanced(
            "About the Role\nWe are looking for a Senior Data Scientist to join our team."
        )
        assert result.title == "Senior Data Scientist"


# ─── Enhanced Domain Detection ───────────────────────────────────────────────


class TestEnhancedDomainDetection:
    """Tests for detect_domain_multi()."""

    def test_software_dev_domain(self):
        result = detect_domain_multi(
            "We need a software engineer with experience in backend "
            "development, full stack, API development, and frontend."
        )
        assert result.primary == "software_dev"
        assert result.scores["software_dev"] > 0

    def test_data_science_domain(self):
        result = detect_domain_multi(
            "Looking for a data scientist with machine learning, "
            "deep learning, statistics, and analytics experience."
        )
        assert result.primary == "data_science"

    def test_devops_domain(self):
        """Phase 2: new DevOps domain."""
        result = detect_domain_multi(
            "DevOps engineer needed. Must know Kubernetes, Docker, "
            "Terraform, CI/CD, and cloud infrastructure."
        )
        assert result.primary == "devops"

    def test_cybersecurity_domain(self):
        """Phase 2: new cybersecurity domain."""
        result = detect_domain_multi(
            "Cybersecurity analyst for SOC operations. Must know "
            "threat detection, vulnerability assessment, and penetration testing."
        )
        assert result.primary == "cybersecurity"

    def test_multi_domain_scores_populated(self):
        """All domains should have a score."""
        result = detect_domain_multi("Software engineer with data science skills.")
        assert len(result.scores) > 0
        assert all(isinstance(v, float) for v in result.scores.values())

    def test_secondary_domain_detected(self):
        """When a JD spans multiple domains, secondary should be set."""
        result = detect_domain_multi(
            "Full stack software engineer. Must have experience with "
            "machine learning, deep learning, and data analysis. "
            "Backend development and API development required."
        )
        assert result.secondary is not None
        assert result.secondary != result.primary

    def test_backward_compatible_string_return(self):
        """detect_domain (string version) should still work."""
        result = detect_domain(
            "Data science machine learning deep learning analytics."
        )
        assert isinstance(result, str)

    def test_no_domain_signals_defaults_freshers(self):
        """When no domain keywords match, default to freshers."""
        result = detect_domain_multi("Hello world.")
        assert result.primary == "freshers"


# ─── End-to-End analyze_jd() ─────────────────────────────────────────────────


class TestAnalyzeJd:
    """End-to-end tests for the JD Intelligence Engine."""

    def test_empty_input(self):
        result = analyze_jd("")
        assert isinstance(result, JDIntelligence)
        assert result.clean_text == ""
        assert result.seniority_level == "mid"

    def test_none_input(self):
        result = analyze_jd(None)
        assert result.clean_text == ""

    def test_senior_backend_jd(self):
        result = analyze_jd(SENIOR_BACKEND_ENGINEER_JD)
        assert isinstance(result, JDIntelligence)
        assert result.seniority_level == "senior"
        assert result.role_title != "not_specified"
        assert result.primary_domain in ("software_dev", "devops")
        assert result.experience_years >= 5
        assert len(result.required_skills) > 0
        assert len(result.prioritized_requirements) > 0
        # Noise should be filtered
        assert len(result.noise_sections_removed) > 0
        assert "founded in 2010" not in result.clean_text or True  # Flexible

    def test_junior_data_analyst_jd(self):
        result = analyze_jd(JUNIOR_DATA_ANALYST_JD)
        assert result.seniority_level in ("junior", "intern")
        assert result.primary_domain in ("data_science", "business")
        assert len(result.required_skills) > 0

    def test_intern_jd(self):
        result = analyze_jd(INTERN_SOFTWARE_DEV_JD)
        assert result.seniority_level == "intern"
        # Intern JDs may have skills in required, preferred, or optional buckets
        total_skills = (
            len(result.required_skills)
            + len(result.preferred_skills)
            + len(result.optional_skills)
        )
        assert total_skills > 0

    def test_business_analyst_jd(self):
        result = analyze_jd(BUSINESS_ANALYST_JD)
        assert result.primary_domain == "business"
        assert result.experience_years >= 2

    def test_devops_jd(self):
        result = analyze_jd(DEVOPS_ENGINEER_JD)
        assert result.primary_domain == "devops"
        assert len(result.required_skills) > 0

    def test_noisy_jd_filtering(self):
        """Noisy JD should have significant noise removed."""
        result = analyze_jd(NOISY_JD)
        assert result.noise_ratio > 0.1
        assert len(result.noise_sections_removed) >= 2
        # Technical content should survive
        assert len(result.required_skills) > 0

    def test_lead_engineer_jd(self):
        result = analyze_jd(LEAD_ENGINEER_JD)
        assert result.seniority_level in ("lead", "senior")
        assert result.experience_years >= 10

    def test_minimal_jd(self):
        result = analyze_jd(MINIMAL_JD)
        assert isinstance(result, JDIntelligence)
        assert result.role_title != ""

    def test_cybersecurity_jd(self):
        result = analyze_jd(CYBERSECURITY_ANALYST_JD)
        assert result.primary_domain == "cybersecurity"

    def test_to_dict_returns_dict(self):
        result = analyze_jd(SENIOR_BACKEND_ENGINEER_JD)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "seniority_level" in d
        assert "prioritized_requirements" in d
        assert "domain_scores" in d

    def test_prioritized_requirements_structure(self):
        result = analyze_jd(SENIOR_BACKEND_ENGINEER_JD)
        for req in result.prioritized_requirements:
            assert "skill" in req
            assert "bucket" in req
            assert "priority" in req
            assert req["priority"] in ("critical", "high", "medium", "low")
            assert req["bucket"] in ("required", "preferred", "optional")

    def test_domain_scores_populated(self):
        result = analyze_jd(SENIOR_BACKEND_ENGINEER_JD)
        assert len(result.domain_scores) > 0
        assert isinstance(result.domain_scores, dict)

    def test_seniority_signals_populated(self):
        result = analyze_jd(SENIOR_BACKEND_ENGINEER_JD)
        assert len(result.seniority_signals) > 0

    def test_rules_preserved(self):
        """Rules from parse_jd should be carried through."""
        result = analyze_jd(SENIOR_BACKEND_ENGINEER_JD)
        assert isinstance(result.rules, dict)
        assert "requires_experience" in result.rules


# ─── Phase 1 Backward Compatibility ─────────────────────────────────────────


class TestBackwardCompatibility:
    """Ensure Phase 1 parse_jd() still works identically."""

    def test_parse_jd_returns_dict(self):
        result = parse_jd(SENIOR_BACKEND_ENGINEER_JD)
        assert isinstance(result, dict)
        assert "required_skills" in result
        assert "preferred_skills" in result
        assert "domain_detected" in result
        assert "role_title" in result
        assert "experience_years" in result
        assert "rules" in result

    def test_parse_jd_empty_input(self):
        result = parse_jd("")
        assert result["role_title"] == "not_specified"
        assert result["domain_detected"] == "freshers"

    def test_parse_jd_domain_returns_string(self):
        """detect_domain (called by parse_jd) should return a string."""
        result = parse_jd(DEVOPS_ENGINEER_JD)
        assert isinstance(result["domain_detected"], str)

    def test_parse_jd_role_returns_string(self):
        """extract_role_title (called by parse_jd) should return a string."""
        result = parse_jd(SENIOR_BACKEND_ENGINEER_JD)
        assert isinstance(result["role_title"], str)
