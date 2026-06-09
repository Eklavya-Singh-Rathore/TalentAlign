"""Tests for the skill matcher (Phase 5).

Strategy for deterministic testing without SBERT:
  - exact / alias / synonym-map layers use only string normalization and the
    synonym map, so they're tested directly with a TF-IDF provider.
  - semantic / partial / cluster layers depend on embedding similarity, so
    they're tested with a StubProvider that returns a controlled cosine
    matrix. This pins the threshold behavior (P5.1) regardless of backend.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.services.skill_matcher import (
    CLUSTER_MIN_SIMILARITY,
    EMBEDDED_SYNONYM_THRESHOLD,
    PARTIAL_TOKEN_OVERLAP_FLOOR,
    SEMANTIC_PARTIAL_FLOOR,
    _consolidate_missing_skills,
    _decompose_compound_phrases,
    _infer_exact_match_type,
    build_jd_skill_entries,
    extract_jd_skill_phrases,
    match_skills,
    run_skill_extraction_pipeline,
)
from app.utils.embeddings import EmbeddingProvider, BACKEND_TFIDF, BACKEND_TOKEN


def _tfidf():
    return EmbeddingProvider(backend=BACKEND_TFIDF)


class StubProvider:
    """Embedding provider that returns a fixed cosine matrix.

    sim_map maps (resume_phrase, jd_phrase) -> cosine value. Missing pairs
    default to 0.0. Lets tests exercise the semantic/partial/cluster layers
    without a real embedding model.
    """

    def __init__(self, sim_map: dict, backend: str = "stub"):
        self.sim_map = sim_map
        self._backend = backend

    @property
    def backend(self) -> str:
        return self._backend

    def encode_pair(self, group_a, group_b):
        # Carry the raw texts through so cosine_similarity can look them up.
        return list(group_a), list(group_b)

    def cosine_similarity(self, embeddings_a, embeddings_b):
        mat = np.zeros((len(embeddings_a), len(embeddings_b)), dtype="float32")
        for i, ra in enumerate(embeddings_a):
            for j, jb in enumerate(embeddings_b):
                mat[i, j] = self.sim_map.get((ra, jb), 0.0)
        return mat


# ─── Exact / alias / synonym-map layers ──────────────────────────────────────


class TestExactAliasSynonymLayers:
    def test_exact_match(self):
        result = match_skills(["python"], [{"phrase": "python", "bucket": "required"}], _tfidf())
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "exact"

    def test_alias_match_normalizes(self):
        # 'reactjs' aliases to 'react'; resume 'react' → both normalize equal.
        result = match_skills(["react"], [{"phrase": "reactjs", "bucket": "required"}], _tfidf())
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] in ("exact", "alias")

    def test_synonym_map_match(self):
        # scikit-learn ↔ 'machine learning library' (synonym map)
        result = match_skills(
            ["scikit-learn"],
            [{"phrase": "machine learning library", "bucket": "required"}],
            _tfidf(),
        )
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "synonym"

    def test_p52_new_synonym_match(self):
        """P5.2: git ↔ version control should now match via synonym map."""
        result = match_skills(
            ["git"], [{"phrase": "version control", "bucket": "required"}], _tfidf()
        )
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "synonym"

    def test_missing_and_unmatched(self):
        result = match_skills(
            ["python", "docker"],
            [{"phrase": "python", "bucket": "required"}, {"phrase": "kubernetes", "bucket": "optional"}],
            _tfidf(),
        )
        assert "kubernetes" in result["missing_from_resume"]
        assert "docker" in result["unmatched_in_resume"]

    def test_empty_inputs(self):
        assert match_skills([], [{"phrase": "python", "bucket": "required"}], _tfidf())["matched"] == []
        assert match_skills(["python"], [], _tfidf())["matched"] == []


class TestInferExactMatchType:
    def test_identical_is_exact(self):
        assert _infer_exact_match_type("python", "python") == "exact"

    def test_alias_pair(self):
        # 'reactjs' and 'react' normalize to the same canonical → alias
        assert _infer_exact_match_type("reactjs", "react") == "alias"


# ─── Semantic / partial / cluster layers (StubProvider) ──────────────────────


class TestSemanticLayer:
    def test_high_similarity_is_synonym_grade(self):
        sim = {("ml engineering", "machine learning ops"): EMBEDDED_SYNONYM_THRESHOLD + 0.05}
        result = match_skills(
            ["ml engineering"],
            [{"phrase": "machine learning ops", "bucket": "required"}],
            StubProvider(sim),
        )
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "synonym"

    def test_mid_similarity_is_semantic(self):
        # Above adaptive threshold for a 3-word phrase (~0.52) but below the
        # synonym grade.
        sim = {("data pipelines", "building data workflows"): 0.6}
        result = match_skills(
            ["data pipelines"],
            [{"phrase": "building data workflows", "bucket": "required"}],
            StubProvider(sim),
        )
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "semantic"

    def test_low_similarity_no_match(self):
        sim = {("cooking", "kubernetes"): 0.05}
        result = match_skills(
            ["cooking"], [{"phrase": "kubernetes", "bucket": "required"}], StubProvider(sim)
        )
        assert result["matched"] == []
        assert "kubernetes" in result["missing_from_resume"]


class TestPartialLayerThresholds:
    """P5.1: token-overlap floor raised 0.50 → 0.60."""

    def test_single_token_overlap_rejected(self):
        # "deep learning" vs "learning frameworks": 1 shared token / 2 = 0.50,
        # which is now BELOW the 0.60 floor → must NOT match (was a false positive).
        sim = {("deep learning", "learning frameworks"): 0.10}
        result = match_skills(
            ["deep learning"],
            [{"phrase": "learning frameworks", "bucket": "required"}],
            StubProvider(sim),
        )
        assert result["matched"] == []

    def test_subset_overlap_still_matches(self):
        # "machine learning" vs "machine learning models": 2/3 = 0.667 ≥ 0.60 → partial.
        sim = {("machine learning", "machine learning models"): 0.10}
        result = match_skills(
            ["machine learning"],
            [{"phrase": "machine learning models", "bucket": "required"}],
            StubProvider(sim),
        )
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "partial"

    def test_floor_constants_tightened(self):
        # Guards against accidental loosening in future edits.
        assert PARTIAL_TOKEN_OVERLAP_FLOOR == 0.60
        assert SEMANTIC_PARTIAL_FLOOR == 0.45


class TestClusterShareGuard:
    """P5.1: cluster-share fallback now requires sim ≥ CLUSTER_MIN_SIMILARITY."""

    def test_same_cluster_low_sim_rejected(self):
        # redis and sql are both in the 'databases' cluster, but with near-zero
        # similarity the cluster fallback must NOT fire.
        sim = {("redis", "sql"): 0.05}
        result = match_skills(
            ["redis"], [{"phrase": "sql", "bucket": "required"}], StubProvider(sim)
        )
        # sql is whitelisted/short; ensure it's treated as a JD phrase and unmatched
        assert result["matched"] == []

    def test_same_cluster_adequate_sim_matches(self):
        sim = {("redis", "mysql"): CLUSTER_MIN_SIMILARITY + 0.02}
        result = match_skills(
            ["redis"], [{"phrase": "mysql", "bucket": "required"}], StubProvider(sim)
        )
        assert len(result["matched"]) == 1
        assert result["matched"][0]["match_type"] == "partial"


# ─── JD entry building / decomposition ───────────────────────────────────────


class TestBuildJdSkillEntries:
    def test_buckets_preserved(self):
        parsed_jd = {
            "required_skills": ["python", "sql"],
            "preferred_skills": ["docker"],
            "optional_skills": ["kubernetes"],
            "raw_text": "",
        }
        entries = build_jd_skill_entries(parsed_jd, kw=None)
        phrases = {e["phrase"]: e["bucket"] for e in entries}
        assert phrases.get("python") == "required"
        assert phrases.get("docker") == "preferred"
        assert phrases.get("kubernetes") == "optional"

    def test_no_keybert_no_crash(self):
        parsed_jd = {"required_skills": ["python"], "preferred_skills": [],
                     "optional_skills": [], "raw_text": "some jd text"}
        entries = build_jd_skill_entries(parsed_jd, kw=None)
        assert any(e["phrase"] == "python" for e in entries)

    def test_extract_jd_skill_phrases_wrapper(self):
        parsed_jd = {"required_skills": ["python", "sql"], "preferred_skills": [],
                     "optional_skills": [], "raw_text": ""}
        phrases = extract_jd_skill_phrases(parsed_jd, kw=None)
        assert "python" in phrases
        assert "sql" in phrases


class TestDecomposeCompoundPhrases:
    def test_splits_compound(self):
        entries = [{"phrase": "python and machine learning", "bucket": "required"}]
        out = _decompose_compound_phrases(entries)
        phrases = {e["phrase"] for e in out}
        # Original preserved + at least one decomposed sub-skill
        assert "python and machine learning" in phrases
        assert len(out) > 1


class TestConsolidateMissingSkills:
    def test_removes_subphrases(self):
        phrases = ["machine learning", "machine learning models", "machine"]
        out = _consolidate_missing_skills(phrases)
        # "machine" and "machine learning" are subsets of "machine learning models"
        assert "machine learning models" in out
        assert "machine" not in out

    def test_empty(self):
        assert _consolidate_missing_skills([]) == []

    def test_no_redundancy_preserved(self):
        phrases = ["python", "kubernetes", "docker"]
        out = _consolidate_missing_skills(phrases)
        assert set(out) == {"python", "kubernetes", "docker"}


# ─── End-to-end pipeline ─────────────────────────────────────────────────────


class TestRunSkillExtractionPipeline:
    def test_basic_pipeline(self):
        parsed_resume = {
            "skills": ["python", "sql", "react"],
            "_skill_sources": {
                "skills": ["python", "sql", "react"],
                "cert_derived": [], "projects": [], "internships": [],
                "work_experience": [], "fallback_full_text": [],
            },
            "_empty_sections": [],
        }
        parsed_jd = {
            "required_skills": ["python", "sql"],
            "preferred_skills": ["react"],
            "optional_skills": ["kubernetes"],
            "raw_text": "",
        }
        result = run_skill_extraction_pipeline(
            parsed_resume, parsed_jd, kw=None, provider=_tfidf()
        )
        assert result["summary"]["total_matched"] >= 3  # python, sql, react
        assert "kubernetes" in result["missing_from_resume"]
        assert result["summary"]["embedding_backend"] == "tfidf"

    def test_score_in_range(self):
        parsed_resume = {
            "skills": ["python"],
            "_skill_sources": {"skills": ["python"], "cert_derived": [],
                               "projects": [], "internships": [],
                               "work_experience": [], "fallback_full_text": []},
            "_empty_sections": [],
        }
        parsed_jd = {"required_skills": ["python", "java", "go"],
                     "preferred_skills": [], "optional_skills": [], "raw_text": ""}
        result = run_skill_extraction_pipeline(parsed_resume, parsed_jd, kw=None, provider=_tfidf())
        assert 0.0 <= result["summary"]["skills_score_S_sk"] <= 1.0

    def test_missing_capped_at_12(self):
        parsed_resume = {
            "skills": [],
            "_skill_sources": {"skills": [], "cert_derived": [], "projects": [],
                               "internships": [], "work_experience": [], "fallback_full_text": []},
            "_empty_sections": ["skills"],
        }
        parsed_jd = {
            "required_skills": [f"skill{i}" for i in range(20)],
            "preferred_skills": [], "optional_skills": [], "raw_text": "",
        }
        result = run_skill_extraction_pipeline(parsed_resume, parsed_jd, kw=None, provider=_tfidf())
        assert len(result["missing_from_resume"]) <= 12

    def test_token_backend_pipeline(self):
        """Pipeline should also run on the token backend."""
        parsed_resume = {
            "skills": ["python", "docker"],
            "_skill_sources": {"skills": ["python", "docker"], "cert_derived": [],
                               "projects": [], "internships": [],
                               "work_experience": [], "fallback_full_text": []},
            "_empty_sections": [],
        }
        parsed_jd = {"required_skills": ["python"], "preferred_skills": [],
                     "optional_skills": [], "raw_text": ""}
        result = run_skill_extraction_pipeline(
            parsed_resume, parsed_jd, kw=None,
            provider=EmbeddingProvider(backend=BACKEND_TOKEN),
        )
        assert result["summary"]["total_matched"] >= 1
        assert result["summary"]["embedding_backend"] == "token"
