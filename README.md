# 🌿 AyurVeda — Small RAG Prototype

A small **Ayurvedic health-awareness chatbot prototype** built with:

- React + Vite frontend
- FastAPI backend
- Gemini API
- Basic local RAG using TF-IDF
- PDF/TXT document ingestion
- Source snippets/citations
- Render deployment

This is intentionally a small prototype. It is **not** the final Azure architecture discussed for the larger project.

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

## Deploy with Supabase and Render

1. Create a Supabase project and copy its **Project URL** and **anon public key** from Project Settings > API.
2. Open Supabase SQL Editor and run [supabase/schema.sql](supabase/schema.sql).
3. In Supabase Authentication > URL Configuration, add the deployed frontend URL as the Site URL and redirect URL. For local development, use `http://localhost:5173`.
4. Create a Render **Web Service** for this repository with root directory `backend`, build command `pip install -r requirements.txt`, and start command `uvicorn app:app --host 0.0.0.0 --port $PORT`.
5. Add these private Render environment variables to the backend service:

```env
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-flash-lite-latest
FRONTEND_URL=https://your-frontend.onrender.com
ADMIN_TOKEN=use_a_long_random_value
```

6. Create a Render **Static Site** for the same repository with root directory `frontend`, build command `npm install && npm run build`, and publish directory `dist`.
7. Add these frontend environment variables to the Render static site before deploying:

```env
VITE_API_URL=https://your-backend.onrender.com
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

The Supabase anon key is designed for frontend use with Row Level Security enabled. Never expose `GEMINI_API_KEY`, `ADMIN_TOKEN`, a database password, or a Supabase service-role key in the frontend. The frontend now uses Supabase Auth and RLS-protected Postgres tables for accounts, conversations, and messages; FastAPI continues to handle retrieval and Gemini generation.

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

You do NOT need:

- Qdrant
- PostgreSQL
- Azure
- OpenAI
- Streamlit

for this prototype.

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

Start FastAPI:

```bash
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

Copy your document into:

```text
backend/data/
```

Then restart FastAPI:

```bash
uvicorn app:app --reload
```

The documents are loaded when the server starts.

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

# 11. Render deployment

Render can deploy FastAPI as a free web service and React as a free static site. Free Render web services spin down after 15 minutes of inactivity and have an ephemeral filesystem, so this prototype should treat `backend/data` as part of the Git repository rather than as user-uploaded persistent storage.

## Backend

Push this project to GitHub.

On Render:

```text
New
→ Web Service
→ Connect your GitHub repository
```

Set the backend root directory to:

```text
backend
```

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

Choose the Free plan for the prototype.

Add environment variables:

```text
GEMINI_API_KEY = your Gemini API key
GEMINI_MODEL = gemini-2.5-flash
FRONTEND_URL = https://YOUR-FRONTEND.onrender.com
```

After deployment, you should receive a URL such as:

```text
https://ayurveda-api.onrender.com
```

Test:

```text
https://ayurveda-api.onrender.com/health
```

---

# 12. Deploy the React frontend

On Render:

```text
New
→ Static Site
→ Connect the same GitHub repository
```

Set root directory:

```text
frontend
```

Build command:

```bash
npm install && npm run build
```

Publish directory:

```text
dist
```

Add:

```text
VITE_API_URL=https://YOUR-BACKEND.onrender.com
```

Example:

```text
VITE_API_URL=https://ayurveda-api.onrender.com
```

Deploy.

Render will provide a URL such as:

```text
https://ayurveda.onrender.com
```

---

# 13. Render architecture

```text
                  User
                   |
                   v
        +----------------------+
        | React Static Site    |
        | Render               |
        +----------+-----------+
                   |
                   | HTTPS
                   v
        +----------------------+
        | FastAPI Web Service  |
        | Render Free          |
        +----------+-----------+
                   |
             +-----+-----+
             |           |
             v           v
        TF-IDF RAG    Gemini API
             |
             v
      backend/data/
      PDF + TXT files
```

---

# 14. Important Render limitation

Render Free web services have an ephemeral filesystem.

Do NOT create a production document-upload system that expects files uploaded through the API to remain on disk.

