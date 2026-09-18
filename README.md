# 🌿 AyurVeda — A RAG-based Source Grounded AI ChatBot 

An **Ayurvedic health-awareness chatbot** built with:

- React + Vite frontend
- FastAPI backend
- Gemini API
- Basic local RAG using TF-IDF
- PDF/TXT document ingestion
- Source snippets/citations

## Try it out Here:
https://ayurveda-rag-prototype.onrender.com

## What it does

```text
User question
      ↓
FastAPI
      ↓
TF-IDF retrieval from your documents
      ↓
Top relevant passages
      ↓
Gemini
      ↓
Grounded answer + source snippets
      ↓
React UI
```

The prototype uses **TF-IDF for retrieval** instead of a vector database. This keeps it very small and avoids embedding API calls while you are experimenting with the free Gemini API.

When no bundled document matches a question, the assistant can still answer general educational questions using Gemini's broader knowledge. It labels those answers as general information; Ayurveda and health claims continue to prioritize the local source context and safety rules.

## Health disclaimer

This is an educational prototype, not a doctor or medical diagnostic system.

It must not be used to diagnose disease, replace professional medical care, or decide whether to start/stop/change prescribed treatment.

For the real project, replace the sample knowledge files with carefully curated, legally usable and authoritative sources.

## New product experience

The frontend now includes a professional landing page, Supabase sign-in/sign-up flow, responsive assistant workspace, saved conversation history, source cards, copy and regenerate actions, dark mode, and dedicated About and Safety views.

Authentication is handled by Supabase Auth, while conversations and messages are persisted in Supabase PostgreSQL. A production release should still configure email verification, password policies, backups, and monitoring.


## Supabase persistence

The application now uses Supabase Auth for email/password accounts and Supabase PostgreSQL for user-owned conversations and messages. Run [supabase/schema.sql](supabase/schema.sql) once in the Supabase SQL Editor. Row Level Security ensures users can only access their own records.

Create `frontend/.env` from [frontend/.env.example](frontend/.env.example):

```env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

Only the Supabase URL and anon key belong in the frontend. Never put a Supabase service-role key or Gemini key in `frontend/.env`.

---

# 1. Project structure

```text
ayurveda-rag-prototype/
│
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   └── data/
│       ├── ayurveda_basics.txt
│       └── safety_example.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
│
└── README.md
```

---

# 2. Prerequisites

Install:

- Python 3.10+
- Node.js 18+
- Git
- a Gemini API key

---

# 3. Get a Gemini API key

Create a Gemini API key using Google's Gemini API/AI Studio.

Then configure it locally.

Create:

```text
backend/.env
```

from:

```text
backend/.env.example
```

Set:

```env
GEMINI_API_KEY=YOUR_KEY_HERE
GEMINI_MODEL=gemini-2.5-flash
FRONTEND_URL=http://localhost:5173
```

The model is configurable. If your Gemini account/API currently exposes another supported model, change `GEMINI_MODEL`.

Do not commit the API key.

---

# 4. Start the FastAPI backend

Open a terminal:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

macOS/Linux:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 4. Building the RAG Index

The backend uses a **pre-built TF-IDF index** architecture. Text extraction from PDFs and TF-IDF matrix fitting are done offline before deployment. Normal server startups load the pre-built index in milliseconds without running expensive PDF processing.

To build or update the index locally:

```bash
cd backend
python scripts/build_index.py
```

This will:
1. Process all `.txt` and `.pdf` files recursively in `backend/data/`.
2. Extract text and create structured chunks.
3. Fit the `TfidfVectorizer` (English stopwords, 1-2 n-grams, max 12,000 features).
4. Save the pre-built index files into `backend/index/`:
   - `chunks.json` (all chunks with page/source metadata)
   - `vectorizer.joblib` (fitted vectorizer)
   - `tfidf_matrix.npz` (sparse TF-IDF matrix)
   - `metadata.json` (index statistics and build timestamp)
5. Atomically verify and install the index.

### Committing the Index to Git
Because the total index size is compact (~3.8 MB for ~1,100 chunks), `backend/index/` is tracked in Git:

```bash
git add backend/index/
git commit -m "chore: update pre-built RAG index"
git push
```

Render will then deploy the pre-built index and boot instantly.

---

# 5. Start the FastAPI backend

With the pre-built index in place, start FastAPI:

```bash
cd backend
uvicorn app:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

Swagger documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

---

# 5. Start React

Open another terminal:

