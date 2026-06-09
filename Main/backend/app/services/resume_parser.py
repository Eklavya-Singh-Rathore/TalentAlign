"""Resume parsing service.

Ported from Code/app_logic.py (Stage 1: Resume Parser). Behavior is preserved
identically during the Phase 1 port. Phase 1 improvements (broader section
regex, expanded aliases, per-section fallback) are layered in subsequent
sub-tasks (P1.2–P1.5).
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from app.utils.file_handling import (
    extract_text_from_docx,
    extract_text_from_pdf,
)
from app.utils.text_cleaning import normalize_document_text
from app.utils.skill_normalization import (
    extract_skills_from_full_text,
    extract_skills_from_section as core_extract_skills_from_section,
    merge_unique_skills,
    split_resume_into_sections,
    split_skill_line,
)


# --- Certification → implied skills map ---
CERT_SKILL_MAP = {
    "aws": ["aws", "cloud computing", "amazon web services"],
    "azure": ["azure", "cloud computing", "microsoft azure"],
    "google cloud": ["gcp", "cloud computing", "google cloud platform"],
    "data analytics": ["data analytics", "sql", "tableau", "spreadsheets"],
    "data science": ["data science", "python", "statistics", "machine learning"],
    "machine learning": ["machine learning", "python", "scikit-learn"],
    "deep learning": ["deep learning", "tensorflow", "keras", "neural networks"],
    "web development": ["html", "css", "javascript", "web development"],
    "docker": ["docker", "containerization", "devops"],
    "kubernetes": ["kubernetes", "container orchestration", "devops"],
    "python": ["python", "programming"],
    "java": ["java", "object-oriented programming"],
    "nlp": ["nlp", "natural language processing", "python"],
    "computer vision": ["computer vision", "opencv", "deep learning"],
    "agile": ["agile", "scrum", "project management"],
    "tableau": ["tableau", "data visualization"],
    "power bi": ["power bi", "data visualization"],
    "sql": ["sql", "database"],
    "mongodb": ["mongodb", "nosql", "database"],
}


def split_into_sections(raw_text: str) -> dict:
    """Split raw resume text into 7 structured sections."""
    return split_resume_into_sections(raw_text)


def extract_skills_from_certifications(cert_section: list) -> list:
    """Extract implied skills from certification titles."""
    if not cert_section:
        return []
    extracted_skills = set()
    for cert_entry in cert_section:
        cert_lower = cert_entry.lower()
        for keyword, skills in CERT_SKILL_MAP.items():
            if keyword in cert_lower:
                extracted_skills.update(skills)
    return sorted(list(extracted_skills))


def extract_skills_from_section(section_entries: list) -> list:
    """Backward-compatible wrapper around the shared helper."""
    return core_extract_skills_from_section(section_entries)


def parse_resume(file_path: str) -> dict:
    """Parse a resume file (PDF/DOCX) into a structured 7-section dictionary."""
    empty_output = {
        "skills": [], "projects": [], "certifications": [],
        "cert_derived_skills": [],
        "internships": [], "work_experience": [],
        "education": [], "achievements": [],
    }
    if not file_path:
        return empty_output
    file_path = str(file_path)
    ext = Path(file_path).suffix.lower()
    if ext not in [".pdf", ".docx"]:
        raise ValueError(f"Unsupported file type: '{ext}'. Only .pdf and .docx are supported.")

    if ext == ".pdf":
        raw_text = extract_text_from_pdf(file_path)
    else:
        raw_text = extract_text_from_docx(file_path)

    if not raw_text.strip():
        return empty_output

    raw_text = normalize_document_text(raw_text)
    sections = split_into_sections(raw_text)
    soft_skill_labels = {"soft skills", "personal skills", "interpersonal skills"}
    sections["skills"] = [
        entry for entry in sections["skills"]
        if entry.split(":", 1)[0].strip().lower() not in soft_skill_labels
    ]

    explicit_skill_items: List[str] = []
    for entry in sections["skills"]:
        explicit_skill_items.extend(split_skill_line(entry) or [entry])

    cert_skills = extract_skills_from_certifications(sections["certifications"])
    project_skills = core_extract_skills_from_section(sections["projects"])
    internship_skills = core_extract_skills_from_section(sections["internships"])
    work_skills = core_extract_skills_from_section(sections["work_experience"])

    fallback_skills: List[str] = []
    merged_skills = merge_unique_skills(
        explicit_skill_items, cert_skills, project_skills, internship_skills, work_skills
    )
    # Phase 1 (P1.5): per-section fallback. Fire the full-text skill miner
    # whenever the explicit Skills section yielded nothing, instead of only
    # when *every* structured source is empty. This catches resumes where the
    # Skills section is missing or used an unrecognized header but skill
    # terms appear inline (in summaries, project blurbs, etc.).
    needs_skill_fallback = not explicit_skill_items
    if needs_skill_fallback:
        fallback_skills = extract_skills_from_full_text(raw_text)
        merged_skills = merge_unique_skills(merged_skills, fallback_skills)

    sections["skills"] = merged_skills
    sections["cert_derived_skills"] = cert_skills
    sections["_raw_text"] = raw_text
    sections["_skill_sources"] = {
        "skills": merge_unique_skills(explicit_skill_items),
        "cert_derived": merge_unique_skills(cert_skills),
        "projects": merge_unique_skills(project_skills),
        "internships": merge_unique_skills(internship_skills),
        "work_experience": merge_unique_skills(work_skills),
        "fallback_full_text": merge_unique_skills(fallback_skills),
    }
    sections["_empty_sections"] = [
        key for key in (
            "skills", "projects", "certifications", "internships",
            "work_experience", "education", "achievements",
        ) if not sections.get(key)
    ]
    return sections
