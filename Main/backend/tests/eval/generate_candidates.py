"""Sub-phase 1.12 — generate candidate pairs for hand-labeling.

Runs the existing matcher on the cross-test matrix (2 resumes × 5 JDs) and
exports every borderline pair as a JSONL row. A pair is "borderline" when:
  * it landed in `matched` with cosine in [LOW, HIGH] AND tier in
    {semantic, partial}, OR
  * it landed in `debug.rejected_matches` with cosine in [LOW, HIGH].

The user then opens the output JSONL, marks each row with
``"label": "true_match"`` or ``"label": "false_match"``, and saves as
``gold_labels.jsonl`` for ``run_eval.py``.

Run:
    python tests/eval/generate_candidates.py \
        [--low 0.40] [--high 0.80] [--out tests/eval/candidates.jsonl]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.jd_parser import parse_jd
from app.services.resume_parser import parse_resume
from app.services.skill_matcher import (
    LLM_VALIDATE_HIGH,
    LLM_VALIDATE_LOW,
    match_skills,
    run_skill_extraction_pipeline,
)
from app.utils.embeddings import get_embedding_provider
from app.utils.file_handling import extract_text_from_docx
from app.utils.skill_normalization import DebugLog

from tests.eval.eval_io import CandidateRow, write_jsonl


FIXTURES = BACKEND_ROOT / "tests" / "fixtures"


def _discover():
    """Discover all resumes (*.pdf) and JDs (JD_N / JD-N) under fixtures."""
    import glob
    import os
    import re
    resumes = {}
    for f in sorted(glob.glob(str(FIXTURES / "*.pdf"))):
        name = os.path.basename(f).split("_Resume")[0].split(" ")[0].replace(".pdf", "")
        resumes[name] = Path(f)
    def jd_key(p):
        m = re.search(r"JD[_-](\d+)", os.path.basename(p))
        return int(m.group(1)) if m else 999
    jds = {}
    for f in sorted(glob.glob(str(FIXTURES / "JD*.docx")), key=jd_key):
        name = os.path.basename(f).replace(".docx", "").replace("_", "-")
        jds[name] = Path(f)
    return resumes, jds


RESUMES, JDS = _discover()


def collect_candidates(low: float, high: float):
    """Run cross-test matrix and yield CandidateRow objects for the band."""
    provider = get_embedding_provider()
    seen = set()
    for r_name, r_path in RESUMES.items():
        parsed = parse_resume(str(r_path))
        for j_name, j_path in JDS.items():
            jd_text = extract_text_from_docx(str(j_path))
            parsed_jd = parse_jd(jd_text)
            # Use run_skill_extraction_pipeline to populate the same JD entries
            # and resume phrases the real matcher sees.
            dbg = DebugLog()
            result = run_skill_extraction_pipeline(
                parsed, parsed_jd, kw=None, provider=provider, debug=dbg
            )
            # 1. Borderline matched pairs in semantic/partial tiers.
            for m in result["matched"]:
                if m.get("match_type") not in ("semantic", "partial"):
                    continue
                sim = float(m.get("similarity", 0.0) or 0.0)
                if not (low <= sim <= high):
                    continue
                key = (r_name, j_name, m["resume_phrase"], m["jd_phrase"])
                if key in seen:
                    continue
                seen.add(key)
                yield CandidateRow(
                    resume=r_name, jd=j_name,
                    resume_phrase=m["resume_phrase"],
                    jd_phrase=m["jd_phrase"],
                    cosine=round(sim, 4),
                    token_overlap=round(float(m.get("token_overlap", 0.0) or 0.0), 4),
                    current_match_type=m["match_type"],
                )
            # 2. Rejected matches in the band (matcher considered but dropped).
            for r in dbg.rejected_matches:
                sim = float(r.get("similarity", 0.0) or 0.0)
                if not (low <= sim <= high):
                    continue
                key = (r_name, j_name, r["resume_phrase"], r["jd_phrase"])
                if key in seen:
                    continue
                seen.add(key)
                yield CandidateRow(
                    resume=r_name, jd=j_name,
                    resume_phrase=r["resume_phrase"],
                    jd_phrase=r["jd_phrase"],
                    cosine=round(sim, 4),
                    token_overlap=round(float(r.get("token_overlap", 0.0) or 0.0), 4),
                    current_match_type="rejected",
                )


def main() -> int:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--low", type=float, default=0.40,
                    help="lower cosine bound (default: 0.40)")
    ap.add_argument("--high", type=float, default=0.80,
                    help="upper cosine bound (default: 0.80)")
    ap.add_argument("--out", type=Path, default=HERE / "candidates.jsonl",
                    help="output JSONL path")
    args = ap.parse_args()

    rows = list(collect_candidates(args.low, args.high))
    n = write_jsonl(args.out, rows)
    # Quick distribution summary
    by_type = {}
    for r in rows:
        by_type[r.current_match_type] = by_type.get(r.current_match_type, 0) + 1
    by_cell = {}
    for r in rows:
        k = f"{r.resume}×{r.jd}"
        by_cell[k] = by_cell.get(k, 0) + 1
    print(f"Wrote {n} candidate rows to {args.out}")
    print(f"Band: [{args.low}, {args.high}]   Backend: {get_embedding_provider().backend}")
    print("By match_type:", by_type)
    print(f"By cell: {len(by_cell)} cells, "
          f"min={min(by_cell.values(), default=0)}, "
          f"max={max(by_cell.values(), default=0)}, "
          f"mean={sum(by_cell.values()) / max(len(by_cell), 1):.1f}")
    print()
    print("Next step: edit the JSONL, set 'label' to 'true_match' or 'false_match'")
    print("for each row, then save as tests/eval/gold_labels.jsonl and run run_eval.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
