"""Duration extraction utility.

Extracts duration in months from text entries in resumes:
- Explicit durations: "3 months", "1.5 years", "8 weeks"
- Date ranges: "Jan 2023 - Jun 2023", "March 2022 to Present"
- Duration classification: short (<3 months), medium (3-6), long (>6)

Ported from Code/app_logic.py (_extract_duration_months, _get_duration_factor)
with Phase 3 improvements:
  - Better Unicode dash handling (pre-normalized by Phase 1 text_cleaning)
  - Season-based date detection ("Summer 2023")
  - Aggregated duration across multiple entries
  - Structured DurationResult output
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class DurationResult:
    """Result of duration extraction from a single entry."""
    months: Optional[float]           # Duration in months (None = not detected)
    classification: str               # short/medium/long/unknown
    raw_text: str                     # The source text
    extraction_method: str            # explicit/date_range/season/none


@dataclass
class AggregatedDuration:
    """Aggregated duration across multiple entries."""
    total_months: float
    entry_count: int
    longest_entry_months: float
    entries: List[DurationResult]
    classification: str               # short/medium/long/unknown


# Duration classification thresholds (in months)
DURATION_SHORT_MAX = 3.0
DURATION_MEDIUM_MAX = 6.0

DURATION_FACTORS = {"short": 0.7, "medium": 0.85, "long": 1.0, "unknown": 0.6}

# Month name → number mapping
MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}

# Season → approximate month mapping (start month)
SEASON_MAP = {
    "spring": 3, "summer": 5, "fall": 9, "autumn": 9, "winter": 12,
}


def _normalize_dashes(text: str) -> str:
    """Normalize various dash characters to ASCII hyphen.

    Phase 1 text_cleaning already handles most Unicode dashes in resume
    text, but JD/raw text may still contain them.
    """
    return (
        text
        .replace("\u2013", "-")   # en-dash
        .replace("\u2014", "-")   # em-dash
        .replace("\u2012", "-")   # figure dash
        .replace("\u2015", "-")   # horizontal bar
        .replace("\u00e2\u20ac\u201c", "-")  # mojibake en-dash
        .replace("\u00e2\u20ac\u201d", "-")  # mojibake em-dash
    )


def extract_duration_months(text: str) -> DurationResult:
    """Extract duration in months from a single text entry.

    Tries multiple strategies in order:
    1. Explicit duration ("3 months", "1.5 years", "8 weeks")
    2. Date range ("Jan 2023 - Jun 2023", "March 2022 to Present")
    3. Season-based ("Summer 2023")

    Args:
        text: A single resume entry string (e.g., an internship or
              work experience bullet/paragraph).

    Returns:
        DurationResult with extracted months and classification.
    """
    if not text or not text.strip():
        return DurationResult(
            months=None,
            classification="unknown",
            raw_text=text or "",
            extraction_method="none",
        )

    text_lower = _normalize_dashes(text.lower())

    # Strategy 1: Explicit duration mentions
    # Match "3 months", "1.5 years", "8 weeks"
    m = re.search(r"(\d+\.?\d*)\s*months?", text_lower)
    if m:
        months = float(m.group(1))
        return DurationResult(
            months=months,
            classification=_classify_duration(months),
            raw_text=text,
            extraction_method="explicit",
        )

    y = re.search(r"(\d+\.?\d*)\s*years?", text_lower)
    if y:
        months = float(y.group(1)) * 12
        return DurationResult(
            months=months,
            classification=_classify_duration(months),
            raw_text=text,
            extraction_method="explicit",
        )

    w = re.search(r"(\d+\.?\d*)\s*weeks?", text_lower)
    if w:
        months = float(w.group(1)) / 4.0
        return DurationResult(
            months=months,
            classification=_classify_duration(months),
            raw_text=text,
            extraction_method="explicit",
        )

    # Strategy 2: Date range ("Jan 2023 - Jun 2023", "March 2022 to Present")
    date_pattern = (
        r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
        r"dec(?:ember)?)\s*[',]?\s*(\d{4})\s*(?:[^\w]+|to|through|until)\s*"
        r"(?:(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
        r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
        r"dec(?:ember)?)\s*[',]?\s*(\d{4})|present|current|ongoing)"
    )
    dm = re.search(date_pattern, text_lower)
    if dm:
        start_month_name = dm.group(1)
        start_month = MONTH_MAP.get(start_month_name, MONTH_MAP.get(start_month_name[:3], 1))
        start_year = int(dm.group(2))

        if dm.group(3):
            end_month_name = dm.group(3)
            end_month = MONTH_MAP.get(end_month_name, MONTH_MAP.get(end_month_name[:3], 1))
            end_year = int(dm.group(4))
        else:
            # "present" / "current" / "ongoing"
            now = datetime.now()
            end_month, end_year = now.month, now.year

        months = (end_year - start_year) * 12 + (end_month - start_month)
        months = max(float(months), 1.0)

        return DurationResult(
            months=months,
            classification=_classify_duration(months),
            raw_text=text,
            extraction_method="date_range",
        )

    # Strategy 3: Season-based ("Summer 2023 Intern")
    season_pattern = r"(spring|summer|fall|autumn|winter)\s*(\d{4})"
    sm = re.search(season_pattern, text_lower)
    if sm:
        # Assume 3-month season
        months = 3.0
        return DurationResult(
            months=months,
            classification=_classify_duration(months),
            raw_text=text,
            extraction_method="season",
        )

    # No duration found
    return DurationResult(
        months=None,
        classification="unknown",
        raw_text=text,
        extraction_method="none",
    )


def _classify_duration(months: float) -> str:
    """Classify duration into short/medium/long."""
    if months < DURATION_SHORT_MAX:
        return "short"
    elif months <= DURATION_MEDIUM_MAX:
        return "medium"
    return "long"


def get_duration_factor(months: Optional[float]) -> float:
    """Get the scoring factor for a duration.

    Maps:
      short  (<3 months)  → 0.7
      medium (3-6 months) → 0.85
      long   (>6 months)  → 1.0
      unknown (None)      → 0.6
    """
    if months is None:
        return DURATION_FACTORS["unknown"]
    classification = _classify_duration(months)
    return DURATION_FACTORS[classification]


def aggregate_durations(entries: List[str]) -> AggregatedDuration:
    """Extract and aggregate durations across multiple entries.

    Args:
        entries: List of resume entry strings (internship or work experience).

    Returns:
        AggregatedDuration with total months, longest entry, and per-entry results.
    """
    results = [extract_duration_months(entry) for entry in entries]
    valid_results = [r for r in results if r.months is not None]

    if not valid_results:
        return AggregatedDuration(
            total_months=0.0,
            entry_count=len(entries),
            longest_entry_months=0.0,
            entries=results,
            classification="unknown",
        )

    total = sum(r.months for r in valid_results)
    longest = max(r.months for r in valid_results)

    return AggregatedDuration(
        total_months=round(total, 2),
        entry_count=len(entries),
        longest_entry_months=round(longest, 2),
        entries=results,
        classification=_classify_duration(total),
    )


def count_roles(entries: List[str]) -> int:
    """Number of distinct roles in a flat experience-entry list.

    Uses date-range lines as anchors (resumes list one date range per role), so
    a role's title + bullet lines count once rather than inflating the tally.
    Falls back to 1 when entries exist but no date range is machine-detectable,
    so a single undated role still counts as one (never zero when non-empty).
    """
    if not entries:
        return 0
    anchors = sum(
        1 for e in entries
        if extract_duration_months(e).extraction_method == "date_range"
    )
    return anchors if anchors > 0 else 1
