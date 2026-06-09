"""Unit tests for the eval harness itself (sub-phase 1.14).

The harness is a tool — if it silently misclassifies TPs/FNs/etc. we'd
report wrong numbers. Tests here pin its internal logic.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.eval.eval_io import (
    CandidateRow,
    GoldRow,
    LABEL_FALSE,
    LABEL_TRUE,
    read_jsonl,
    write_jsonl,
)
from tests.eval.run_eval import Confusion, classify, render_report
from app.utils.llm import LLMUsage


class TestSchemas:
    def test_candidate_row_round_trip(self, tmp_path: Path):
        rows = [
            CandidateRow(
                resume="Eklavya", jd="JD_1",
                resume_phrase="python", jd_phrase="python",
                cosine=1.0, token_overlap=1.0, current_match_type="exact",
            ),
            CandidateRow(
                resume="Vignesh", jd="JD_3",
                resume_phrase="ml", jd_phrase="machine learning",
                cosine=0.62, token_overlap=0.5, current_match_type="semantic",
                label=LABEL_TRUE,
            ),
        ]
        f = tmp_path / "out.jsonl"
        n = write_jsonl(f, rows)
        assert n == 2
        loaded = read_jsonl(f, CandidateRow)
        assert len(loaded) == 2
        assert loaded[1].label == LABEL_TRUE

    def test_gold_row_requires_label(self):
        with pytest.raises(ValidationError):
            GoldRow(
                resume="r", jd="j",
                resume_phrase="a", jd_phrase="b",
            )  # missing label

    def test_label_value_validated(self):
        with pytest.raises(ValidationError):
            GoldRow(
                resume="r", jd="j",
                resume_phrase="a", jd_phrase="b",
                label="maybe",  # not in literal set
            )

    def test_cosine_bounds(self):
        with pytest.raises(ValidationError):
            CandidateRow(
                resume="r", jd="j",
                resume_phrase="a", jd_phrase="b",
                cosine=1.5, token_overlap=0.0, current_match_type="rejected",
            )


class TestClassify:
    def test_tp(self):
        assert classify(predicted_match=True, gold_label=LABEL_TRUE) == "tp"

    def test_fp(self):
        assert classify(predicted_match=True, gold_label=LABEL_FALSE) == "fp"

    def test_fn(self):
        assert classify(predicted_match=False, gold_label=LABEL_TRUE) == "fn"

    def test_tn(self):
        assert classify(predicted_match=False, gold_label=LABEL_FALSE) == "tn"


class TestConfusion:
    def test_metrics_all_positive(self):
        c = Confusion(tp=8, fp=2, tn=10, fn=2)
        assert c.precision == 0.8
        assert c.recall == 0.8
        assert c.f1 == pytest.approx(0.8)
        assert c.fp_rate == pytest.approx(2 / 12)
        assert c.fn_rate == pytest.approx(2 / 10)
        assert c.total == 22

    def test_metrics_zero_denominators(self):
        c = Confusion()
        assert c.precision == 0.0
        assert c.recall == 0.0
        assert c.f1 == 0.0
        assert c.fp_rate == 0.0
        assert c.fn_rate == 0.0

    def test_perfect(self):
        c = Confusion(tp=10, tn=10)
        assert c.precision == 1.0
        assert c.recall == 1.0
        assert c.f1 == 1.0
        assert c.fp_rate == 0.0
        assert c.fn_rate == 0.0


class TestRenderReport:
    def test_smoke_renders(self):
        baseline = Confusion(tp=8, fp=4, tn=6, fn=2)
        gated = Confusion(tp=7, fp=1, tn=9, fn=3)
        usage = LLMUsage(calls=5, cache_hits=2, tokens_in=100, tokens_out=50, cost_usd=0.0123)
        out = render_report(
            baseline=baseline, baseline_latency=0.020,
            gated=gated, gated_usage=usage, gated_latency=0.350,
            backend_used="mock",
            n_cells=10, n_gold=20,
        )
        # Required sections present
        assert "TalentAlign LLM-Gate Evaluation" in out
        assert "Metrics" in out
        assert "baseline" in out
        assert "LLM-gated" in out
        assert "Delta" in out
        # FP reduction: baseline 4/10 = 0.4 → gated 1/10 = 0.1 → -75%
        assert "75.0%" in out or "75%" in out
