"""JD noise filtering utility.

Strips non-technical boilerplate from job descriptions before analysis.
This runs as the first step in the JD Intelligence Engine pipeline.

Handles:
  - Section-level noise: "About Us", "Benefits", "Perks", "EEO",
    "Disclaimer", "How to Apply", "Company Overview", etc.
  - Inline noise: generic employer branding sentences, legal disclaimers.

Design principle: conservative removal. Only strips sections/sentences
that are high-confidence boilerplate. When in doubt, preserve the text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class NoiseSection:
    """A detected boilerplate section in the JD."""
    heading: str
    start_line: int
    end_line: int  # exclusive
    category: str  # e.g. "company_info", "benefits", "eeo", "application"


@dataclass
class FilteredJD:
    """Result of JD noise filtering."""
    clean_text: str
    removed_sections: List[str]
    noise_ratio: float  # fraction of original text removed (0.0–1.0)
    original_length: int
    clean_length: int


# ─── Section-level noise headings ───────────────────────────────────────────
# Maps category → list of heading patterns (matched case-insensitively).
# These patterns are anchored to the start of a line after stripping.

NOISE_SECTION_HEADINGS = {
    "company_info": [
        r"about\s+us",
        r"about\s+the\s+company",
        r"about\s+the\s+team",
        r"about\s+the\s+organization",
        r"company\s+overview",
        r"company\s+description",
        r"company\s+profile",
        r"our\s+company",
        r"our\s+mission",
        r"our\s+story",
        r"our\s+values",
        r"who\s+we\s+are",
        r"why\s+join\s+us",
        r"why\s+work\s+(?:with|for|at)\s+us",
        r"life\s+at\s+\w+",
        r"culture\s+at\s+\w+",
    ],
    "benefits": [
        r"benefits",
        r"compensation\s+and\s+benefits",
        r"compensation",
        r"salary\s+(?:range|details|information)",
        r"what\s+we\s+offer",
        r"perks",
        r"perks\s+and\s+benefits",
        r"employee\s+benefits",
        r"total\s+rewards",
    ],
    "eeo": [
        r"equal\s+(?:employment\s+)?opportunity",
        r"eeo\s+statement",
        r"diversity\s+(?:statement|and\s+inclusion)",
        r"non[\-\s]?discrimination",
        r"affirmative\s+action",
    ],
    "application": [
        r"how\s+to\s+apply",
        r"application\s+process",
        r"application\s+instructions",
        r"to\s+apply",
        r"apply\s+now",
        r"next\s+steps",
        r"interview\s+process",
        r"hiring\s+process",
    ],
    "disclaimer": [
        r"disclaimer",
        r"legal\s+notice",
        r"privacy\s+(?:notice|policy|statement)",
        r"note\s*:",
        r"important\s+note",
    ],
}

# Compile all heading patterns into a single dict of category → compiled regex
_COMPILED_NOISE_HEADINGS = {
    category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for category, patterns in NOISE_SECTION_HEADINGS.items()
}

# ─── Technical section headings (these are NEVER removed) ───────────────────
TECHNICAL_SECTION_HEADINGS = [
    re.compile(pattern, re.IGNORECASE) for pattern in [
        r"requirements?",
        r"required\s+skills?",
        r"required\s+qualifications?",
        r"qualifications?",
        # "Requirements And Qualification" appears as a single heading on
        # some JD templates; treat the combined form as a technical heading
        # so the noise filter (and any future role-title rejection list) can
        # recognize it explicitly.
        r"requirements?\s+and\s+qualifications?",
        r"skills?",
        r"technical\s+skills?",
        r"preferred\s+(?:skills?|qualifications?)",
        r"nice\s+to\s+have",
        r"must\s+have",
        r"key\s+responsibilities",
        r"responsibilities",
        r"job\s+responsibilities",
        r"role\s+(?:overview|description|summary)",
        r"job\s+description",
        r"job\s+summary",
        # "About the job" / "About the role" are JD-content markers used as
        # the opening line on platforms like LinkedIn. They are NOT
        # boilerplate (unlike "About us" / "About the company") — they
        # introduce the actual JD content.
        r"about\s+the\s+job",
        r"about\s+the\s+role",
        r"what\s+you(?:'ll| will)\s+(?:do|work\s+on)",
        r"what\s+we(?:'re| are)\s+looking\s+for",
        r"experience",
        r"experience\s+required",
        r"education",
        r"educational\s+requirements?",
        r"mandatory",
    ]
]

# ─── Inline noise patterns ──────────────────────────────────────────────────
# These match individual sentences/lines that are boilerplate even when
# not inside a recognized noise section.

INLINE_NOISE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in [
        r"we\s+are\s+an?\s+equal\s+opportunity\s+employer",
        r"all\s+qualified\s+applicants\s+will\s+receive\s+consideration",
        r"without\s+regard\s+to\s+race,?\s+color,?\s+religion",
        r"we\s+celebrate\s+diversity",
        r"we\s+value\s+diversity",
        r"we\s+are\s+committed\s+to\s+(?:creating\s+)?(?:a\s+)?diverse",
        r"accommodation\s+(?:is\s+)?available\s+(?:for\s+)?(?:applicants|candidates)",
        r"this\s+(?:job\s+)?(?:description|posting)\s+(?:is\s+)?(?:not\s+)?(?:intended\s+to\s+be\s+)?(?:an?\s+)?(?:exhaustive|complete)\s+list",
        r"salary\s+(?:range|is)\s+(?:commensurate|competitive|based\s+on)",
        r"we\s+offer\s+(?:a\s+)?competitive\s+(?:salary|compensation|benefits)",
        r"please\s+(?:apply|submit|send)\s+(?:your\s+)?(?:resume|cv|application)",
        r"interested\s+candidates\s+(?:are\s+)?(?:encouraged|invited)\s+to\s+apply",
    ]
]


def _strip_heading_decoration(line: str) -> str:
    """Remove decorative characters from a line for heading matching.

    Strips: #, *, =, -, >, ■, •, ●, leading/trailing colons, trailing :.
    """
    cleaned = re.sub(r"^[#*=>■•●\-\s]+", "", line)
    cleaned = re.sub(r"[#*=>■•●\-:\s]+$", "", cleaned)
    return cleaned.strip()


def _is_technical_heading(cleaned_line: str) -> bool:
    """Check if a heading matches a known technical section."""
    for pattern in TECHNICAL_SECTION_HEADINGS:
        if pattern.fullmatch(cleaned_line):
            return True
    return False


def _classify_heading(cleaned_line: str) -> str | None:
    """Classify a heading as a noise category, or None if not noise."""
    for category, patterns in _COMPILED_NOISE_HEADINGS.items():
        for pattern in patterns:
            if pattern.fullmatch(cleaned_line):
                return category
    return None


def _is_heading_line(line: str) -> bool:
    """Heuristic: is this line likely a section heading?

    Short lines (≤10 words) that don't start with a bullet and contain
    at least one alpha character are candidates.
    """
    stripped = line.strip()
    if not stripped:
        return False
    # Bullet lines are content, not headings
    if stripped[0] in "•-*▪■▫◦·⁃∙":
        return False
    cleaned = _strip_heading_decoration(stripped)
    if not cleaned:
        return False
    words = cleaned.split()
    if len(words) > 10:
        return False
    if not any(c.isalpha() for c in cleaned):
        return False
    return True


def _detect_noise_sections(text: str) -> List[NoiseSection]:
    """Identify contiguous boilerplate sections in the JD text.

    Scans line-by-line. When a noise heading is detected, all subsequent
    lines are marked as noise until a technical heading or another noise
    heading is encountered.
    """
    lines = text.split("\n")
    noise_sections: List[NoiseSection] = []
    current_noise: NoiseSection | None = None

    for i, line in enumerate(lines):
        if not _is_heading_line(line):
            continue

        cleaned = _strip_heading_decoration(line.strip())
        if not cleaned:
            continue

        # Check technical heading first — always terminates noise
        if _is_technical_heading(cleaned):
            if current_noise is not None:
                current_noise.end_line = i
                noise_sections.append(current_noise)
                current_noise = None
            continue

        # Check noise heading
        category = _classify_heading(cleaned)
        if category is not None:
            # Close previous noise section if any
            if current_noise is not None:
                current_noise.end_line = i
                noise_sections.append(current_noise)
            # Start new noise section
            current_noise = NoiseSection(
                heading=cleaned,
                start_line=i,
                end_line=len(lines),  # will be adjusted
                category=category,
            )

    # Close any open noise section at end of document
    if current_noise is not None:
        current_noise.end_line = len(lines)
        noise_sections.append(current_noise)

    return noise_sections


def _remove_inline_noise(text: str) -> str:
    """Remove individual boilerplate sentences/lines from text."""
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue
        is_noise = False
        for pattern in INLINE_NOISE_PATTERNS:
            if pattern.search(stripped):
                is_noise = True
                break
        if not is_noise:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def filter_jd_noise(text: str) -> FilteredJD:
    """Filter boilerplate noise from a job description.

    This is the main entry point for the noise filter. It:
    1. Detects and removes boilerplate sections (About Us, Benefits, etc.)
    2. Removes inline noise sentences (EEO statements, etc.)
    3. Collapses excessive whitespace in the result.

    Returns a FilteredJD with the clean text, list of removed sections,
    and the noise ratio (fraction of text that was removed).
    """
    if not isinstance(text, str) or not text.strip():
        return FilteredJD(
            clean_text="",
            removed_sections=[],
            noise_ratio=0.0,
            original_length=0,
            clean_length=0,
        )

    original_length = len(text.strip())

    # Step 1: Detect and remove noise sections
    noise_sections = _detect_noise_sections(text)
    lines = text.split("\n")
    removed_section_names: List[str] = []

    if noise_sections:
        # Build a set of line indices to remove
        remove_indices = set()
        for section in noise_sections:
            for idx in range(section.start_line, section.end_line):
                remove_indices.add(idx)
            removed_section_names.append(
                f"{section.category}: {section.heading}"
            )

        lines = [
            line for i, line in enumerate(lines) if i not in remove_indices
        ]

    section_cleaned = "\n".join(lines)

    # Step 2: Remove inline noise
    clean_text = _remove_inline_noise(section_cleaned)

    # Step 3: Collapse excessive blank lines
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

    clean_length = len(clean_text)
    noise_ratio = 1.0 - (clean_length / original_length) if original_length > 0 else 0.0

    return FilteredJD(
        clean_text=clean_text,
        removed_sections=removed_section_names,
        noise_ratio=round(noise_ratio, 4),
        original_length=original_length,
        clean_length=clean_length,
    )
