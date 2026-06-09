"""Tests for the Experience Intelligence Engine (Phase 3).

Covers:
- Duration extraction (explicit, date range, season, edge cases)
- Duration aggregation
- Internship analysis and scoring
- Work experience analysis and scoring
- Candidate classification
- End-to-end analyze_experience()
- Relevance detection
"""

import pytest

from app.utils.duration_extraction import (
    extract_duration_months,
    aggregate_durations,
    get_duration_factor,
    DurationResult,
    AggregatedDuration,
)
from app.services.experience_intelligence import (
    analyze_experience,
    classify_candidate,
    score_internships,
    score_work_experience,
    _compute_relevance,
    _extract_keywords_from_jd,
    _reclassify_internship_entries,
    _detect_role,
    ExperienceIntelligence,
)
from tests.fixtures.sample_resumes import (
    FRESHER_RESUME,
    INTERN_RESUME,
    MULTIPLE_INTERNSHIPS_RESUME,
    EARLY_CAREER_RESUME,
    EXPERIENCED_RESUME,
    SENIOR_PROFESSIONAL_RESUME,
    DURATION_EDGE_CASES_RESUME,
    EMPTY_RESUME,
    SAMPLE_JD_BACKEND,
    SAMPLE_JD_FRESHER,
    SAMPLE_JD_SENIOR,
)


# ─── Duration Extraction ────────────────────────────────────────────────────


class TestDurationExtraction:
    """Tests for extract_duration_months()."""

    def test_explicit_months(self):
        result = extract_duration_months("Intern at Google - 3 months")
        assert result.months == 3.0
        assert result.classification == "medium"
        assert result.extraction_method == "explicit"

    def test_explicit_years(self):
        result = extract_duration_months("Worked for 2.5 years at Amazon")
        assert result.months == 30.0
        assert result.classification == "long"
        assert result.extraction_method == "explicit"

    def test_explicit_weeks(self):
        result = extract_duration_months("8 weeks internship at startup")
        assert result.months == 2.0
        assert result.classification == "short"
        assert result.extraction_method == "explicit"

    def test_date_range_same_year(self):
        result = extract_duration_months("Jan 2023 - Jun 2023")
        assert result.months == 5.0
        assert result.extraction_method == "date_range"

    def test_date_range_cross_year(self):
        result = extract_duration_months("October 2022 to March 2023")
        assert result.months == 5.0
        assert result.extraction_method == "date_range"

    def test_date_range_full_month_names(self):
        result = extract_duration_months("January 2022 to December 2023")
        assert result.months == 23.0
        assert result.classification == "long"

    def test_season_based(self):
        result = extract_duration_months("Summer 2023 Intern at TechCo")
        assert result.months == 3.0
        assert result.extraction_method == "season"

    def test_no_duration(self):
        result = extract_duration_months("Worked on various projects")
        assert result.months is None
        assert result.classification == "unknown"
        assert result.extraction_method == "none"

    def test_empty_input(self):
        result = extract_duration_months("")
        assert result.months is None
        assert result.classification == "unknown"

    def test_none_input(self):
        result = extract_duration_months(None)
        assert result.months is None

    def test_short_classification(self):
        result = extract_duration_months("2 months")
        assert result.classification == "short"

    def test_medium_classification(self):
        result = extract_duration_months("5 months")
        assert result.classification == "medium"

    def test_long_classification(self):
        result = extract_duration_months("1 year")
        assert result.classification == "long"


class TestDurationFactor:
    """Tests for get_duration_factor()."""

    def test_short_factor(self):
        assert get_duration_factor(2.0) == 0.7

    def test_medium_factor(self):
        assert get_duration_factor(4.0) == 0.85

    def test_long_factor(self):
        assert get_duration_factor(12.0) == 1.0

    def test_none_factor(self):
        assert get_duration_factor(None) == 0.6


