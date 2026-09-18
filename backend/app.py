from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
import threading
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from rag_index import (
    atomic_reindex,
    load_prebuilt_index,
    validate_index,
)

# Configure server logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ayurveda_rag")

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "index"
INDEX_BUILD_TMP_DIR = BASE_DIR / "index_build_tmp"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

if not GEMINI_API_KEY:
    # The server can still start so /health works, but chat will return a clear error.
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)


class KnowledgeBase:
    """Manages knowledge-base documents and TF-IDF index with thread-safe access."""

    def __init__(self, data_dir: Path, index_dir: Path, tmp_dir: Path):
        self.data_dir = data_dir
        self.index_dir = index_dir
        self.tmp_dir = tmp_dir
        self.documents: list[dict[str, Any]] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.matrix: Any = None
        self.metadata: Optional[dict[str, Any]] = None
        self.index_ready: bool = False
        self.index_loading: bool = False
        self.index_error: Optional[str] = None
        self.documents_loaded: int = 0
        self._lock = threading.Lock()

    def load_prebuilt(self) -> bool:
        """Loads pre-built index files (chunks.json, vectorizer.joblib, tfidf_matrix.npz, metadata.json).
        
        Does NOT perform expensive PDF parsing or TF-IDF fitting on startup.
        """
        with self._lock:
            self.index_loading = True
            self.index_ready = False
            self.index_error = None

        logger.info("Loading pre-built RAG index from %s...", self.index_dir)
        try:
            docs, vec, mat, metadata = load_prebuilt_index(self.index_dir)
            with self._lock:
                self.documents = docs
                self.vectorizer = vec
                self.matrix = mat
                self.metadata = metadata
                self.documents_loaded = len(docs)
                self.index_ready = True
                self.index_loading = False
                self.index_error = None

            logger.info("Pre-built RAG index loaded successfully (%d chunks).", len(docs))
            return True
        except Exception as exc:
            err_msg = str(exc)
            logger.error(
                "Pre-built RAG index not found or invalid: %s. Run scripts/build_index.py before deployment.",
                err_msg,
            )
            with self._lock:
                self.documents = []
                self.vectorizer = None
                self.matrix = None
                self.metadata = None
                self.documents_loaded = 0
                self.index_ready = False
                self.index_loading = False
                self.index_error = f"Pre-built index unavailable: {err_msg}"
            return False

    def rebuild_sync(self) -> dict[str, Any]:
        """Explicit on-demand reindex: extracts PDF/TXT files, fits TF-IDF, atomically saves, and reloads."""
        with self._lock:
            self.index_loading = True

        try:
            logger.info("Starting explicit knowledge-base rebuild...")
            metadata = atomic_reindex(self.data_dir, self.index_dir, self.tmp_dir)
            loaded = self.load_prebuilt()
            if not loaded:
                raise RuntimeError("Failed to load freshly built index.")
            return metadata
        except Exception as exc:
            logger.exception("Explicit index rebuild failed: %s", exc)
            with self._lock:
                self.index_loading = False
                if not self.index_ready:
                    self.index_error = f"Rebuild failed: {exc}"
            raise


knowledge_base = KnowledgeBase(DATA_DIR, INDEX_DIR, INDEX_BUILD_TMP_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FastAPI application...")
    logger.info("Loading pre-built RAG index...")
    loaded = knowledge_base.load_prebuilt()
    if not loaded:
        logger.warning("Knowledge base started in degraded mode (pre-built index missing or invalid).")
    yield


app = FastAPI(
    title="AyurVeda RAG Prototype",
    version="0.2.0",
    lifespan=lifespan,
)
app.state.knowledge_base = knowledge_base

origins = ["*"] if FRONTEND_URL == "*" else [FRONTEND_URL]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_admin(
    authorization: Optional[str] = Header(None),
    x_admin_token: Optional[str] = Header(None),
):
    """Verifies ADMIN_TOKEN from X-Admin-Token or Authorization: Bearer <token>."""
    token = x_admin_token
    if not token and authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
        else:
            token = authorization

    if not ADMIN_TOKEN or not token or token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: invalid or missing admin token.",
        )


class ChatRequest(BaseModel):
    message: str = Field(..., max_length=2000)
    top_k: int = Field(default=4, ge=1, le=8)


class Source(BaseModel):
    name: str
    page: Optional[int] = None
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


