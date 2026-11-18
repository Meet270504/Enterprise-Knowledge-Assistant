# Enterprise Generative AI Knowledge Assistant

Portfolio document Q&A app: upload company documents, ask natural-language questions, and get answers grounded in retrieved passages with visible citations.

**Stack:** Python 3.12 · FastAPI · LangChain · OpenAI (configurable) · PostgreSQL · pgvector

> **Scope:** This is a **single-tenant portfolio demo**. It has no sign-in, role-based access control, or tenant isolation. **Do not use it with confidential enterprise data**, and do not treat AI answers as authoritative without checking the cited sources.

---

## Features

- Upload PDF, DOCX, TXT, Markdown, and CSV; validate type/size; extract text; chunk with overlap; embed; store in PostgreSQL/pgvector
- Document processing status, chunk counts, and error messages (including guidance that scanned PDFs need OCR)
- RAG query with optional department/category filters, relevance threshold, citation validation
- Embedding isolation by `embedding_provider` + `embedding_model` (OpenAI vectors are never mixed with local demo vectors)
- **Local demo mode** (no OpenAI key): fictional sample policies, deterministic retrieval, evidence excerpts (not fake GPT answers)
- Same-origin responsive browser UI + OpenAPI docs at `/docs`
- Docker Compose for API + pgvector Postgres
- `PUBLIC_DEMO` flag to disable anonymous uploads/deletes

---

## Quick start (Docker Compose)

Requires Docker Desktop (or another Docker engine).

```bash
cp .env.example .env
# Optional: set OPENAI_API_KEY and DEMO_MODE=false for OpenAI mode
docker compose up --build
```

Open:

- UI: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Default Compose credentials are local-only (`eka` / `eka_secret`). Change them for any shared host.

---

## Local setup (venv + Postgres)

### 1. PostgreSQL with pgvector

You need a Postgres instance with the `vector` extension. Easiest path:

```bash
docker compose up -d db
```

Or install Postgres + [pgvector](https://github.com/pgvector/pgvector) yourself and create a database/user matching `DATABASE_URL`.

### 2. Python environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Run the API

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
```

Or:

```bash
python -m app.main
```

The app respects the platform `PORT` environment variable.

---

## Configuration

See `.env.example`. Important variables:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | Enables OpenAI embeddings + chat when demo mode is off |
| `OPENAI_CHAT_MODEL` | Default `gpt-4o-mini` (set `gpt-4o` to upgrade) |
| `OPENAI_EMBEDDING_MODEL` | Default `text-embedding-3-small` |
| `DEMO_MODE` | `true` → local deterministic retrieval + evidence answers |
| `SEED_DEMO_DOCUMENTS` | Seed fictional PTO/security/remote/travel/onboarding docs |
| `PUBLIC_DEMO` | Disable uploads & deletes; fictional docs only |
| `DATABASE_URL` | Async SQLAlchemy URL (`postgresql+asyncpg://…`) |
| `MAX_UPLOAD_BYTES` | Upload size limit (default 10 MB) |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Chunking |
| `TOP_K` / `RELEVANCE_THRESHOLD` | Retrieval |

### Enable OpenAI mode

1. Put a real key in `.env`: `OPENAI_API_KEY=sk-...`
2. Set `DEMO_MODE=false`
3. Optionally set `OPENAI_CHAT_MODEL=gpt-4o`
4. Restart the app
5. Re-upload or re-seed documents **in OpenAI mode** so chunks are embedded with the OpenAI model (retrieval never mixes providers/models)

### Local demo mode (no key)

Leave `OPENAI_API_KEY` empty and/or `DEMO_MODE=true`. The UI badge shows **Local demo mode**. Answers list matching excerpts with similarity scores instead of calling GPT.

---

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness + mode + DB check |
| `GET` | `/api/config` | Non-secret runtime config for the UI |
| `GET` | `/api/documents` | List documents + status |
| `POST` | `/api/documents` | Multipart upload (`file`, `department`, `category`) |
| `DELETE` | `/api/documents/{id}` | Delete document + chunks |
| `POST` | `/api/query` | JSON `{question, department?, category?, top_k?}` |

Interactive docs: `/docs`.

### Example query

```bash
curl -s http://127.0.0.1:8000/api/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Is MFA required for VPN access?","department":"Security"}'
```

---

## Retrieval evaluation

With the server running and samples seeded:

```bash
python scripts/evaluate_retrieval.py --base-url http://127.0.0.1:8000
```

Representative questions expect hits on the fictional PTO, security, travel, remote-work, and onboarding samples, plus an abstention case.

---

## Project layout

```
app/
  main.py              # FastAPI app + static UI
  config.py            # Settings from env
  database.py          # Async SQLAlchemy + pgvector bootstrap
  models.py            # Document / Chunk tables
  schemas.py           # Request/response models
  api/routes/          # health, documents, query
  services/            # extraction, chunking, embeddings, ingestion, rag, demo seed
  static/              # Browser UI
sample_docs/           # Fictional Contoso North policies
scripts/evaluate_retrieval.py
Dockerfile
docker-compose.yml
.env.example
```

---

## Security notes

- Secrets stay in environment variables; `.env` is gitignored
- Upload validation: extension allow-list, size limit, sanitized filenames, no path traversal
- API keys are never sent to the browser
- Citation markers from the model are validated against retrieved sources; fabricated `[S#]` markers are stripped
- Prompt instructs the model to treat document text as untrusted reference material
- **Not production-hardened for multi-user confidential data**

---

## Deployment (public Docker host)

This repo is deployment-ready. A live recruiter URL is **not** included until you deploy it.

### What you need to provide

1. A Docker-capable host with a public HTTPS URL, for example:
   - [Railway](https://railway.app), [Render](https://render.com), [Fly.io](https://fly.io), or a VPS with Docker
2. A PostgreSQL database with **pgvector** (Compose `db` service, managed Postgres + extension, or Supabase/Neon with pgvector)
3. Optional: `OPENAI_API_KEY` for OpenAI mode
4. For a public anonymous demo: set `PUBLIC_DEMO=true`, `DEMO_MODE=true`, `SEED_DEMO_DOCUMENTS=true`, and **do not** upload real company documents

### Suggested public-demo env

```env
DEMO_MODE=true
SEED_DEMO_DOCUMENTS=true
PUBLIC_DEMO=true
OPENAI_API_KEY=
PORT=8000
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DB
```

### Deploy outline

1. Push this repository to GitHub (or your git host)
2. Create a Postgres/pgvector service and copy its URL into `DATABASE_URL`
3. Deploy the Dockerfile; ensure `PORT` is provided by the platform
4. Confirm `CREATE EXTENSION vector` is allowed (the app runs this on startup)
5. Open the service URL — you should see the UI in **Local demo mode** with sample docs

Never commit or paste your OpenAI key into the README, screenshots, or client-side code.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `connection refused` to Postgres | Start DB (`docker compose up -d db`) and check `DATABASE_URL` |
| `type "vector" does not exist` | Enable pgvector / use `pgvector/pgvector` image |
| Empty PDF text | Scanned PDFs need OCR before upload; this app extracts digital text only |
| Demo answers look “non-GPT” | Expected in local demo mode — enable OpenAI mode for model answers |
| No results after switching modes | Embeddings are isolated; re-seed/re-upload under the active provider/model |
| Uploads return 403 | `PUBLIC_DEMO=true` disables uploads/deletes |
| Port already in use | Set `PORT=8001` (or another free port) |

---

## License / attribution

Portfolio project for demonstration. Sample “Contoso North” policies are fictional.