```bash
cd frontend
```

Install:

```bash
npm install
```

Create:

```text
frontend/.env
```

with:

```env
VITE_API_URL=http://localhost:8000
```

Run:

```bash
npm run dev
```

Open the Vite URL shown in the terminal, normally:

```text
http://localhost:5173
```

---

# 6. How the RAG works

This prototype uses a simple local TF-IDF retrieval system.

It loads:

```text
backend/data/
```

and supports:

```text
.txt
.pdf
```

For PDFs, each page is treated as a retrievable document segment.

Yes, you can add PDFs to increase the available context. Place legally usable, text-based PDFs anywhere under `backend/data/` (including subfolders), then restart FastAPI so the index is rebuilt. Scanned/image-only PDFs need OCR before they can be retrieved reliably.

For a question:

```text
"What is Ayurveda?"
```

the backend:

1. converts the question into TF-IDF features
2. compares it with the document passages
3. selects the most relevant passages
4. sends those passages to Gemini
5. asks Gemini to answer using those passages
6. returns the answer and retrieved sources

This is basic RAG.

---

# 7. Where to put your documents

Put your documents here:

```text
backend/data/
```

For example:

```text
backend/data/

charaka_samhita.pdf
safety_guidelines.pdf
ayurveda_lifestyle.txt
medicinal_plants.pdf
research_paper_01.pdf
```

You can also create subfolders.

Example:

```text
backend/data/

classical/
    charaka_samhita.pdf
    sushruta_samhita.pdf

research/
    paper_01.pdf
    paper_02.pdf

safety/
    safety_guidelines.pdf
```

The backend searches recursively.

---

# 8. Important: document quality

Do not just download random Ayurveda PDFs.

For a serious version of this project, curate sources carefully.

Prefer:

- authentic classical texts
- government/official publications
- peer-reviewed research
- systematic reviews
- clinical studies
- reliable safety references

Record source information.

Avoid treating a traditional claim as equivalent to modern clinical evidence.

---

# 9. Adding a new document

1. Copy your new `.txt` or text-based `.pdf` document into:

```text
backend/data/
```
(or any subfolder, such as `backend/data/classical/`, `backend/data/medicinal_plants/`, `backend/data/research/`, or `backend/data/safety/`).

2. Rebuild the index offline:

```bash
cd backend
python scripts/build_index.py
```

Alternatively, if the server is already running in production or staging, trigger an atomic reindex via the admin endpoint:

```bash
curl -X POST https://your-backend.onrender.com/api/admin/reindex \
  -H "X-Admin-Token: YOUR_ADMIN_TOKEN"
```

3. Commit and push the updated `backend/index/` files to Git if deploying a new release.

---

# 10. Current retrieval limitation

This prototype uses TF-IDF.

That means it is NOT a sophisticated semantic vector RAG system.

For example, TF-IDF works well when the question and document use related words.

A future version can replace it with:

```text
Gemini embeddings
        ↓
pgvector / Qdrant
        ↓
semantic search
```

or another vector database.

For the first prototype, TF-IDF keeps:

- setup simple
- deployment cheap
- debugging easy
- Gemini API usage low

---

# 11. API endpoints

## Health Check

```http
GET /health
GET /api/health
```

Returns server readiness, index status, and chunk count:
```json
{
  "status": "ok",
  "index_ready": true,
  "index_loading": false,
  "documents_loaded": 1092,
  "gemini_configured": true,
  "index_type": "prebuilt_tfidf",
  "index_version": 1
}
```

## Sources

```http
GET /api/sources
```

Returns the list of documents and page/chunk counts currently indexed.

## Admin Reindex (Protected)

```http
POST /api/admin/reindex
Header: X-Admin-Token: <ADMIN_TOKEN>
```

Re-scans `backend/data/`, rebuilds the TF-IDF matrix in a temporary staging directory, validates it, atomically replaces `backend/index/`, and hot-reloads the knowledge base into memory without server restarts.

## Admin Status (Protected)

```http
GET /api/admin/status
Header: X-Admin-Token: <ADMIN_TOKEN>
```

Returns current index metadata, chunk counts, and memory state.

## Chat

```http
POST /api/chat
```

Request:

```json
{
  "message": "What is Ayurveda?",
  "top_k": 4
}
```

Response:

```json
{
  "answer": "...",
  "sources": [
    {
      "name": "ayurveda_basics.txt",
      "page": null,
      "snippet": "..."
    }
  ]
}
```

---