class TestDurationAggregation:
    """Tests for aggregate_durations()."""

    def test_multiple_entries(self):
        entries = ["3 months at CompA", "6 months at CompB", "2 months at CompC"]
        result = aggregate_durations(entries)
        assert result.total_months == 11.0
        assert result.longest_entry_months == 6.0
        assert result.entry_count == 3
        assert result.classification == "long"

    def test_empty_entries(self):
        result = aggregate_durations([])
        assert result.total_months == 0.0
        assert result.entry_count == 0
        assert result.classification == "unknown"

    def test_no_detectable_durations(self):
        entries = ["Did some stuff", "Worked on projects"]
        result = aggregate_durations(entries)
        assert result.total_months == 0.0
        assert result.classification == "unknown"

    def test_mixed_detectable(self):
        entries = ["3 months at CompA", "Worked on projects"]
        result = aggregate_durations(entries)
        assert result.total_months == 3.0
        assert result.longest_entry_months == 3.0


# ─── Candidate Classification ────────────────────────────────────────────────


class TestCandidateClassification:
    """Tests for classify_candidate()."""

    def test_fresher_no_experience(self):
        cat, conf, signals = classify_candidate(0, 0, 0, 0)
        assert cat == "fresher"
        assert conf == "high"

    def test_fresher_short_internship(self):
        cat, conf, signals = classify_candidate(3, 0, 1, 0)
        assert cat == "fresher"

    def test_early_career(self):
        cat, conf, signals = classify_candidate(6, 12, 1, 1)
        assert cat == "early_career"

    def test_experienced(self):
        cat, conf, signals = classify_candidate(0, 60, 0, 2)
        assert cat == "experienced"

    def test_senior_professional(self):
        cat, conf, signals = classify_candidate(0, 120, 0, 4)
        assert cat == "senior_professional"

    def test_signals_populated(self):
        _, _, signals = classify_candidate(6, 24, 2, 1)
        assert len(signals) > 0
        assert any("total experience" in s for s in signals)


# ─── Relevance Detection ────────────────────────────────────────────────────


class TestRelevanceDetection:
    """Tests for keyword-based relevance matching."""

    def test_relevant_entry(self):
        jd_keywords = {"python", "fastapi", "postgresql", "docker"}
        score, signals = _compute_relevance(
            "Built REST APIs using Python and FastAPI with PostgreSQL database",
            jd_keywords,
        )
        assert score > 0.0
        assert len(signals) > 0

    def test_irrelevant_entry(self):
        jd_keywords = {"java", "spring boot", "kafka"}
        score, signals = _compute_relevance(
            "Managed office supplies and scheduling for the team",
            jd_keywords,
        )
        assert score == 0.0
        assert len(signals) == 0

    def test_empty_keywords(self):
        score, signals = _compute_relevance("Some text", set())
        assert score == 0.0

    def test_empty_text(self):
        score, signals = _compute_relevance("", {"python", "sql"})
        assert score == 0.0

    def test_keyword_extraction_from_jd(self):
        keywords = _extract_keywords_from_jd(
            ["Python", "FastAPI", "SQL"],
            jd_domain="software_dev",
            jd_role="Backend Engineer",
        )
        assert "python" in keywords
        assert "fastapi" in keywords
        assert "sql" in keywords
        assert "software dev" in keywords


# ─── Internship Scoring ─────────────────────────────────────────────────────


class TestInternshipScoring:
    """Tests for score_internships()."""

    def test_no_internships(self):
        score, analyses = score_internships([], set())
        assert score == 0.0
        assert len(analyses) == 0

    def test_single_internship(self):
        internships = ["Backend Intern at Google - 3 months. Used Python and Docker."]
        jd_keywords = {"python", "docker", "rest api"}
        score, analyses = score_internships(internships, jd_keywords)
        assert score > 0.0
        assert len(analyses) == 1

    def test_multiple_internships_higher_score(self):
        internships = [
            "Intern at Google - 6 months. Python and Kubernetes.",
            "Intern at Meta - 3 months. React and Node.js.",
        ]
        single = ["Intern at Google - 6 months. Python and Kubernetes."]
        jd_keywords = {"python", "kubernetes"}
        score_multi, _ = score_internships(internships, jd_keywords)
        score_single, _ = score_internships(single, jd_keywords)
        assert score_multi >= score_single

    def test_relevant_internship_scores_higher(self):
        relevant = ["Built REST APIs using Python and FastAPI - 3 months"]
        irrelevant = ["Organized team events and managed schedules - 3 months"]
        jd_keywords = {"python", "fastapi", "rest api"}
        score_rel, _ = score_internships(relevant, jd_keywords)
        score_irr, _ = score_internships(irrelevant, jd_keywords)
        assert score_rel > score_irr