For this prototype:

```text
GitHub repository
       ↓
backend/data/
       ↓
Render deployment
```

If you add a new knowledge document:

```text
1. Put it in backend/data/
2. Commit it
3. Push to GitHub
4. Render redeploys
5. Backend loads the new document
```

For the future Azure version, move the documents to Azure Blob Storage.

---

# 15. API endpoints

## Health

```http
GET /health
```

Returns service status and number of loaded documents.

## Sources

```http
GET /api/sources
```

Returns the documents currently loaded.

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

# 16. What this prototype does NOT include

This is intentionally small.

It does NOT yet include:

- login/signup
- PostgreSQL
- pgvector
- Qdrant
- Azure
- Blob Storage
- admin dashboard
- persistent chat history
- advanced reranking
- semantic embeddings
- hybrid retrieval
- multilingual support
- production-grade medical evidence evaluation

Those belong to the next version.

---

# 17. Why this prototype is useful

The purpose is to validate the core idea first:

```text
Documents
    ↓
Retrieval
    ↓
Gemini
    ↓
Grounded answer
    ↓
React UI
```

Once this works reliably, you can replace only the retrieval layer with:

```text
Documents
    ↓
Gemini embeddings
    ↓
PostgreSQL + pgvector
    ↓
Semantic retrieval
    ↓
Gemini
```

without redesigning the entire application.

---

# 18. Suggested next upgrade

After the prototype works, the next architecture should be:

```text
React
   ↓
FastAPI
   ↓
LlamaIndex
   ↓
Gemini
   ↓
PostgreSQL + pgvector
   ↑
Azure Blob Storage
```

Then add:

- authentication
- user accounts
- chat history
- admin document upload
- evidence metadata
- better citations
- evaluation
- safety classification
- Azure deployment

---

# 19. Health-safety requirements for future versions

The production version should include a stronger safety layer.

Especially for questions involving:

- pregnancy
- children
- medication interactions
- serious chronic illness
- severe symptoms
- emergencies

The assistant should not present itself as a doctor or recommend replacing prescribed treatment.

---

# 20. Troubleshooting

## Gemini API error

Check:

```text
GEMINI_API_KEY
```

and:

```text
GEMINI_MODEL
```

Also check that your Gemini API quota has not been exhausted.

## CORS error

Check:

```text
FRONTEND_URL
```

on the backend.

For local development:

```text
http://localhost:5173
```

For Render:

```text
https://your-frontend.onrender.com
```

## Frontend cannot reach backend

Check:

```text
VITE_API_URL
```

and make sure it contains the deployed backend URL.

## No sources are returned

Check:

```text
backend/data/
```

and restart the backend.

## PDF does not extract correctly

Some PDFs contain scanned images rather than selectable text.

This prototype does not include OCR.

For the next version, add OCR/document-processing support where necessary.

---

# 21. Prototype checklist

Before deployment:

- [ ] Gemini API key works
- [ ] Backend starts
- [ ] `/health` works
- [ ] Documents load
- [ ] `/api/sources` works
- [ ] `/api/chat` works
- [ ] React starts
- [ ] React can call FastAPI
- [ ] RAG returns relevant source snippets
- [ ] Gemini answers from retrieved context
- [ ] No API key is committed
- [ ] Render backend deployed
- [ ] Render frontend deployed
- [ ] `VITE_API_URL` points to Render backend
- [ ] CORS is configured

---

# 22. Security reminder

Never put:

```text
GEMINI_API_KEY
```

inside React.

The Gemini API key must exist only on the FastAPI server.

Correct:

```text
React
  ↓
FastAPI
  ↓
Gemini
```

Incorrect:

```text
React
  ↓
Gemini API directly
```

because that would expose your API key to browser users.

---

# 23. Final goal

This prototype is the first small working version of the larger AyurVeda project.

Start small.

Validate:

1. RAG retrieval
2. Gemini responses
3. source grounding
4. React UI
5. Render deployment

Then progressively add:

PostgreSQL
→ pgvector
→ better embeddings
→ document metadata
→ authentication
→ chat history
→ admin ingestion
→ safety evaluation
→ Azure deployment
