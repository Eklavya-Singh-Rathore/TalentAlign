"""Pre-warm the SBERT embedding model at image-build / container-start time.

Running this once during ``docker build`` (or a startup hook on managed
platforms that allow build-time preparation) downloads the
``all-MiniLM-L6-v2`` weights into the HuggingFace cache so the first user
request doesn't pay the ~30-60s cold-start penalty.

Usage:
  python scripts/prewarm_sbert.py

Honors HF_HOME / TRANSFORMERS_CACHE / SENTENCE_TRANSFORMERS_HOME so the
cache directory can be redirected to a writable persistent volume.

Exit codes:
  0  model loaded + encoded test sentence successfully
  1  load failed (network, disk, or unsupported environment)
"""

from __future__ import annotations

import sys
import time


def main() -> int:
    print("[prewarm-sbert] starting…", flush=True)
    t0 = time.monotonic()
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        print(f"[prewarm-sbert] sentence-transformers not installed: {exc}", file=sys.stderr)
        return 1

    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        # Force a real encode so any deferred initialization completes.
        out = model.encode(["TalentAlign warmup sentence."])
        load_seconds = time.monotonic() - t0
        print(
            f"[prewarm-sbert] OK — loaded all-MiniLM-L6-v2 in {load_seconds:.1f}s "
            f"(embedding dim={len(out[0])})",
            flush=True,
        )
        return 0
    except Exception as exc:
        print(f"[prewarm-sbert] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