# ─── Work Experience Scoring ─────────────────────────────────────────────────


class TestWorkExperienceScoring:
    """Tests for score_work_experience()."""

    def test_no_work_experience(self):
        score, analyses = score_work_experience([], set(), 0)
        assert score == 0.0

    def test_no_required_years(self):
        """When JD doesn't require experience, any experience = 1.0."""
        work_exp = ["Developer at CompA - 1 year"]
        score, _ = score_work_experience(work_exp, set(), 0)
        assert score == 1.0

    def test_meets_required_years(self):
        work_exp = ["Engineer at CompA - 5 years"]
        score, _ = score_work_experience(work_exp, set(), 3)
        assert score == 1.0

    def test_partial_required_years(self):
        work_exp = ["Engineer at CompA - 2 years"]
        score, _ = score_work_experience(work_exp, set(), 5)
        assert 0.0 < score < 1.0

    def test_multiple_entries_aggregate(self):
        work_exp = [
            "Engineer at CompA - 2 years",
            "Developer at CompB - 3 years",
        ]
        score, _ = score_work_experience(work_exp, set(), 5)
        assert score == 1.0


# ─── End-to-End analyze_experience() ─────────────────────────────────────────


class TestAnalyzeExperience:
    """End-to-end tests for the Experience Intelligence Engine."""

    def test_empty_resume(self):
        result = analyze_experience(EMPTY_RESUME)
        assert isinstance(result, ExperienceIntelligence)
        assert result.candidate_category == "fresher"
        assert result.internship_count == 0
        assert result.work_experience_count == 0

    def test_none_resume(self):
        result = analyze_experience(None)
        assert result.candidate_category == "fresher"

    def test_fresher_resume(self):
        result = analyze_experience(FRESHER_RESUME, SAMPLE_JD_FRESHER)
        assert result.candidate_category == "fresher"
        assert result.classification_confidence == "high"
        assert result.internship_count == 0
        assert result.work_experience_count == 0
        assert result.experience_quality_score == 0.0

    def test_intern_resume(self):
        result = analyze_experience(INTERN_RESUME, SAMPLE_JD_BACKEND)
        assert result.candidate_category == "fresher"  # 3 months = fresher
        assert result.internship_count == 1
        assert result.internship_total_months > 0
        assert result.internship_quality_score > 0.0

    def test_multiple_internships_resume(self):
        result = analyze_experience(MULTIPLE_INTERNSHIPS_RESUME, SAMPLE_JD_BACKEND)
        assert result.internship_count == 3
        assert result.internship_total_months > 0
        assert result.internship_quality_score > 0.0

    def test_early_career_resume(self):
        result = analyze_experience(EARLY_CAREER_RESUME, SAMPLE_JD_BACKEND)
        assert result.candidate_category in ("early_career", "experienced")
        assert result.internship_count == 1
        assert result.work_experience_count == 1
        assert result.total_experience_months > 12

    def test_experienced_resume(self):
        result = analyze_experience(EXPERIENCED_RESUME, SAMPLE_JD_SENIOR)
        assert result.candidate_category in ("experienced", "senior_professional")
        assert result.work_experience_count == 3
        assert result.total_experience_months > 60

    def test_senior_professional_resume(self):
        result = analyze_experience(SENIOR_PROFESSIONAL_RESUME, SAMPLE_JD_SENIOR)
        assert result.candidate_category == "senior_professional"
        assert result.work_experience_count == 4
        assert result.total_experience_months > 96

    def test_duration_edge_cases(self):
        result = analyze_experience(DURATION_EDGE_CASES_RESUME)
        assert result.internship_count == 4
        assert result.work_experience_count == 2
        # Should detect at least some durations
        assert result.total_experience_months > 0

    def test_with_jd_data(self):
        result = analyze_experience(EXPERIENCED_RESUME, SAMPLE_JD_SENIOR)
        assert result.jd_required_years == 5
        assert isinstance(result.experience_meets_jd_requirement, bool)

    def test_without_jd_data(self):
        result = analyze_experience(EXPERIENCED_RESUME, None)
        assert result.jd_required_years == 0
        assert result.experience_meets_jd_requirement is True

    def test_meets_jd_requirement(self):
        result = analyze_experience(EXPERIENCED_RESUME, SAMPLE_JD_SENIOR)
        assert result.experience_meets_jd_requirement is True

    def test_does_not_meet_jd_requirement(self):
        result = analyze_experience(INTERN_RESUME, SAMPLE_JD_SENIOR)
        assert result.experience_meets_jd_requirement is False

    def test_to_dict_returns_dict(self):
        result = analyze_experience(EXPERIENCED_RESUME, SAMPLE_JD_SENIOR)
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "candidate_category" in d
        assert "experience_quality_score" in d
        assert "internship_analyses" in d

    def test_internship_analyses_structure(self):
        result = analyze_experience(MULTIPLE_INTERNSHIPS_RESUME, SAMPLE_JD_BACKEND)
        for analysis in result.internship_analyses:
            assert "raw_text" in analysis
            assert "duration_months" in analysis
            assert "relevance_score" in analysis
            assert "company_detected" in analysis

    def test_work_experience_analyses_structure(self):
        result = analyze_experience(EXPERIENCED_RESUME, SAMPLE_JD_SENIOR)
        for analysis in result.work_experience_analyses:
            assert "raw_text" in analysis
            assert "duration_months" in analysis
            assert "relevance_score" in analysis
            assert "role_detected" in analysis

    def test_classification_signals_populated(self):
        result = analyze_experience(EXPERIENCED_RESUME, SAMPLE_JD_SENIOR)
        assert len(result.classification_signals) > 0

    def test_quality_scores_bounded(self):
        """All quality scores should be in [0.0, 1.0]."""
        for resume in [FRESHER_RESUME, INTERN_RESUME, EXPERIENCED_RESUME]:
            result = analyze_experience(resume, SAMPLE_JD_BACKEND)
            assert 0.0 <= result.experience_quality_score <= 1.0
            assert 0.0 <= result.internship_quality_score <= 1.0
            assert 0.0 <= result.work_experience_quality_score <= 1.0


