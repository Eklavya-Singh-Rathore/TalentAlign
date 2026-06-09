"""Shared I/O schemas + helpers for the evaluation harness (sub-phase 1.12–1.14).

Two row types:
  * Candidate row — emitted by ``generate_candidates.py`` for hand-labeling.
  * Gold-label row — what the user produces by labeling candidates.

Both use Pydantic so a malformed JSONL fails loudly at load time rather than
silently producing wrong metrics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


LABEL_TRUE = "true_match"
LABEL_FALSE = "false_match"


class CandidateRow(BaseModel):
    """One borderline pair from the cross-test matrix, awaiting a label."""
    model_config = ConfigDict(extra="forbid")

    resume: str
    jd: str
    resume_phrase: str
    jd_phrase: str
    cosine: float = Field(ge=-1.0, le=1.0)
    token_overlap: float = Field(ge=0.0, le=1.0)
    current_match_type: str   # "semantic" | "partial" | "rejected"
    label: Optional[Literal["true_match", "false_match"]] = None
    notes: Optional[str] = None


class GoldRow(BaseModel):
    """A labeled (resume_skill, jd_skill) pair used by run_eval.py."""
    model_config = ConfigDict(extra="forbid")

    resume: str
    jd: str
    resume_phrase: str
    jd_phrase: str
    label: Literal["true_match", "false_match"]
    # The candidate-row fields below are preserved when the user re-saves
    # the candidates file as gold_labels.jsonl with `label` filled in.
    cosine: Optional[float] = None
    token_overlap: Optional[float] = None
    current_match_type: Optional[str] = None
    notes: Optional[str] = None


def write_jsonl(path: Path, rows: Iterable[BaseModel]) -> int:
    """Atomically write a sequence of pydantic rows to a JSONL file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    count = 0
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(row.model_dump_json())
            f.write("\n")
            count += 1
    import os
    os.replace(tmp, path)
    return count


def read_jsonl(path: Path, model_cls):
    """Load a JSONL file into a list of pydantic rows."""
    path = Path(path)
    out = []
    with path.open("r", encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{ln}: invalid JSON ({exc})") from exc
            try:
                out.append(model_cls.model_validate(data))
            except Exception as exc:
                raise ValueError(f"{path}:{ln}: schema error ({exc})") from exc
    return out
