"""Embedding abstraction with graceful degradation.

Provides a single interface (EmbeddingProvider) that encodes text into
fixed-dimensional vectors and computes cosine similarity. The actual
backend is chosen at runtime in this order of preference:

  1. SBERT (sentence-transformers) — semantically rich; requires the
     'sentence-transformers' package and a downloaded model.
  2. TF-IDF (scikit-learn) — bag-of-words with IDF weighting; fast,
     no model download, but only catches lexical overlap.
  3. Token-overlap fallback — pure-Python Jaccard similarity on
     normalized tokens. Used only when neither SBERT nor scikit-learn
     is available (e.g., minimal test environments).

Following the spaCy lazy-load pattern already used elsewhere in the
codebase (see skill_normalization._load_spacy), the heaviest backend is
loaded only when first requested. Tests can force a specific backend by
constructing EmbeddingProvider(backend="tfidf") directly.

Phase 5 (Matching Optimization) is the natural home for tuning the
embedding model choice, thresholds, and similarity blending — this
module only provides the substrate.
"""

from __future__ import annotations

import os

import logging
import re
from typing import Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)


# Allowed backend identifiers. "auto" picks the best available at runtime.
BACKEND_AUTO = "auto"
BACKEND_SBERT = "sbert"
BACKEND_TFIDF = "tfidf"
BACKEND_TOKEN = "token"

_VALID_BACKENDS = {BACKEND_AUTO, BACKEND_SBERT, BACKEND_TFIDF, BACKEND_TOKEN}


def _tokenize(text: str) -> List[str]:
    """Lowercase + split on non-alphanumeric. Used by the token fallback."""
    if not text:
        return []
    return [tok for tok in re.split(r"[^a-z0-9]+", text.lower()) if tok]


