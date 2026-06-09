"""Tests for the FastAPI HTTP layer (app.main)."""

from __future__ import annotations

import os
from pathlib import Path

# Force the fast/deterministic embedding backend for API tests.
os.environ["TALENTALIGN_EMBEDDING_BACKEND"] = "tfidf"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.file_handling import extract_text_from_docx

FIXTURES = Path(__file__).resolve().parent / "fixtures"
RESUME = FIXTURES / "Eklavya_Singh_Rathore_Resume.pdf"
JD_TEXT = extract_text_from_docx(str(FIXTURES / "JD_1.docx"))

client = TestClient(app)


def _resume_files():
    return {"resume": ("resume.pdf", RESUME.read_bytes(), "application/pdf")}


class TestHealth:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["service"] == "talentalign-api"
        assert "embedding_backend" in body


class TestAnalyze:
    def test_analyze_returns_full_payload(self):
        r = client.post("/analyze", files=_resume_files(), data={"jd_text": JD_TEXT})
        assert r.status_code == 200, r.text
        body = r.json()
        assert 0.0 <= body["placement_score"] <= 100.0
        assert body["match_level"] in {"EXCELLENT", "GOOD", "MODERATE", "BELOW AVERAGE", "POOR"}
        assert len(body["component_breakdown"]) == 6
        assert "skills_analysis" in body and "recommendations" in body
        assert "warnings" in body
        # heavy debug log trimmed by default
        assert "full_debug_log" not in body.get("debug", {})

    def test_include_debug_keeps_full_log(self):
        r = client.post("/analyze?include_debug=true", files=_resume_files(), data={"jd_text": JD_TEXT})
        assert r.status_code == 200
        assert "full_debug_log" in r.json()["debug"]

    def test_empty_jd_rejected(self):
        r = client.post("/analyze", files=_resume_files(), data={"jd_text": "   "})
        assert r.status_code == 422

    def test_unsupported_extension_rejected(self):
        r = client.post(
            "/analyze",
            files={"resume": ("resume.txt", b"hello world", "text/plain")},
            data={"jd_text": "python developer"},
        )
        assert r.status_code == 422

    def test_empty_file_rejected(self):
        r = client.post(
            "/analyze",
            files={"resume": ("resume.pdf", b"", "application/pdf")},
            data={"jd_text": "python developer"},
        )
        assert r.status_code == 422

    def test_corrupt_pdf_returns_400_not_silent_zero(self):
        # Audit F1: a corrupt upload must error, not yield a misleading 0%.
        r = client.post(
            "/analyze",
            files={"resume": ("resume.pdf", b"this is not a real pdf", "application/pdf")},
            data={"jd_text": "python developer"},
        )
        assert r.status_code == 400

    def test_no_skill_jd_warns(self):
        # Audit F2: a JD with no extractable requirements is flagged.
        r = client.post("/analyze", files=_resume_files(), data={"jd_text": "lorem ipsum dolor sit amet foo bar baz qux"})
        assert r.status_code == 200
        assert any("job description" in w.lower() for w in r.json()["warnings"])
