from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from google import genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypdf import PdfReader

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

if not GEMINI_API_KEY:
    # The server can still start so /health works, but chat will return a clear error.
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="AyurVeda RAG Prototype", version="0.1.0")

origins = ["*"] if FRONTEND_URL == "*" else [FRONTEND_URL]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


def load_documents() -> list[dict[str, Any]]:
    documents = []

    if not DATA_DIR.exists():
        return documents

    for path in sorted(DATA_DIR.rglob("*")):
        if not path.is_file():
            continue

        try:
            if path.suffix.lower() == ".txt":
                text = path.read_text(encoding="utf-8")
                documents.append(
                    {
                        "name": path.name,
                        "page": None,
                        "text": text.strip(),
                    }
                )

            elif path.suffix.lower() == ".pdf":
                reader = PdfReader(str(path))
                for page_number, page in enumerate(reader.pages, start=1):
                    text = (page.extract_text() or "").strip()
                    if text:
                        documents.append(
                            {
                                "name": path.name,
                                "page": page_number,
                                "text": text,
                            }
                        )
        except Exception as exc:
            print(f"Could not load {path}: {exc}")

    return [d for d in documents if d["text"]]


DOCUMENTS = load_documents()
vectorizer = TfidfVectorizer(
    lowercase=True,
    stop_words="english",
    ngram_range=(1, 2),
    max_features=12000,
)
MATRIX = vectorizer.fit_transform([d["text"] for d in DOCUMENTS]) if DOCUMENTS else None


def retrieve(query: str, top_k: int = 4) -> list[dict[str, Any]]:
    if not DOCUMENTS or MATRIX is None:
        return []

    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, MATRIX).flatten()

    ranked = scores.argsort()[::-1]
    results = []

    for index in ranked:
        score = float(scores[index])
        if score <= 0:
            continue

        item = DOCUMENTS[index].copy()
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
            + (f" | PAGE: {item['page']}" if item["page"] else "")
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
    return {
        "status": "ok",
        "documents_loaded": len(DOCUMENTS),
        "gemini_configured": bool(GEMINI_API_KEY),
    }


@app.get("/api/sources")
def sources():
    unique = {}
    for item in DOCUMENTS:
        key = item["name"]
        unique.setdefault(key, 0)
        unique[key] += 1

    return {
        "documents": [
            {"name": name, "pages_or_chunks": count}
            for name, count in sorted(unique.items())
        ]
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

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
        print(f"Gemini request failed: {exc}")
        raise HTTPException(
            status_code=502,
            detail="Gemini could not generate a response. Check the API key, model and quota.",
        )

    sources = [
        Source(
            name=item["name"],
            page=item["page"],
            snippet=item["text"][:260].replace("\n", " "),
        )
        for item in contexts
    ]

    return ChatResponse(answer=answer, sources=sources)