class EmbeddingProvider:
    """Encodes text and computes cosine similarity, with backend autoselection.

    Usage:
        provider = EmbeddingProvider()         # auto-pick best backend
        embeddings = provider.encode([text1, text2, ...])
        sim_matrix = provider.cosine_similarity(emb_a, emb_b)

    For backends that produce real vectors (SBERT, TF-IDF), `encode`
    returns a 2D numpy array of shape (n_texts, dim). For the token
    fallback, `encode` returns a list of token sets and `cosine_similarity`
    computes Jaccard overlap.
    """

    def __init__(
        self,
        backend: str = BACKEND_AUTO,
        sbert_model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        if backend not in _VALID_BACKENDS:
            raise ValueError(
                f"Unknown backend {backend!r}; must be one of {_VALID_BACKENDS}"
            )
        self._requested_backend = backend
        self._sbert_model_name = sbert_model_name
        self._backend: Optional[str] = None
        self._sbert = None
        self._sbert_util = None
        self._tfidf_vectorizer = None

    # ── Backend resolution ────────────────────────────────────────────────

    @property
    def backend(self) -> str:
        """Return the actually-selected backend ('sbert' / 'tfidf' / 'token')."""
        if self._backend is None:
            self._resolve_backend()
        return self._backend  # type: ignore[return-value]

    def _resolve_backend(self) -> None:
        """Choose the highest-priority backend that's available."""
        if self._requested_backend == BACKEND_SBERT:
            self._init_sbert(strict=True)
            return
        if self._requested_backend == BACKEND_TFIDF:
            self._init_tfidf(strict=True)
            return
        if self._requested_backend == BACKEND_TOKEN:
            self._backend = BACKEND_TOKEN
            return

        # auto: try SBERT → TF-IDF → token
        if self._init_sbert(strict=False):
            return
        if self._init_tfidf(strict=False):
            return
        self._backend = BACKEND_TOKEN
        logger.info(
            "Embedding backend resolved: %s (SBERT and scikit-learn unavailable)",
            BACKEND_TOKEN,
        )

    def _init_sbert(self, strict: bool) -> bool:
        try:
            from sentence_transformers import SentenceTransformer, util  # type: ignore
            self._sbert = SentenceTransformer(self._sbert_model_name)
            self._sbert_util = util
            self._backend = BACKEND_SBERT
            logger.info("Embedding backend resolved: sbert (%s)", self._sbert_model_name)
            return True
        except Exception as exc:
            if strict:
                raise
            logger.debug("SBERT unavailable: %s", exc)
            return False

    def _init_tfidf(self, strict: bool) -> bool:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
            self._tfidf_vectorizer = TfidfVectorizer(
                lowercase=True,
                token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9+#./\-]*\b",
                ngram_range=(1, 2),
                max_features=5000,
            )
            self._backend = BACKEND_TFIDF
            logger.info("Embedding backend resolved: tfidf (sklearn)")
            return True
        except Exception as exc:
            if strict:
                raise
            logger.debug("scikit-learn unavailable: %s", exc)
            return False

    # ── Public encode / similarity API ────────────────────────────────────

    def encode(self, texts: Sequence[str]):
        """Encode a sequence of texts into the backend's native representation.

        Returns:
          - For SBERT / TF-IDF: 2D numpy array shape (n_texts, dim)
          - For token fallback: list of token sets
        """
        backend = self.backend
        if not texts:
            if backend == BACKEND_TOKEN:
                return []
            import numpy as np
            return np.zeros((0, 1), dtype="float32")

        if backend == BACKEND_SBERT:
            return self._sbert.encode(list(texts), convert_to_numpy=True)  # type: ignore[union-attr]

        if backend == BACKEND_TFIDF:
            assert self._tfidf_vectorizer is not None
            # TF-IDF needs a corpus to fit on. We fit on the texts at hand.
            # This is acceptable for project-vs-JD similarity because we always
            # encode (projects + jd) together via encode_pair() below.
            matrix = self._tfidf_vectorizer.fit_transform(list(texts))
            return matrix.toarray().astype("float32")

        # token backend
        return [set(_tokenize(t)) for t in texts]

    def encode_pair(self, group_a: Sequence[str], group_b: Sequence[str]):
        """Encode two groups jointly so TF-IDF sees a shared vocabulary.

        Returns:
          (embeddings_a, embeddings_b) tuple.
        """
        backend = self.backend
        if backend != BACKEND_TFIDF:
            return self.encode(group_a), self.encode(group_b)

        assert self._tfidf_vectorizer is not None
        all_texts = list(group_a) + list(group_b)
        if not all_texts:
            import numpy as np
            return (
                np.zeros((0, 1), dtype="float32"),
                np.zeros((0, 1), dtype="float32"),
            )
        matrix = self._tfidf_vectorizer.fit_transform(all_texts)
        dense = matrix.toarray().astype("float32")
        n_a = len(group_a)
        return dense[:n_a], dense[n_a:]

    def cosine_similarity(self, embeddings_a, embeddings_b):
        """Compute cosine similarity matrix between two groups of embeddings.

        Returns a 2D numpy array of shape (len(a), len(b)) with values in
        [-1, 1] for vector backends, [0, 1] for the token (Jaccard) backend.
        """
        backend = self.backend
        if backend == BACKEND_TOKEN:
            import numpy as np
            sims = np.zeros((len(embeddings_a), len(embeddings_b)), dtype="float32")
            for i, ta in enumerate(embeddings_a):
                for j, tb in enumerate(embeddings_b):
                    union = ta | tb
                    sims[i, j] = (len(ta & tb) / len(union)) if union else 0.0
            return sims

        # SBERT / TF-IDF — both produce numpy arrays, use a pure-numpy cosine.
        import numpy as np
        a = np.asarray(embeddings_a, dtype="float32")
        b = np.asarray(embeddings_b, dtype="float32")
        if a.ndim == 1:
            a = a[np.newaxis, :]
        if b.ndim == 1:
            b = b[np.newaxis, :]
        if a.size == 0 or b.size == 0:
            return np.zeros((a.shape[0], b.shape[0]), dtype="float32")
        # Normalize rows; guard zero-norm rows.
        a_norm = np.linalg.norm(a, axis=1, keepdims=True)
        b_norm = np.linalg.norm(b, axis=1, keepdims=True)
        a_norm[a_norm == 0] = 1.0
        b_norm[b_norm == 0] = 1.0
        a_n = a / a_norm
        b_n = b / b_norm
        return (a_n @ b_n.T).astype("float32")


# Module-level singleton for "default" usage. Lazy: the first call to
# get_embedding_provider() pins the backend choice for the process.
_default_provider: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return the process-wide default EmbeddingProvider."""
    global _default_provider

    if _default_provider is None:
        env_backend = os.environ.get(
            "TALENTALIGN_EMBEDDING_BACKEND", ""
        ).strip().lower()

        if env_backend in _VALID_BACKENDS:
            _default_provider = EmbeddingProvider(backend=env_backend)
        else:
            _default_provider = EmbeddingProvider(backend=BACKEND_AUTO)

    return _default_provider


def reset_default_provider() -> None:
    """Clear the cached default provider (useful for tests)."""
    global _default_provider
    _default_provider = None
