"""Sub-phase 1.14 — evaluation harness.

Reads ``gold_labels.jsonl`` (one labeled pair per row), runs the matcher
twice for each unique (resume × JD) referenced:

  * **Baseline**: ``llm_provider=None`` — the deterministic matcher as it
    stands today.
  * **LLM-gated**: ``llm_provider=get_llm_provider()`` — the validation gate
    enabled. The active LLM backend depends on ``LLM_BACKEND`` env (none,
    mock, ollama, groq).

For each gold-labeled pair, asks: did the matcher include it in
``matched``? Compares to the gold label and tallies TP/FP/TN/FN.

Reports for both runs:
  * precision, recall, F1, FP-rate, FN-rate
  * mean LLM cost per analysis (USD), mean LLM latency (s) when active
  * delta vs baseline

Run:
    python tests/eval/run_eval.py [--gold path] [--out report.md]

Environment:
    LLM_BACKEND  none | mock | ollama | groq   (default: auto)
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
BACKEND_ROOT = HERE.parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.jd_parser import parse_jd
from app.services.resume_parser import parse_resume
from app.services.skill_matcher import run_skill_extraction_pipeline
from app.utils.embeddings import get_embedding_provider
from app.utils.file_handling import extract_text_from_docx
from app.utils.llm import LLMUsage, get_llm_provider, reset_default_provider

from tests.eval.eval_io import GoldRow, LABEL_FALSE, LABEL_TRUE, read_jsonl


FIXTURES = BACKEND_ROOT / "tests" / "fixtures"
RESUMES = {
    "Eklavya": FIXTURES / "Eklavya_Singh_Rathore_Resume.pdf",
    "Vignesh": FIXTURES / "VIGNESH B_Resume.pdf",
}
JDS = {f"JD_{i}": FIXTURES / f"JD_{i}.docx" for i in range(1, 6)}


# ─── Confusion / metrics ────────────────────────────────────────────────────


@dataclass
class Confusion:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0

    @property
    def total(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return (2 * p * r / (p + r)) if (p + r) else 0.0

    @property
    def fp_rate(self) -> float:
        denom = self.fp + self.tn
        return self.fp / denom if denom else 0.0

    @property
    def fn_rate(self) -> float:
        denom = self.fn + self.tp
        return self.fn / denom if denom else 0.0


def classify(predicted_match: bool, gold_label: str) -> str:
    is_true = (gold_label == LABEL_TRUE)
    if predicted_match and is_true:
        return "tp"
    if predicted_match and not is_true:
        return "fp"
    if not predicted_match and is_true:
        return "fn"
    return "tn"


# ─── Eval ────────────────────────────────────────────────────────────────────


def _resume_path(name: str) -> Path:
    if name in RESUMES:
        return RESUMES[name]
    raise KeyError(f"Unknown resume fixture: {name!r} (have {list(RESUMES)})")


def _jd_path(name: str) -> Path:
    if name in JDS:
        return JDS[name]
    raise KeyError(f"Unknown JD fixture: {name!r} (have {list(JDS)})")


def _matched_pair_set(result: Dict) -> set:
    """Set of (resume_phrase, jd_phrase) tuples in the result's matched list."""
    return {(m["resume_phrase"], m["jd_phrase"]) for m in result["matched"]}


def evaluate(
    gold: List[GoldRow],
    *,
    with_llm: bool,
) -> Tuple[Confusion, Dict, LLMUsage, float]:
    """Run the matcher across all (resume, jd) cells in the gold set.

    Returns (confusion, per_cell_results, llm_usage, mean_latency_s).
    """
    confusion = Confusion()
    per_cell: Dict[str, Dict] = {}

    # Group gold rows by (resume, jd) to avoid redundant matcher runs.
    cells: Dict[Tuple[str, str], List[GoldRow]] = defaultdict(list)
    for row in gold:
        cells[(row.resume, row.jd)].append(row)

    provider_embed = get_embedding_provider()
    if with_llm:
        # Reset provider so usage counters start clean.
        reset_default_provider()
        llm_provider = get_llm_provider()
    else:
        llm_provider = None

    latencies: List[float] = []
    for (resume_name, jd_name), rows in sorted(cells.items()):
        parsed = parse_resume(str(_resume_path(resume_name)))
        jd_text = extract_text_from_docx(str(_jd_path(jd_name)))
        parsed_jd = parse_jd(jd_text)

        t0 = time.perf_counter()
        result = run_skill_extraction_pipeline(
            parsed, parsed_jd, kw=None, provider=provider_embed,
        )
        # The pipeline calls match_skills internally without llm_provider.
        # Re-run match_skills directly on the same inputs to apply the gate.
        if with_llm and llm_provider is not None:
            from app.services.skill_matcher import match_skills
            gate_t0 = time.perf_counter()
            gated = match_skills(
                result["resume_skill_phrases"],
                result["jd_skill_entries"],
                provider=provider_embed,
                llm_provider=llm_provider,
            )
            latencies.append(time.perf_counter() - gate_t0)
            matched_pairs = _matched_pair_set(gated)
        else:
            latencies.append(time.perf_counter() - t0)
            matched_pairs = _matched_pair_set(result)

        cell_key = f"{resume_name}×{jd_name}"
        cell_record = {"tp": [], "fp": [], "tn": [], "fn": []}
        for row in rows:
            predicted = (row.resume_phrase, row.jd_phrase) in matched_pairs
            verdict = classify(predicted, row.label)
            setattr(confusion, verdict, getattr(confusion, verdict) + 1)
            cell_record[verdict].append(
                f"{row.resume_phrase!r} ↔ {row.jd_phrase!r}"
            )
        per_cell[cell_key] = cell_record

    usage = llm_provider.usage if (with_llm and llm_provider is not None) else LLMUsage()
    mean_latency = sum(latencies) / len(latencies) if latencies else 0.0
    return confusion, per_cell, usage, mean_latency


