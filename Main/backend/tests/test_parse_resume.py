"""Phase 1 — integration tests for parse_resume against synthetic DOCX inputs."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

docx = pytest.importorskip("docx")
from docx import Document  # noqa: E402

from app.services.resume_parser import parse_resume  # noqa: E402


def _write_docx(paragraphs: list[str], tmp_path: Path, name: str = "resume.docx") -> str:
    path = tmp_path / name
    doc = Document()
    for para in paragraphs:
        doc.add_paragraph(para)
    doc.save(str(path))
    return str(path)


class TestParseResumeBaseline:
    def test_standard_sections(self, tmp_path: Path) -> None:
        path = _write_docx([
            "John Doe",
            "Skills",
            "Python, SQL, Pandas",
            "",
            "Projects",
            "Built a churn dashboard",
            "",
            "Education",
            "B.Tech CSE",
        ], tmp_path)
        out = parse_resume(path)
        assert "python" in out["skills"]
        assert "sql" in out["skills"]
        assert out["projects"] == ["Built a churn dashboard"]
        assert out["education"] == ["B.Tech CSE"]


class TestParseResumePhase1Improvements:
    def test_decorated_section_headers(self, tmp_path: Path) -> None:
        path = _write_docx([
            "=== SKILLS ===",
            "Python, TensorFlow",
            "### Projects",
            "Built ML model",
            "--- Work Experience ---",
            "Acme Corp",
        ], tmp_path)
        out = parse_resume(path)
        assert "python" in out["skills"]
        assert "tensorflow" in out["skills"]
        assert out["projects"] == ["Built ML model"]
        assert out["work_experience"] == ["Acme Corp"]

    def test_new_section_aliases(self, tmp_path: Path) -> None:
        path = _write_docx([
            "Tools",
            "Python, SQL",
            "Selected Projects",
            "Built a thing",
            "Credentials",
            "AWS SAA",
            "Internship History",
            "TCS Summer 2024",
        ], tmp_path)
        out = parse_resume(path)
        assert "python" in out["skills"]
        assert out["projects"] == ["Built a thing"]
        assert out["certifications"] == ["AWS SAA"]
        assert out["internships"] == ["TCS Summer 2024"]

    def test_per_section_fallback_when_skills_section_missing(self, tmp_path: Path) -> None:
        # No Skills section, but Projects mentions skills inline.
        path = _write_docx([
            "Jane Roe",
            "Projects",
            "Built a churn model using scikit-learn and pandas.",
            "Tech Stack: TensorFlow, PyTorch",
            "Education",
            "B.Tech CSE",
        ], tmp_path)
        out = parse_resume(path)
        assert "tensorflow" in out["skills"]
        assert "pytorch" in out["skills"]
        assert "scikit-learn" in out["skills"]
        # And fallback noise should NOT appear
        assert "jane roe" not in out["skills"]
        assert "b.tech cse" not in out["skills"]
        # Fallback source should be populated
        assert out["_skill_sources"]["fallback_full_text"]

    def test_skills_section_present_does_not_trigger_fallback(self, tmp_path: Path) -> None:
        path = _write_docx([
            "Skills",
            "Python, SQL",
            "Projects",
            "Built X using TensorFlow",
        ], tmp_path)
        out = parse_resume(path)
        # Fallback source should be empty since skills section yielded data
        assert out["_skill_sources"]["fallback_full_text"] == []
        assert "python" in out["skills"]
        assert "sql" in out["skills"]


class TestParseResumeEdgeCases:
    def test_empty_file_returns_empty_skeleton(self, tmp_path: Path) -> None:
        path = _write_docx([], tmp_path)
        out = parse_resume(path)
        assert out["skills"] == []
        assert out["projects"] == []

    def test_unsupported_extension_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "resume.txt"
        path.write_text("Hello")
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_resume(str(path))

    def test_missing_path_returns_empty(self) -> None:
        out = parse_resume("")
        assert out["skills"] == []
        assert out["projects"] == []
