"""Phase 1 regression baseline.

Runs both the OLD parser pipeline (Code/app_logic.py) and the NEW one
(Main/backend/app/services/) on the fixtures in tests/fixtures/, then prints
a side-by-side diff of resume sections and JD fields.

Why subprocess for OLD: the legacy module imports SBERT/KeyBERT at
module-load time and uses a different package layout (the legacy
Code/cpps_core.py sits next to Code/app_logic.py). Isolating it in a
subprocess keeps the new (TalentAlign) module's imports clean.

Run from anywhere:
    python Main/backend/tests/regression_baseline.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent                                  # Main/backend
PROJECT_ROOT = BACKEND_ROOT.parent.parent                   # repo root
OLD_DIR = PROJECT_ROOT / "Code"                             # legacy baseline
FIXTURES = HERE / "fixtures"

RESUME_PDF = FIXTURES / "Eklavya_Singh_Rathore_Resume.pdf"
# JD.docx was renamed to JD_1.docx when the benchmark dataset (JD_1..JD_5)
# was added. The regression baseline tracks the original JD against the OLD
# pipeline, so it continues to use JD_1.docx (formerly JD.docx).
JD_DOCX = FIXTURES / "JD_1.docx"


def run_new() -> Dict[str, Any]:
    sys.path.insert(0, str(BACKEND_ROOT))
    from app.services.resume_parser import parse_resume
    from app.services.jd_parser import parse_jd
    from app.utils.file_handling import extract_text_from_docx

    jd_text = extract_text_from_docx(str(JD_DOCX))
    out = {
        "resume": parse_resume(str(RESUME_PDF)),
        "jd": parse_jd(jd_text),
        "jd_text": jd_text,
    }
    out["resume"].pop("_raw_text", None)
    out["jd"].pop("raw_text", None)
    return out


def run_old() -> Dict[str, Any]:
    """Run the OLD pipeline in a subprocess to keep imports isolated.

    The OLD module imports keybert + sentence_transformers at module-load
    time, and the parse_resume/parse_jd code paths only use SBERT in
    detect_domain's optional fallback (which already degrades gracefully
    when SBERT signal is weak). To avoid forcing the user to install ~2 GB
    of torch + transformers just for a parser regression check, we stub
    keybert and sentence_transformers with no-op classes before importing
    app_logic.
    """
    code = (
        "import json, sys, types\n"
        "\n"
        "class _DummySBERT:\n"
        "    def __init__(self, *a, **kw): pass\n"
        "    def encode(self, *a, **kw):\n"
        "        import numpy as np\n"
        "        return np.zeros((1, 384), dtype='float32')\n"
        "\n"
        "class _DummyKeyBERT:\n"
        "    def __init__(self, *a, **kw): pass\n"
        "    def extract_keywords(self, *a, **kw): return []\n"
        "\n"
        "class _DummyUtil:\n"
        "    @staticmethod\n"
        "    def cos_sim(a, b):\n"
        "        class _Tensor:\n"
        "            def item(self): return 0.0\n"
        "        return _Tensor()\n"
        "\n"
        "for name, attrs in (\n"
        "    ('keybert', {'KeyBERT': _DummyKeyBERT}),\n"
        "    ('sentence_transformers', {\n"
        "        'SentenceTransformer': _DummySBERT, 'util': _DummyUtil\n"
        "    }),\n"
        "):\n"
        "    mod = types.ModuleType(name)\n"
        "    for k, v in attrs.items(): setattr(mod, k, v)\n"
        "    sys.modules[name] = mod\n"
        "\n"
        f"sys.path.insert(0, r'{OLD_DIR}')\n"
        "import app_logic\n"
        "from app_logic import parse_resume, parse_jd, extract_text_from_docx\n"
        f"jd_text = extract_text_from_docx(r'{JD_DOCX}')\n"
        f"resume = parse_resume(r'{RESUME_PDF}')\n"
        "jd = parse_jd(jd_text)\n"
        "resume.pop('_raw_text', None)\n"
        "jd.pop('raw_text', None)\n"
        "print('---JSON_START---')\n"
        "print(json.dumps({'resume': resume, 'jd': jd, 'jd_text': jd_text}, default=str))\n"
        "print('---JSON_END---')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        sys.stderr.write("\n[OLD pipeline failed]\n")
        sys.stderr.write(proc.stderr)
        raise SystemExit(1)
    out = proc.stdout
    start = out.index("---JSON_START---") + len("---JSON_START---")
    end = out.index("---JSON_END---")
    return json.loads(out[start:end].strip())


def _as_sorted_set(v):
    if isinstance(v, list):
        return sorted({str(x) for x in v})
    return v


_MOJIBAKE_CHARS = "•●▪■○◦·–—‐‑‒―−�"  # bullets, dashes, replacement char
_MOJIBAKE_RE = None  # lazily built


def _canonical_for_compare(value: Any) -> Any:
    """Normalize bullets/dashes so OLD mojibake and NEW ASCII compare equal.

    We map "" (cp1252 misdecode), Unicode bullets, and dash variants to a
    single ASCII "-" and collapse whitespace, so the diff surfaces only
    true content differences rather than P1.2 cosmetic wins.
    """
    if isinstance(value, str):
        global _MOJIBAKE_RE
        if _MOJIBAKE_RE is None:
            import re as _re
            _MOJIBAKE_RE = _re.compile(rf"[{_MOJIBAKE_CHARS}]")
        v = _MOJIBAKE_RE.sub("-", value)
        import re as _re
        v = _re.sub(r"\s+", " ", v).strip()
        # Drop a single leading "- " so "- X" and "X" both reduce to "X"
        if v.startswith("- "):
            v = v[2:]
        return v
    if isinstance(value, list):
        return [_canonical_for_compare(x) for x in value]
    return value


def diff_section(label: str, key: str, old: Any, new: Any) -> None:
    if isinstance(old, list) or isinstance(new, list):
        old_set = set(old or [])
        new_set = set(new or [])
        if old_set == new_set:
            print(f"  [SAME]   {key}: {len(new_set)} items")
            return
        # Normalize cosmetic differences (mojibake bullets/dashes vs ASCII)
        old_canon = set(_canonical_for_compare(list(old or [])))
        new_canon = set(_canonical_for_compare(list(new or [])))
        if old_canon == new_canon:
            print(f"  [COSMETIC] {key}: {len(new_set)} items (formatting-only changes)")
            return
        added = sorted(new_canon - old_canon)
        removed = sorted(old_canon - new_canon)
        print(f"  [DIFF]   {key}: +{len(added)} / -{len(removed)} (after formatting normalization)")
        if added:
            print(f"           added:   {added[:20]}")
        if removed:
            print(f"           removed: {removed[:20]}")
    else:
        if old == new:
            print(f"  [SAME]   {key}: {new!r}")
        else:
            old_c = _canonical_for_compare(old)
            new_c = _canonical_for_compare(new)
            if old_c == new_c:
                print(f"  [COSMETIC] {key}: {new!r}")
                return
            print(f"  [DIFF]   {key}")
            print(f"           old: {old!r}")
            print(f"           new: {new!r}")


def main() -> int:
    print(f"Fixtures: {FIXTURES}")
    print(f"  resume: {RESUME_PDF.name}")
    print(f"  jd:     {JD_DOCX.name}")
    print()

    print("Running NEW pipeline ...")
    new = run_new()
    print("Running OLD pipeline (subprocess; may load SBERT/KeyBERT) ...")
    old = run_old()

    print()
    print("=" * 70)
    print("RESUME comparison")
    print("=" * 70)
    for key in (
        "skills", "projects", "certifications", "cert_derived_skills",
        "internships", "work_experience", "education", "achievements",
        "_empty_sections",
    ):
        diff_section("resume", key, old["resume"].get(key), new["resume"].get(key))

    print()
    print("=" * 70)
    print("JD comparison")
    print("=" * 70)
    for key in (
        "required_skills", "preferred_skills", "optional_skills",
        "experience_years", "education_level", "role_title",
        "domain_detected",
    ):
        diff_section("jd", key, old["jd"].get(key), new["jd"].get(key))

    print()
    print("=" * 70)
    print("JD rules comparison")
    print("=" * 70)
    old_rules = old["jd"].get("rules", {}) or {}
    new_rules = new["jd"].get("rules", {}) or {}
    for key in sorted(set(old_rules) | set(new_rules)):
        diff_section("rules", key, old_rules.get(key), new_rules.get(key))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