# ─── Report ──────────────────────────────────────────────────────────────────


def render_report(
    *,
    baseline: Confusion, baseline_latency: float,
    gated: Confusion, gated_usage: LLMUsage, gated_latency: float,
    backend_used: str, n_cells: int, n_gold: int,
) -> str:
    def row(label: str, c: Confusion, latency: float, usage: Optional[LLMUsage] = None):
        cost = f"${usage.cost_usd:.4f}" if usage else "—"
        cache_hits = str(usage.cache_hits) if usage else "—"
        calls = str(usage.calls) if usage else "—"
        return (
            f"| {label:<11} | {c.precision:>6.3f} | {c.recall:>6.3f} | {c.f1:>5.3f} | "
            f"{c.fp_rate:>7.3f} | {c.fn_rate:>7.3f} | "
            f"{c.tp:>3} | {c.fp:>3} | {c.tn:>3} | {c.fn:>3} | "
            f"{latency * 1000:>6.1f} | {cost:>9} | {calls:>5} | {cache_hits:>10} |"
        )

    delta_fp_rate = (baseline.fp_rate - gated.fp_rate) / baseline.fp_rate if baseline.fp_rate else 0.0
    delta_recall = (baseline.recall - gated.recall)   # absolute drop

    lines = [
        "# TalentAlign LLM-Gate Evaluation",
        "",
        f"- LLM backend: **{backend_used}**",
        f"- Gold-labeled pairs: **{n_gold}** across **{n_cells}** (resume × JD) cells",
        "",
        "## Metrics",
        "",
        "| Run         | Precis | Recall |  F1   | FP-rate | FN-rate |  TP |  FP |  TN |  FN | Latency(ms) |     Cost$ | Calls | Cache hits |",
        "|-------------|-------:|-------:|------:|--------:|--------:|----:|----:|----:|----:|------------:|----------:|------:|-----------:|",
        row("baseline", baseline, baseline_latency),
        row("LLM-gated", gated, gated_latency, gated_usage),
        "",
        "## Delta (baseline → LLM-gated)",
        "",
        f"- FP-rate reduction: **{delta_fp_rate*100:+.1f}%** (target ≥ 30%)",
        f"- Recall drop (absolute): **{delta_recall*100:+.2f} pp** (target ≤ 5 pp)",
        f"- F1: {baseline.f1:.3f} → {gated.f1:.3f}",
        "",
        "## Success criteria (Phase 2 sub-phase 2.11)",
        "",
        f"- ① FP reduction ≥ 30%: {'PASS' if delta_fp_rate >= 0.30 else 'FAIL'}",
        f"- ② Recall drop ≤ 5 pp:  {'PASS' if delta_recall <= 0.05 else 'FAIL'}",
        "",
    ]
    if gated_usage.skipped:
        lines.append("## Skipped reasons (LLM-gated run)")
        lines.append("")
        for reason, count in sorted(gated_usage.skipped.items()):
            lines.append(f"- {reason}: {count}")
        lines.append("")
    return "\n".join(lines)


# ─── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", type=Path, default=HERE / "gold_labels.jsonl",
                    help="path to gold labels JSONL")
    ap.add_argument("--out", type=Path, default=HERE / "eval_report.md",
                    help="output report path")
    args = ap.parse_args()

    if not args.gold.exists():
        print(f"ERROR: gold-labels file not found: {args.gold}", file=sys.stderr)
        print("Run generate_candidates.py first, then label the rows.", file=sys.stderr)
        return 2

    gold = read_jsonl(args.gold, GoldRow)
    if not gold:
        print("ERROR: gold-labels file is empty.", file=sys.stderr)
        return 2

    cells = {(g.resume, g.jd) for g in gold}
    print(f"Loaded {len(gold)} gold labels across {len(cells)} cells.")

    print("Running baseline (no LLM)...")
    baseline_conf, _, _, baseline_lat = evaluate(gold, with_llm=False)

    print("Running LLM-gated...")
    gated_conf, _, gated_usage, gated_lat = evaluate(gold, with_llm=True)

    # Determine which backend was actually used for the report.
    from app.utils.llm import get_llm_provider
    backend_used = get_llm_provider().backend

    report = render_report(
        baseline=baseline_conf, baseline_latency=baseline_lat,
        gated=gated_conf, gated_usage=gated_usage, gated_latency=gated_lat,
        backend_used=backend_used,
        n_cells=len(cells), n_gold=len(gold),
    )
    args.out.write_text(report, encoding="utf-8")
    print()
    print(report)
    print()
    print(f"Report saved to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
