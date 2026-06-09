"""Phase 1 (P1.3, P1.4) — section detection regex + alias expansion."""

from __future__ import annotations

from app.utils.skill_normalization import split_resume_into_sections
from app.utils.text_cleaning import normalize_document_text


def _split(resume_text: str) -> dict:
    return split_resume_into_sections(normalize_document_text(resume_text))


class TestStrictHeaders:
    def test_simple_headers_still_match(self) -> None:
        text = "Skills\nPython\n\nProjects\nBuilt X"
        out = _split(text)
        assert out["skills"] == ["Python"]
        assert out["projects"] == ["Built X"]

    def test_trailing_colon(self) -> None:
        text = "Skills:\nPython"
        out = _split(text)
        assert out["skills"] == ["Python"]

    def test_trailing_dash(self) -> None:
        text = "Skills -\nPython"
        out = _split(text)
        assert out["skills"] == ["Python"]


class TestAllCapsHeaders:
    def test_all_caps_skills(self) -> None:
        text = "SKILLS\nPython, SQL"
        out = _split(text)
        assert out["skills"] == ["Python, SQL"]

    def test_all_caps_with_underscore_decoration(self) -> None:
        text = "___ EXPERIENCE ___\nAcme Corp"
        out = _split(text)
        assert out["work_experience"] == ["Acme Corp"]


class TestDecoratedHeaders:
    def test_equals_decoration(self) -> None:
        text = "=== Skills ===\nPython"
        out = _split(text)
        assert out["skills"] == ["Python"]

    def test_hash_decoration(self) -> None:
        text = "### Projects\nBuilt X"
        out = _split(text)
        assert out["projects"] == ["Built X"]

    def test_dash_decoration(self) -> None:
        text = "--- Work Experience ---\nAcme"
        out = _split(text)
        assert out["work_experience"] == ["Acme"]

    def test_asterisk_decoration(self) -> None:
        text = "* Education *\nB.Tech"
        out = _split(text)
        assert out["education"] == ["B.Tech"]

    def test_chevron_decoration(self) -> None:
        text = "> Certifications\nAWS Cloud Practitioner"
        out = _split(text)
        assert out["certifications"] == ["AWS Cloud Practitioner"]


class TestNewAliases:
    def test_tools_routes_to_skills(self) -> None:
        text = "Tools\nPython, SQL"
        out = _split(text)
        assert out["skills"] == ["Python, SQL"]

    def test_selected_projects_routes_to_projects(self) -> None:
        text = "Selected Projects\nBuilt X"
        out = _split(text)
        assert out["projects"] == ["Built X"]

    def test_credentials_routes_to_certifications(self) -> None:
        text = "Credentials\nAWS SAA"
        out = _split(text)
        assert out["certifications"] == ["AWS SAA"]

    def test_internship_history_routes_to_internships(self) -> None:
        text = "Internship History\nTCS"
        out = _split(text)
        assert out["internships"] == ["TCS"]

    def test_professional_history_routes_to_work_experience(self) -> None:
        text = "Professional History\nAcme"
        out = _split(text)
        assert out["work_experience"] == ["Acme"]

    def test_education_and_training_routes_to_education(self) -> None:
        text = "Education & Training\nB.Tech"
        out = _split(text)
        assert out["education"] == ["B.Tech"]

    def test_honors_and_awards_routes_to_achievements(self) -> None:
        text = "Honors and Awards\nDean's List"
        out = _split(text)
        # smart quote becomes ASCII apostrophe after normalization
        assert out["achievements"] == ["Dean's List"]


class TestNoFalsePositives:
    def test_content_line_with_colon_is_not_a_header(self) -> None:
        text = "Skills\nLanguages: Python, Java"
        out = _split(text)
        assert out["skills"] == ["Languages: Python, Java"]

    def test_bare_content_line_not_treated_as_header(self) -> None:
        text = "Skills\nReact developer"
        out = _split(text)
        # 'React developer' has no matching alias; stays as skills content
        assert out["skills"] == ["React developer"]