# ─── Phase 3 Fix A: Internship reclassification ─────────────────────────────


class TestInternshipReclassification:
    """Tests for _reclassify_internship_entries() (Phase 3 fix A)."""

    def test_intern_titled_entry_moved_when_internships_empty(self):
        """When internships=[] and work_experience has an Intern-titled entry,
        the whole work_experience block should move to internships.
        """
        work_exp = [
            "Data & Insights Intern - Skypoint",
            "Apr 2026 - Present",
            "Built reporting pipelines.",
        ]
        intern, work = _reclassify_internship_entries([], work_exp)
        assert len(intern) == 3
        assert len(work) == 0

    def test_no_reclassification_when_internships_already_populated(self):
        """If the original split already produced internships, trust it."""
        existing_intern = ["Backend Intern at Google - 6 months"]
        work_exp = ["Software Engineer Intern - 1 year at Meta"]
        intern, work = _reclassify_internship_entries(existing_intern, work_exp)
        assert intern == existing_intern
        assert work == work_exp

    def test_no_reclassification_when_no_intern_marker(self):
        """Pure work_experience (no internship words) stays as work_experience."""
        work_exp = [
            "Senior Backend Engineer at Acme",
            "Jan 2020 - Dec 2023",
            "Built distributed systems.",
        ]
        intern, work = _reclassify_internship_entries([], work_exp)
        assert intern == []
        assert work == work_exp

    def test_trainee_keyword_triggers_reclassification(self):
        """Trainee should also trigger reclassification."""
        work_exp = ["Graduate Trainee at TCS", "Aug 2023 - Feb 2024"]
        intern, work = _reclassify_internship_entries([], work_exp)
        assert len(intern) == 2
        assert len(work) == 0

    def test_apprentice_keyword_triggers(self):
        work_exp = ["Software Apprentice at LMNO", "6 months"]
        intern, work = _reclassify_internship_entries([], work_exp)
        assert len(intern) == 2

    def test_returns_copies_not_references(self):
        """Returned lists should be new objects, not aliases to inputs."""
        original_intern = ["A"]
        original_work = ["B"]
        intern, work = _reclassify_internship_entries(original_intern, original_work)
        intern.append("X")
        work.append("Y")
        assert original_intern == ["A"]
        assert original_work == ["B"]

    def test_multi_role_moves_only_the_intern_role(self):
        """With multiple dated roles, only the intern role is moved; genuine
        professional roles stay as work experience (per-role segmentation)."""
        work_exp = [
            "Acme Corp", "Senior Engineer", "Jan 2021 - Dec 2023", "- Led backend.",
            "Beta Inc", "Software Intern", "Jun 2020 - Aug 2020", "- Built a feature.",
        ]
        intern, work = _reclassify_internship_entries([], work_exp)
        assert "Senior Engineer" in work and "Software Intern" not in work
        assert "Software Intern" in intern and "Senior Engineer" not in intern
        assert len(work) == 4 and len(intern) == 4

    def test_experienced_candidate_not_swept_into_internships(self):
        """Ananya-style: two professional roles + one intern role under a single
        'Experience' header. Only the intern role should reclassify."""
        work_exp = [
            "Skill Arbitrage", "Gurugram, India", "Data Science Consultant",
            "Oct 2024 - Present", "- Authored reusable Python modules.",
            "Solkraft Technology", "Jaipur, India", "Data Analyst",
            "Sep 2023 - Oct 2024", "- Validated terabytes of solar data.",
            "HUDCO", "New Delhi, India", "Data Scientist & Analyst Intern",
            "Jan 2023 - Aug 2023", "- Built an ML recommendation engine.",
        ]
        intern, work = _reclassify_internship_entries([], work_exp)
        assert "Data Science Consultant" in work
        assert "Data Analyst" in work
        assert "Data Scientist & Analyst Intern" in intern
        # The two professional role blocks stay; only the intern block moves.
        assert all("Intern" not in e for e in work)
        assert len(intern) == 5 and len(work) == 10


