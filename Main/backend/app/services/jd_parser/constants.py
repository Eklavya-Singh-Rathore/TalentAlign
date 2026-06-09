"""Shared data constants for JD parsing.

Section cues, domain keyword maps, job-title noun set, seniority taxonomies.
Pure data — no logic.
"""

from __future__ import annotations


REQUIRED_CUES = [
    "required", "must have", "requirements", "qualifications", "mandatory", "skills:",
    # P7.3: explicit skill-section headers so JDs that list skills under
    # these headings (rather than "Required Skills") still populate the
    # required bucket. "core skills:" already matched via "skills:", but the
    # no-colon variants need explicit entries.
    "core skills", "key skills", "technical skills", "skills required",
    # P3patch.A: skill-list INTRO phrases that introduce a required-skill
    # list in prose-style JDs (e.g. Barclays JD-9 "...you should possess the
    # following skills:"). Without these the real skills (Python/SAS/SQL)
    # never enter required-skill mode.
    "following skills", "should possess", "you will need", "you should have",
    "you should be proficient", "what you bring", "what we are looking for",
    "what we're looking for",
]
PREFERRED_CUES = [
    "preferred", "nice to have", "good to have", "plus", "bonus", "preferred skills",
    # P3patch.A: "Some other highly valued skills include:" style intros.
    "valued skills", "desired skills", "desirable", "good to have skills",
]
GENERIC_SKIP_PHRASES = {
    "job description", "role overview", "key responsibilities",
    "responsibilities", "requirements", "required skills",
    "preferred skills", "education", "experience", "related field",
}

DOMAIN_KEYWORDS = {
    "data_science": ["data science", "machine learning", "deep learning", "statistics", "analytics", "data analysis"],
    # P3patch.C: expanded software_dev signals. JD-6 ("Software Development
    # Engineer at Clearwater Analytics") was misread as data_science because
    # only "analytics" (a company-name fragment) matched. These terms give the
    # software-engineering signal proper weight.
    "software_dev": [
        "software developer", "software engineer", "software development",
        "software application", "full stack", "fullstack", "backend",
        "back-end", "frontend", "front-end", "web development", "api development",
        "java developer", "spring boot", "object-oriented", "object oriented",
        "microservices", "rest api", "design patterns", "ci/cd",
        "software design", "development engineer", "developer",
    ],
    "business": ["business analysis", "business analyst", "mba", "market research", "operations", "strategy", "finance"],
    "freshers": ["fresher", "entry level", "campus hire", "graduate trainee", "0 years"],
    # Phase 2: expanded domains
    "devops": ["devops", "site reliability", "sre", "infrastructure", "ci/cd", "kubernetes", "docker", "terraform", "cloud infrastructure"],
    "cybersecurity": ["cybersecurity", "security analyst", "penetration testing", "soc", "threat", "vulnerability", "infosec", "information security"],
    "product_management": ["product manager", "product management", "product owner", "product strategy", "roadmap", "stakeholder management"],
    "design": ["ui/ux", "ux design", "ui design", "user experience", "user interface", "figma", "sketch", "design system", "interaction design"],
}

JOB_TITLE_WORDS = {
    "engineer", "developer", "analyst", "scientist", "manager", "lead",
    "senior", "junior", "associate", "intern", "trainee", "consultant",
    "architect", "director", "head", "chief", "officer", "specialist",
    "coordinator", "executive", "administrator", "designer", "researcher",
    "hiring", "looking",
}


# ─── Phase 2: Seniority detection constants ─────────────────────────────────

SENIORITY_LEVELS = ["intern", "junior", "mid", "senior", "lead", "executive"]

# Explicit seniority keywords in JD text (case-insensitive match)
SENIORITY_KEYWORD_MAP = {
    "intern": [
        "intern", "internship", "trainee", "apprentice",
        "co-op", "coop", "student position",
    ],
    "junior": [
        "junior", "entry level", "entry-level", "fresher",
        "associate", "graduate", "new grad", "campus hire",
        "early career", "0-1 year", "0-2 year",
    ],
    "mid": [
        "mid level", "mid-level", "intermediate",
        "2-5 year", "3-5 year", "2+ year", "3+ year",
    ],
    "senior": [
        "senior", "sr.", "sr ", "experienced",
        "5+ year", "5-8 year", "6+ year", "7+ year",
        "8+ year", "senior level",
    ],
    "lead": [
        "lead", "tech lead", "team lead", "principal",
        "staff", "staff engineer", "distinguished",
        "10+ year", "8-12 year", "9+ year",
    ],
    "executive": [
        "director", "vp ", "vice president", "head of",
        "chief", "cto", "cio", "ciso",
        "executive", "c-level", "c-suite",
        "15+ year", "12+ year",
    ],
}

# Seniority prefixes commonly found in role titles
SENIORITY_TITLE_PREFIXES = {
    "intern": ["intern"],
    "junior": ["junior", "jr", "jr.", "associate"],
    "mid": [],  # mid-level rarely appears as a title prefix
    "senior": ["senior", "sr", "sr."],
    "lead": ["lead", "principal", "staff", "distinguished"],
    "executive": ["director", "vp", "vice president", "head", "chief"],
}
