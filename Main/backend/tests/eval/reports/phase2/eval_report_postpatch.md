# TalentAlign LLM-Gate Evaluation

- LLM backend: **ollama**
- Gold-labeled pairs: **200** across **10** (resume × JD) cells

## Metrics

| Run         | Precis | Recall |  F1   | FP-rate | FN-rate |  TP |  FP |  TN |  FN | Latency(ms) |     Cost$ | Calls | Cache hits |
|-------------|-------:|-------:|------:|--------:|--------:|----:|----:|----:|----:|------------:|----------:|------:|-----------:|
| baseline    |  0.208 |  0.588 | 0.308 |   0.208 |   0.412 |  10 |  38 | 145 |   7 | 1364.4 |         — |     — |          — |
| LLM-gated   |  0.500 |  0.353 | 0.414 |   0.033 |   0.647 |   6 |   6 | 177 |  11 | 16777.4 |   $0.0000 |     8 |          3 |

## Delta (baseline → LLM-gated)

- FP-rate reduction: **+84.2%** (target ≥ 30%)
- Recall drop (absolute): **+23.53 pp** (target ≤ 5 pp)
- F1: 0.308 → 0.414

## Success criteria (Phase 2 sub-phase 2.11)

- ① FP reduction ≥ 30%: PASS
- ② Recall drop ≤ 5 pp:  FAIL