# ─── Phase 3 Fix B: _detect_role broader coverage ───────────────────────────


class TestDetectRoleBroaderCoverage:
    """Tests for _detect_role() (Phase 3 fix B)."""

    def test_detects_intern_title_with_ampersand(self):
        """'Data & Insights Intern - Skypoint' should be detected."""
        role = _detect_role("Data & Insights Intern - Skypoint")
        assert "Intern" in role
        assert "Data" in role

    def test_detects_engineer_title(self):
        """Existing Engineer detection still works."""
        role = _detect_role("Senior Software Engineer at Google")
        assert "Engineer" in role

    def test_detects_trainee_title(self):
        role = _detect_role("Graduate Trainee at Infosys")
        assert "Trainee" in role

    def test_detects_associate_title(self):
        role = _detect_role("Research Associate at MIT")
        assert "Associate" in role

    def test_detects_scientist_title(self):
        role = _detect_role("Data Scientist at OpenAI")
        assert "Scientist" in role

    def test_no_role_returns_empty(self):
        role = _detect_role("Worked on various interesting things")
        assert role == ""


# ─── Phase 3 Fix C: JD skill noise stripping ────────────────────────────────


class TestJdSkillNoiseStripping:
    """Tests for _normalize_skill_phrase noise stripping (Phase 3 fix C)."""

    def test_strips_like_prefix(self):
        from app.services.jd_parser import _normalize_skill_phrase
        assert _normalize_skill_phrase("like keras") == "keras"
        assert _normalize_skill_phrase("like scikit-learn") == "scikit-learn"

    def test_strips_etc_suffix(self):
        from app.services.jd_parser import _normalize_skill_phrase
        assert _normalize_skill_phrase("decision forests etc") == "decision forests"
        assert _normalize_skill_phrase("python etc.") == "python"

    def test_strips_is_desired_suffix(self):
        from app.services.jd_parser import _normalize_skill_phrase
        assert _normalize_skill_phrase("nosql is desired") == "nosql"
        assert _normalize_skill_phrase("docker is required") == "docker"
        assert _normalize_skill_phrase("kafka is preferred") == "kafka"

    def test_strips_for_example_prefix(self):
        from app.services.jd_parser import _normalize_skill_phrase
        assert _normalize_skill_phrase("for example python") == "python"

    def test_unchanged_when_no_noise(self):
        from app.services.jd_parser import _normalize_skill_phrase
        assert _normalize_skill_phrase("python") == "python"
        assert _normalize_skill_phrase("machine learning") == "machine learning"
