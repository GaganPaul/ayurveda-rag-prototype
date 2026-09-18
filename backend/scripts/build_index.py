#!/usr/bin/env python3
"""Offline index builder for AyurVeda RAG Prototype.

Extracts text from PDF and TXT documents in backend/data/, fits a TF-IDF vectorizer,
and saves chunks.json, vectorizer.joblib, tfidf_matrix.npz, and metadata.json into
backend/index/ for fast server startup.
"""
from __future__ import annotations

import logging
from pathlib import Path
import sys
import time

# Ensure backend directory is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rag_index import (
    CHUNKS_FILE,
    MATRIX_FILE,
    METADATA_FILE,
    REQUIRED_INDEX_FILES,
    VECTORIZER_FILE,
    atomic_reindex,
    validate_index,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("build_index")


def main() -> int:
    data_dir = BACKEND_DIR / "data"
    index_dir = BACKEND_DIR / "index"
    tmp_dir = BACKEND_DIR / "index_build_tmp"

    print("=" * 60)
    print("AyurVeda RAG Prototype — Offline Index Builder")
    print("=" * 60)
    print(f"Source documents directory : {data_dir}")
    print(f"Target index directory     : {index_dir}")
    print(f"Temporary staging directory: {tmp_dir}")
    print("-" * 60)

    if not data_dir.exists():
        print(f"ERROR: Source directory not found: {data_dir}", file=sys.stderr)
        return 1

    start_time = time.time()
    try:
        print("Starting index generation...")
        metadata = atomic_reindex(data_dir=data_dir, index_dir=index_dir, tmp_dir=tmp_dir)
        elapsed = time.time() - start_time

        # Validate index
        is_valid, msg, _ = validate_index(index_dir)
        if not is_valid:
            print(f"ERROR: Built index failed validation: {msg}", file=sys.stderr)
            return 1

        print("-" * 60)
        print("✓ Pre-built index successfully generated and verified!")
        print(f"  • Source documents count : {metadata.get('documents')}")
        print(f"  • Total chunks indexed   : {metadata.get('chunks')}")
        print(f"  • TF-IDF Matrix shape    : {metadata.get('matrix_shape')}")
        print(f"  • Build time             : {elapsed:.2f} seconds")
        print("\nGenerated files in backend/index/:")

        total_bytes = 0
        for fname in REQUIRED_INDEX_FILES:
            fpath = index_dir / fname
            if fpath.exists():
                size = fpath.stat().st_size
                total_bytes += size
                print(f"  - {fname:<20} ({size / 1024:.1f} KB)")

        print(f"  Total index size: {total_bytes / (1024 * 1024):.2f} MB")
        print("=" * 60)
        print("You can now commit backend/index/ to Git and deploy to Render.")
        print("=" * 60)
        return 0

    except Exception as exc:
        print(f"\nERROR: Failed to build index: {exc}", file=sys.stderr)
        logger.exception("Build index failed:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
