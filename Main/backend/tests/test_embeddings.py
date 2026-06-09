"""Tests for the embedding abstraction (Phase 4 P4.0)."""

from __future__ import annotations

import pytest

from app.utils.embeddings import (
    BACKEND_AUTO,
    BACKEND_TFIDF,
    BACKEND_TOKEN,
    EmbeddingProvider,
    get_embedding_provider,
    reset_default_provider,
)


class TestBackendSelection:
    """Verify backend resolution and forcing."""

    def test_auto_picks_an_available_backend(self):
        p = EmbeddingProvider(backend=BACKEND_AUTO)
        # Must pick something — sklearn is required by Phase 4
        assert p.backend in ("sbert", "tfidf", "token")

    def test_force_tfidf(self):
        p = EmbeddingProvider(backend=BACKEND_TFIDF)
        assert p.backend == "tfidf"

    def test_force_token(self):
        p = EmbeddingProvider(backend=BACKEND_TOKEN)
        assert p.backend == "token"

    def test_invalid_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            EmbeddingProvider(backend="nonsense")

    def test_default_provider_singleton(self):
        reset_default_provider()
        p1 = get_embedding_provider()
        p2 = get_embedding_provider()
        assert p1 is p2


class TestEncodeAndCosineTfidf:
    """End-to-end encode + cosine_similarity using TF-IDF."""

    def test_similar_texts_score_higher(self):
        p = EmbeddingProvider(backend=BACKEND_TFIDF)
        texts = [
            "machine learning python scikit-learn neural networks",
            "machine learning python pandas scikit-learn",
            "marketing campaigns social media",
        ]
        jd = ["machine learning python scikit-learn"]
        embs, jd_emb = p.encode_pair(texts, jd)
        sims = p.cosine_similarity(embs, jd_emb)
        # First two should score above the marketing one.
        assert sims[0, 0] > sims[2, 0]
        assert sims[1, 0] > sims[2, 0]

    def test_identical_texts_score_high(self):
        p = EmbeddingProvider(backend=BACKEND_TFIDF)
        embs, jd_emb = p.encode_pair(["python machine learning"], ["python machine learning"])
        sims = p.cosine_similarity(embs, jd_emb)
        # TF-IDF on identical strings should be ~1.0
        assert sims[0, 0] > 0.9

    def test_empty_inputs(self):
        p = EmbeddingProvider(backend=BACKEND_TFIDF)
        a, b = p.encode_pair([], [])
        assert a.shape[0] == 0
        assert b.shape[0] == 0


class TestEncodeAndCosineToken:
    """End-to-end with the token (Jaccard) backend."""

    def test_overlap_score(self):
        p = EmbeddingProvider(backend=BACKEND_TOKEN)
        a = p.encode(["python sql docker"])
        b = p.encode(["python kubernetes docker"])
        sims = p.cosine_similarity(a, b)
        # 2 shared tokens (python, docker) of 4 unique → 0.5
        assert abs(sims[0, 0] - 0.5) < 0.01

    def test_no_overlap_is_zero(self):
        p = EmbeddingProvider(backend=BACKEND_TOKEN)
        a = p.encode(["alpha beta"])
        b = p.encode(["gamma delta"])
        sims = p.cosine_similarity(a, b)
        assert sims[0, 0] == 0.0

    def test_empty_inputs(self):
        p = EmbeddingProvider(backend=BACKEND_TOKEN)
        a = p.encode([])
        b = p.encode([])
        assert a == []
        assert b == []


class TestCosineMatrixShape:
    """Verify shape of the returned similarity matrix."""

    def test_tfidf_shape(self):
        p = EmbeddingProvider(backend=BACKEND_TFIDF)
        embs, jd_emb = p.encode_pair(["a b c", "d e f"], ["x y z"])
        sims = p.cosine_similarity(embs, jd_emb)
        assert sims.shape == (2, 1)

    def test_token_shape(self):
        p = EmbeddingProvider(backend=BACKEND_TOKEN)
        a = p.encode(["a b", "c d"])
        b = p.encode(["a c", "b d", "x y"])
        sims = p.cosine_similarity(a, b)
        assert sims.shape == (2, 3)