def retrieve(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    with knowledge_base._lock:
        if (
            not knowledge_base.index_ready
            or knowledge_base.vectorizer is None
            or knowledge_base.matrix is None
            or not knowledge_base.documents
        ):
            return []
        docs = knowledge_base.documents
        vec = knowledge_base.vectorizer
        mat = knowledge_base.matrix

    query_vector = vec.transform([query])
    scores = cosine_similarity(query_vector, mat).flatten()

    ranked = scores.argsort()[::-1]
    results = []

    for index in ranked:
        score = float(scores[index])
        if score <= 0:
            continue

        item = docs[index].copy()
        item["score"] = score
        results.append(item)

        if len(results) >= max(1, min(top_k, 8)):
            break

    return results


SYSTEM_INSTRUCTION = """
You are AyurVeda, an educational Ayurvedic health-awareness assistant.

You must answer primarily from the supplied CONTEXT. The context comes from documents curated by the project owner.

Rules:
1. Do not diagnose diseases.
2. Do not prescribe medicines or tell a user to stop prescribed treatment.
3. Do not claim that an Ayurvedic remedy cures a disease unless the supplied context explicitly supports that claim; even then, describe it as the source's claim rather than established medical fact.
4. Clearly distinguish traditional Ayurvedic knowledge from modern scientific evidence.
5. Use the supplied CONTEXT as the primary source for Ayurveda and health claims. If no relevant context is supplied, you may answer general, non-diagnostic educational questions from your broad knowledge, but clearly say when the answer is general knowledge rather than retrieved project evidence.
6. Never invent studies, citations, dosages, contraindications, authors, or sources.
7. For emergencies or potentially serious symptoms, encourage appropriate urgent medical care instead of suggesting home remedies.
8. For pregnancy, children, medication interactions, serious chronic disease, or other high-risk situations, be cautious and encourage consultation with a qualified healthcare professional.
9. Keep answers concise and understandable.
10. Mention supplied sources only when CONTEXT is present. Never invent source names or claim that a source informed the answer when no context was supplied.

This is a prototype for education and health awareness, not a replacement for professional medical care.
""".strip()


def build_prompt(question: str, contexts: list[dict[str, Any]]) -> str:
    context_text = "\n\n".join(
        [
            f"SOURCE: {item['name']}"
            + (f" | PAGE: {item['page']}" if item.get("page") else "")
            + f"\n{item['text']}"
            for item in contexts
        ]
    )

    return f"""
{SYSTEM_INSTRUCTION}

CONTEXT:
{context_text or "No relevant context was retrieved."}

USER QUESTION:
{question}

Answer the user's question helpfully. Use retrieved context first. For general topics such as learning, sleep, memory, nutrition basics, or everyday explanations, you may use general knowledge when retrieval is empty. For medical, diagnostic, treatment, medication, pregnancy, child-health, or emergency claims, remain conservative, avoid personalized instructions, and recommend appropriate professional care when needed. Do not invent citations or sources. If you use general knowledge, label it as general information rather than knowledge-base evidence.
""".strip()


@app.get("/health")
@app.get("/api/health")
def health():
    with knowledge_base._lock:
        index_ready = knowledge_base.index_ready
        index_loading = knowledge_base.index_loading
        documents_loaded = knowledge_base.documents_loaded
        index_error = knowledge_base.index_error
        meta = knowledge_base.metadata

    data: dict[str, Any] = {
        "status": "degraded" if (index_error or not index_ready) else "ok",
        "index_ready": index_ready,
        "index_loading": index_loading,
        "documents_loaded": documents_loaded,
        "gemini_configured": bool(GEMINI_API_KEY),
        "index_type": "prebuilt_tfidf",
        "index_version": meta.get("version", 1) if meta else None,
    }
    if index_error:
        data["index_error"] = index_error
    return data


@app.get("/api/sources")
def sources():
    with knowledge_base._lock:
        if not knowledge_base.index_ready:
            return {"documents": []}
        docs = knowledge_base.documents

    unique: dict[str, int] = {}
    for item in docs:
        key = item["name"]
        unique.setdefault(key, 0)
        unique[key] += 1

    return {
        "documents": [
            {"name": name, "pages_or_chunks": count}
            for name, count in sorted(unique.items())
        ]
    }


@app.post("/api/admin/reindex")
def admin_reindex(authenticated: None = Depends(verify_admin)):
    try:
        metadata = knowledge_base.rebuild_sync()
        return {
            "status": "ok",
            "message": "Knowledge base index rebuilt and reloaded successfully.",
            "documents": metadata.get("documents"),
            "chunks": metadata.get("chunks"),
            "matrix_shape": metadata.get("matrix_shape"),
            "created_at": metadata.get("created_at"),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Reindex failed: {exc}",
        )


@app.get("/api/admin/status")
def admin_status(authenticated: None = Depends(verify_admin)):
    with knowledge_base._lock:
        return {
            "index_ready": knowledge_base.index_ready,
            "index_loading": knowledge_base.index_loading,
            "documents_loaded": knowledge_base.documents_loaded,
            "index_error": knowledge_base.index_error,
            "metadata": knowledge_base.metadata,
        }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    with knowledge_base._lock:
        is_loading = knowledge_base.index_loading
        has_error = knowledge_base.index_error is not None
        is_ready = knowledge_base.index_ready

    if is_loading:
        raise HTTPException(
            status_code=503,
            detail="The Ayurveda knowledge base is currently loading. Please try again shortly.",
        )

    if has_error or not is_ready:
        raise HTTPException(
            status_code=503,
            detail="The Ayurveda knowledge base is temporarily unavailable. Please try again shortly.",
        )

    if client is None:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured on the server.",
        )

    contexts = retrieve(request.message, request.top_k)
    prompt = build_prompt(request.message, contexts)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        answer = (response.text or "").strip()
    except Exception as exc:
        logger.error("Gemini request failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Gemini could not generate a response. Check the API key, model and quota.",
        )

    sources_list = [
        Source(
            name=item["name"],
            page=item.get("page"),
            snippet=item["text"][:260].replace("\n", " "),
        )
        for item in contexts
    ]

    return ChatResponse(answer=answer, sources=sources_list)
