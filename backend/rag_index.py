from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
from typing import Any, Optional

import joblib
from pypdf import PdfReader
import scipy.sparse
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger("ayurveda_rag.index")

CHUNKS_FILE = "chunks.json"
VECTORIZER_FILE = "vectorizer.joblib"
MATRIX_FILE = "tfidf_matrix.npz"
METADATA_FILE = "metadata.json"

REQUIRED_INDEX_FILES = [
    CHUNKS_FILE,
    VECTORIZER_FILE,
    MATRIX_FILE,
    METADATA_FILE,
]


def load_documents(data_dir: Path) -> list[dict[str, Any]]:
    """Recursively extracts text chunks from PDF and TXT documents in data_dir.
    
    Preserves existing metadata fields ('name', 'page', 'text') for full backward
    compatibility, while enriching with 'id', 'filename', 'source', and 'category'.
    """
    documents: list[dict[str, Any]] = []

    if not data_dir.exists():
        logger.warning("Data directory does not exist: %s", data_dir)
        return documents

    for path in sorted(data_dir.rglob("*")):
        if not path.is_file():
            continue

        try:
            suffix = path.suffix.lower()
            category = path.parent.name if path.parent != data_dir else "general"

            if suffix == ".txt":
                text = path.read_text(encoding="utf-8").strip()
                if text:
                    documents.append(
                        {
                            "id": f"{path.stem}_full",
                            "name": path.name,
                            "filename": path.name,
                            "source": path.name,
                            "page": None,
                            "category": category,
                            "text": text,
                        }
                    )

            elif suffix == ".pdf":
                reader = PdfReader(str(path))
                for page_number, page in enumerate(reader.pages, start=1):
                    page_text = (page.extract_text() or "").strip()
                    if page_text:
                        documents.append(
                            {
                                "id": f"{path.stem}_p{page_number}",
                                "name": path.name,
                                "filename": path.name,
                                "source": path.name,
                                "page": page_number,
                                "category": category,
                                "text": page_text,
                            }
                        )
        except Exception as exc:
            logger.warning("Could not load document %s: %s", path, exc)

    logger.info("Loaded %d document chunks from %s", len(documents), data_dir)
    return [d for d in documents if d["text"]]


def build_index(data_dir: Path, output_dir: Path) -> dict[str, Any]:
    """Builds the TF-IDF vectorizer and sparse matrix, saving all artifacts to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    docs = load_documents(data_dir)
    if not docs:
        raise ValueError(f"No documents found in {data_dir} to build index.")

    logger.info("Fitting TfidfVectorizer on %d chunks...", len(docs))
    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        max_features=12000,
    )
    matrix = vectorizer.fit_transform([d["text"] for d in docs])

    # Save chunks.json
    chunks_path = output_dir / CHUNKS_FILE
    chunks_path.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save vectorizer.joblib
    vectorizer_path = output_dir / VECTORIZER_FILE
    joblib.dump(vectorizer, vectorizer_path)

    # Save tfidf_matrix.npz as sparse matrix (keeps memory low)
    matrix_path = output_dir / MATRIX_FILE
    scipy.sparse.save_npz(matrix_path, matrix)

    # Save metadata.json
    unique_sources = sorted(list({d["name"] for d in docs}))
    metadata = {
        "version": 1,
        "retrieval_type": "tfidf",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents": len(unique_sources),
        "chunks": len(docs),
        "unique_sources": len(unique_sources),
        "matrix_shape": list(matrix.shape),
        "vectorizer_params": {
            "lowercase": True,
            "stop_words": "english",
            "ngram_range": [1, 2],
            "max_features": 12000,
        },
    }
    metadata_path = output_dir / METADATA_FILE
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    logger.info(
        "TF-IDF index built successfully in %s (matrix shape: %s, chunks: %d)",
        output_dir,
        matrix.shape,
        len(docs),
    )
    return metadata


def validate_index(index_dir: Path) -> tuple[bool, str, Optional[dict[str, Any]]]:
    """Validates that all required index files exist, are readable, and internally consistent."""
    if not index_dir.exists():
        return False, f"Index directory '{index_dir}' does not exist.", None

    for fname in REQUIRED_INDEX_FILES:
        fpath = index_dir / fname
        if not fpath.exists():
            return False, f"Missing required index file: '{fname}' in '{index_dir}'.", None
        if fpath.stat().st_size == 0:
            return False, f"Index file '{fname}' is empty (0 bytes).", None

    # Validate metadata
    try:
        metadata = json.loads((index_dir / METADATA_FILE).read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Failed to parse '{METADATA_FILE}': {exc}", None

    # Validate chunks
    try:
        chunks = json.loads((index_dir / CHUNKS_FILE).read_text(encoding="utf-8"))
        if not isinstance(chunks, list) or len(chunks) == 0:
            return False, f"'{CHUNKS_FILE}' must contain a non-empty list of chunks.", None
    except Exception as exc:
        return False, f"Failed to parse '{CHUNKS_FILE}': {exc}", None

    # Validate vectorizer and matrix compatibility
    try:
        vectorizer: TfidfVectorizer = joblib.load(index_dir / VECTORIZER_FILE)
        matrix = scipy.sparse.load_npz(index_dir / MATRIX_FILE)
    except Exception as exc:
        return False, f"Failed to load vectorizer or matrix: {exc}", None

    if matrix.shape[0] != len(chunks):
        return (
            False,
            f"Row count mismatch: TF-IDF matrix has {matrix.shape[0]} rows but chunks.json has {len(chunks)} entries.",
            None,
        )

    expected_features = len(vectorizer.get_feature_names_out())
    if matrix.shape[1] != expected_features:
        return (
            False,
            f"Feature count mismatch: matrix has {matrix.shape[1]} columns but vectorizer has {expected_features} features.",
            None,
        )

    return True, "Index is valid and consistent.", metadata


def load_prebuilt_index(
    index_dir: Path,
) -> tuple[list[dict[str, Any]], TfidfVectorizer, Any, dict[str, Any]]:
    """Loads pre-built index files from index_dir and returns (chunks, vectorizer, matrix, metadata).
    
    Raises RuntimeError if validation fails.
    """
    is_valid, msg, metadata = validate_index(index_dir)
    if not is_valid or metadata is None:
        raise RuntimeError(f"Invalid pre-built index: {msg}")

    chunks = json.loads((index_dir / CHUNKS_FILE).read_text(encoding="utf-8"))
    vectorizer: TfidfVectorizer = joblib.load(index_dir / VECTORIZER_FILE)
    matrix = scipy.sparse.load_npz(index_dir / MATRIX_FILE)

    return chunks, vectorizer, matrix, metadata


def atomic_reindex(data_dir: Path, index_dir: Path, tmp_dir: Path) -> dict[str, Any]:
    """Builds a new index into tmp_dir, validates it, and atomically updates index_dir.
    
    Prevents corrupting or losing the existing index if indexing fails halfway through.
    """
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        metadata = build_index(data_dir, tmp_dir)
        is_valid, msg, validated_meta = validate_index(tmp_dir)
        if not is_valid:
            raise RuntimeError(f"Index validation failed in temporary build: {msg}")

        # Atomically install new index files into index_dir
        index_dir.mkdir(parents=True, exist_ok=True)
        for fname in REQUIRED_INDEX_FILES:
            src = tmp_dir / fname
            dest = index_dir / fname
            # Use atomic replace via temporary filename in the destination directory
            staging = index_dir / f"{fname}.staging"
            shutil.copy2(src, staging)
            os.replace(staging, dest)

        logger.info("Successfully installed new pre-built index to %s", index_dir)
        return validated_meta or metadata

    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
