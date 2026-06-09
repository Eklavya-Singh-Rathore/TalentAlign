"""JD skill extraction + experience / education / rule detection.

Mines the JD text for required / preferred / optional skill phrases, then
extracts the structured experience and education requirements plus the
boolean rule flags that gate the scoring engine.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.utils.skill_normalization import (
    clean_jd_skill_phrases,
    filter_non_skill_phrases_pos,
    has_technical_signal,
    is_valid_jd_skill,
    normalize_phrase,
    normalize_skill,
)

from .constants import (
    GENERIC_SKIP_PHRASES,
    JOB_TITLE_WORDS,
    PREFERRED_CUES,
    REQUIRED_CUES,
)


def _ordered_unique(items: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for item in items:
        if item and item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def _normalize_skill_phrase(phrase: str) -> str:
    phrase = phrase.strip().lower()
    phrase = re.sub(r"\be\.?g\.?\b", " ", phrase)
    phrase = re.sub(r"[^a-z0-9\+#\./\- ]+", " ", phrase)
    # Phase 3 fix C: strip enumeration prefixes including "like" and
    # "such as" / "including" / "for example".
    phrase = re.sub(
        r"^(?:experience in|experience with|proficiency with|familiarity with|"
        r"proficient in|proficient with|proficiency in|"
        r"good knowledge of|deep understanding of|strong understanding of|"
        r"knowledge of|understanding of|expertise in|expertise with|"
        r"strong|good|solid|deep|hands-on|hands on|"
        r"tools and techniques|tools and technologies|tools|techniques|"
        r"such as|including|platforms such as|like|for example|e\.?g\.?)\s+",
        "",
        phrase,
    )
    # Phase 3 fix C: strip trailing enumeration / desirability markers
    # ("decision forests etc", "nosql is desired", "X is required", etc.)
    phrase = re.sub(
        r"\s+(?:etc\.?|and so on|and more|is\s+(?:desired|required|preferred|"
        r"nice to have|a plus|mandatory))\s*$",
        "",
        phrase,
    )
    phrase = re.sub(r"\b(?:required|preferred|capabilities|skills?)\b$", "", phrase)
    # Strip a stray trailing single letter (e.g. malformed source "web apis s"),
    # while preserving the real one-letter skills C and R.
    phrase = re.sub(r"\s+[a-bd-qs-z]$", "", phrase)
    phrase = re.sub(r"\s+", " ", phrase)
    return phrase.strip(" -:;,.")


_JD_NLP = None
_JD_NLP_ATTEMPTED = False


def _get_jd_nlp():
    global _JD_NLP, _JD_NLP_ATTEMPTED
    if _JD_NLP_ATTEMPTED:
        return _JD_NLP
    _JD_NLP_ATTEMPTED = True
    try:
        import spacy
        _JD_NLP = spacy.load("en_core_web_sm")
    except Exception:
        _JD_NLP = None
    return _JD_NLP


def _normalize_jd_skill_candidate(phrase: str) -> str:
    # Lightweight canonicalization used by finalize_bucket inside
    # extract_skills_from_jd.
    return normalize_skill(normalize_phrase(phrase))


def _looks_like_skill(phrase: str) -> bool:
    """Filter out non-skill phrases: generic words, job titles, noise."""
    phrase = _normalize_skill_phrase(phrase)
    if not phrase or phrase in GENERIC_SKIP_PHRASES:
        return False
    if len(phrase) < 2 or len(phrase) > 40:
        return False
    if len(phrase.split()) > 4:
        return False
    if not re.search(r"[a-z]", phrase):
        return False

    single_word_noise = {
        "of", "in", "and", "or", "the", "a", "an", "to", "for", "with",
        "on", "at", "by", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "can", "could", "should", "may", "might", "shall", "must",
        "not", "no", "yes", "if", "then", "than", "but", "so", "as",
        "about", "from", "into", "through", "during", "before", "after",
        "above", "below", "between", "under", "over", "up", "down",
        "out", "off", "such", "only", "also", "very", "just", "how",
        "all", "each", "every", "both", "few", "more", "most", "other",
        "some", "any", "many", "much", "own", "same", "new", "old",
        "good", "best", "strong", "skills", "data", "analysis",
        "deep", "platforms", "field", "work", "team", "tools",
    }
    if phrase in single_word_noise:
        return False

    words = phrase.split()
    title_word_count = sum(1 for w in words if w in JOB_TITLE_WORDS)
    if title_word_count >= len(words) * 0.5 and len(words) >= 2:
        return False
    if len(words) <= 3 and all(w in JOB_TITLE_WORDS for w in words):
        return False

    return is_valid_jd_skill(phrase)


def _extract_candidates_from_text(text: str) -> List[str]:
    candidates = []
    working = re.sub(r"[()]", ",", text)
    working = re.sub(r"\be\.g\.\b", " ", working, flags=re.IGNORECASE)
    # Split on enumeration markers ("databases like mysql", "frameworks such as
    # tensorflow") as well as list separators, so the category AND the example
    # survive as separate skills instead of leaking a fragment like
    # "databases like mysql" or dropping the example inside an over-long phrase.
    for chunk in re.split(r"\n|,|;|\||/| and | or | like | such as | including ", working):
        candidate = _normalize_skill_phrase(chunk)
        if _looks_like_skill(candidate):
            candidates.append(candidate)

    cleaned = clean_jd_skill_phrases(candidates)
    cleaned = filter_non_skill_phrases_pos(cleaned)
    return _ordered_unique(clean_jd_skill_phrases(cleaned))


def extract_skills_from_jd(text: str) -> Dict[str, List[str]]:
    """Extract required, preferred, and optional JD skills."""
    required_skills = []
    preferred_skills = []
    optional_seed_skills = []
    current_bucket = "optional"
    current_section = None
    found_section_heading = False
    # P7.3: True while inside an explicit skills/qualifications section. Inside
    # such a section, bullet/list lines are mined as skills even when they
    # lack the hardcoded anchor/positive-signal keywords (those keywords exist
    # to filter prose in responsibility/about sections, not skill lists).
    in_skill_section = False
    rejected_candidates: List[Dict[str, str]] = []
    lines = text.splitlines()
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if index == 0 and len(line.split()) <= 6 and not any(cue in lowered for cue in REQUIRED_CUES + PREFERRED_CUES):
            continue
        if lowered == "job description":
            continue
        if lowered in {"about us", "about the team"} or lowered.startswith("about us"):
            break
        # Non-skill section headers reset in_skill_section so their prose/list
        # content is not mined as skills (e.g. an "Eligibility" or
        # "Responsibilities" list that follows a skills section).
        if lowered.startswith("job responsibilities") or lowered == "responsibilities":
            current_bucket = "optional"
            current_section = "optional"
            found_section_heading = True
            in_skill_section = False
            continue
        if lowered.startswith("experience required"):
            current_section = None
            found_section_heading = True
            in_skill_section = False
            continue
        if lowered.startswith("education"):
            current_section = None
            in_skill_section = False
            continue
        # P3patch.A: expanded non-skill section headers. Corporate JDs
        # (e.g. Barclays JD-9) put responsibility/values prose under headings
        # like "Accountabilities", "Analyst Expectations", "Purpose of the
        # role" — none of which are skill lists. Hitting any of these resets
        # skill-mode so their prose is NOT mined as required skills.
        if lowered.startswith((
            "eligibility", "benefits", "perks", "what you", "who you",
            "why join", "accountabilit", "analyst expectation", "expectation",
            "purpose", "key responsibilit", "your responsibilit", "responsibilit",
            "role overview", "about the", "about us", "disclaimer", "values",
            "the barclays values", "our team", "company", "compensation",
            "location", "work mode", "day to day", "day-to-day",
            "what we offer", "what we look", "how to apply", "interview",
        )):
            current_bucket = "optional"
            current_section = "optional"
            found_section_heading = True
            in_skill_section = False
            continue
        if any(cue in lowered for cue in PREFERRED_CUES):
            current_bucket = "preferred"
            current_section = "preferred"
            found_section_heading = True
            in_skill_section = True
        elif any(cue in lowered for cue in REQUIRED_CUES):
            current_bucket = "required"
            current_section = "required"
            found_section_heading = True
            in_skill_section = True
        else:
            # Generic heading-break: a short, non-bullet line that carries no
            # skill cue and no technical signal is almost certainly a new
            # section header (e.g. "Accountabilities"). Reset skill-mode so an
            # earlier skills section doesn't bleed into it. Lines that look
            # like skill content (bullets, comma lists, tech signals) are left
            # alone so genuine multi-line skill lists keep flowing.
            if in_skill_section:
                is_bullet_line = raw_line.lstrip().startswith(("•", "-", "*"))
                word_count = len(line.split())
                has_tech = any(
                    sig in lowered for sig in (
                        "python", "sql", "java", "aws", "cloud", "data", "ml",
                        "api", "docker", "ml", "tensorflow", "pytorch", "react",
                        "analytics", "model", "pipeline", "framework", "tool",
                    )
                )
                if (not is_bullet_line) and word_count <= 5 and "," not in line and not has_tech:
                    in_skill_section = False

        if found_section_heading and not raw_line.lstrip().startswith(("•", "-", "*")):
            heading_words = re.sub(r"[^a-z ]+", " ", lowered).split()
            if len(heading_words) <= 8 and (
                any(cue in lowered for cue in REQUIRED_CUES + PREFERRED_CUES) or
                "capabilities" in lowered or "qualifications" in lowered
            ):
                continue

        if found_section_heading and current_section not in {"required", "preferred", "optional"}:
            continue

        is_bullet = raw_line.lstrip().startswith(("•", "-", "*"))
        has_skill_anchor = any(
            anchor in lowered for anchor in (
                "experience in", "experience with", "proficiency with",
                "familiarity with", "skills", "capabilities", "using",
                "utilizing", "such as", "tools", "techniques", "methodologies",
                "design and develop", "develop data", "etl", "bi tool",
            )
        )
        has_positive_signal = any(
            signal in lowered for signal in (
                "data ", "analytics", "sql", "tableau", "snowflake", "alteryx",
                "trifacta", "ab initio", "oracle", "teradata", "cloud",
                "aws", "azure", "gcp", "ai integration", "agile",
                "dashboard", "pipeline", "model", "reporting", "etl",
            )
        )
        # P7.3: inside an explicit skill section, accept LIST-LIKE lines
        # (bullets, comma-separated lists, or short phrases) even without
        # anchor/positive-signal keywords — these are skill lists. Long prose
        # sentences inside a skill section (e.g. "Proven experience as a
        # Machine Learning Engineer or similar role") still require an
        # anchor/signal so they don't leak fragments like "similar role".
        # Outside skill sections, the legacy gate always applies.
        is_list_like = is_bullet or ("," in line) or len(line.split()) <= 7
        if in_skill_section:
            if not is_list_like and not has_skill_anchor and not has_positive_signal:
                continue
        elif not has_skill_anchor and not has_positive_signal:
            continue

        working_line = line
        if ("looking for" in lowered or lowered.startswith("hiring")) and " with " in lowered:
            working_line = line.split(" with ", 1)[1]
        if ":" in working_line and any(cue in lowered for cue in REQUIRED_CUES + PREFERRED_CUES):
            working_line = working_line.split(":", 1)[1]
        line_candidates = _extract_candidates_from_text(working_line)
        cleaned_candidates = [c for c in line_candidates if c not in REQUIRED_CUES and c not in PREFERRED_CUES]
        if current_bucket == "preferred":
            preferred_skills.extend(cleaned_candidates)
        elif current_bucket == "required":
            required_skills.extend(cleaned_candidates)
        else:
            optional_seed_skills.extend(cleaned_candidates)

    def finalize_bucket(candidates: List[str], bucket: str, blocked: Optional[set] = None) -> List[str]:
        blocked = blocked or set()
        normalized = [normalize_phrase(item) for item in candidates if normalize_phrase(item)]
        pos_kept = set(filter_non_skill_phrases_pos(normalized))
        cleaned: List[str] = []
        for raw_candidate in normalized:
            canonical = _normalize_jd_skill_candidate(raw_candidate)
            if raw_candidate not in pos_kept:
                rejected_candidates.append({"phrase": raw_candidate, "bucket": bucket, "reason": "pos_filter"})
                continue
            if not is_valid_jd_skill(canonical):
                rejected_candidates.append({"phrase": raw_candidate, "bucket": bucket, "reason": "noise_filter"})
                continue
            if bucket == "optional" and not has_technical_signal(canonical):
                rejected_candidates.append({"phrase": raw_candidate, "bucket": bucket, "reason": "non_technical_optional"})
                continue
            if canonical in blocked or canonical in cleaned:
                continue
            cleaned.append(canonical)
        return cleaned

    required_skills = finalize_bucket(required_skills, "required")
    preferred_skills = finalize_bucket(preferred_skills, "preferred", blocked=set(required_skills))
    optional_candidates = optional_seed_skills + _extract_candidates_from_text(text)
    optional_skills = finalize_bucket(
        optional_candidates,
        "optional",
        blocked=set(required_skills) | set(preferred_skills),
    )
    return {
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "optional_skills": optional_skills,
        "_rejected_skill_candidates": rejected_candidates,
    }


def extract_experience_requirement(text: str) -> int:
    """Extract minimum required experience in years."""
    lowered = text.lower()
    patterns = [
        r"(\d+)\s*\+?\s*(?:to|-)??\s*(\d+)?\s+years? of experience",
        r"minimum\s+(\d+)\s+years?",
        r"at least\s+(\d+)\s+years?",
        r"(\d+)\s*\+\s*years?",
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            return int(match.group(1))
    direct_match = re.search(r"(\d+)\s*[-to]{0,3}\s*(\d+)?\s+years?", lowered)
    if direct_match:
        return int(direct_match.group(1))
    return 0


def extract_education_level(text: str) -> str:
    """Extract the highest mentioned education level."""
    lowered = text.lower()
    edu_patterns = {
        "phd": [r"\bph\.?d\b", r"doctorate"], "mba": [r"\bmba\b"],
        "master": [r"\bm\.?tech\b", r"\bm\.?e\b", r"master(?:'s)?", r"\bm\.s\b"],
        "bachelor": [r"\bb\.?tech\b", r"\bb\.?e\b", r"bachelor(?:'s)?", r"\bb\.s\b"],
    }
    for label, patterns in edu_patterns.items():
        if any(re.search(p, lowered) for p in patterns):
            return label
    return "not_specified"


def _detect_requires_academics(text: str) -> bool:
    """Trigger ONLY on explicit academic performance criteria."""
    lowered = text.lower()
    performance_patterns = [
        r"minimum\s+(?:cgpa|gpa)",
        r"(?:cgpa|gpa)\s+(?:of|above|greater|minimum|required|at\s+least)",
        r"(?:cgpa|gpa)\s*[>:]\s*\d",
        r"academic\s+(?:score|criteria|requirement)",
        r"percentage\s+(?:above|of|required|minimum|at\s+least)\s+\d",
        r"marks\s+(?:above|of|required|minimum|at\s+least)\s+\d",
        r"\bminimum\s+\d+%\s+(?:marks|throughout|aggregate|academics)\b",
        r"\b\d+%\s+(?:marks|throughout|aggregate|academics)\b",
        r"first\s+class\s+(?:degree|honours?)",
        r"distinction\s+required",
        r"consistent\s+academic\s+performance",
    ]
    return any(re.search(pattern, lowered) for pattern in performance_patterns)


def _detect_requires_achievements(text: str) -> bool:
    """Detect explicit achievement emphasis in the JD."""
    lowered = text.lower()
    achievement_patterns = [
        r"publication[s]?\s+(?:required|preferred)",
        r"research\s+paper[s]?\s+(?:required|preferred)",
        r"hackathon\s+winner",
        r"competitive\s+programming\s+(?:required|preferred)",
        r"coding\s+competition\s+(?:required|preferred)",
        r"achievement[s]?\s+(?:required|preferred)",
        r"award[s]?\s+(?:required|preferred)",
    ]
    return any(re.search(pattern, lowered) for pattern in achievement_patterns)
