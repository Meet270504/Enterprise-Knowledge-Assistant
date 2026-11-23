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
| `QUERY_RATE_LIMIT_PER_IP` | Max `/api/query` calls per IP per hour (`0` = off; default `8`) |
| `QUERY_DAILY_GLOBAL_LIMIT` | Max queries per UTC day site-wide (`0` = off; default `40`) |
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

## Deployment (Render + Neon, OpenAI recruiter demo)

Cheap path: **Render** free web (Docker) + **Neon** free Postgres. Recruiters see real **OpenAI** answers; uploads stay locked and query caps limit spend.

### 1. Protect OpenAI spend (do this first)

1. Open [OpenAI usage limits](https://platform.openai.com/settings/organization/limits)
2. Set a low **monthly budget / hard limit** (e.g. **$5–10**) and an email alert
3. Prefer a key used only for this demo

### 2. Neon Postgres + pgvector

1. Create a free project at [neon.tech](https://neon.tech)
2. Copy the connection string (`postgresql://…`)
3. Rewrite the scheme to SQLAlchemy async:
   - `postgresql://` → `postgresql+asyncpg://`
   - Keep `?ssl=require` (or Neon’s SSL query params)
4. In the Neon SQL editor (optional check): `CREATE EXTENSION IF NOT EXISTS vector;`  
   The app also runs this on startup.

### 3. Render web service

1. [Render](https://render.com) → **New** → **Web Service** → connect this GitHub repo
2. Runtime: **Docker** (uses the repo `Dockerfile`). Free plan is fine; expect a **cold start** after idle
3. Health check path: `/api/health`
4. Set environment variables (Blueprint defaults live in `render.yaml`):

```env
DEMO_MODE=false
SEED_DEMO_DOCUMENTS=true
PUBLIC_DEMO=true
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
TOP_K=3
QUERY_RATE_LIMIT_PER_IP=8
QUERY_DAILY_GLOBAL_LIMIT=40
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST/DB?ssl=require
OPENAI_API_KEY=sk-...
```

`DEMO_MODE` **must** be `false` and `OPENAI_API_KEY` set, or the UI stays in local demo mode.  
`PUBLIC_DEMO=true` blocks anonymous uploads/deletes so strangers cannot burn embeddings on large files.

### 4. Verify

1. Open the Render URL — badge should show **OpenAI · gpt-4o-mini**, not Local
2. Library should list the seeded Contoso North sample docs
3. Ask: `Is MFA required for VPN access?` — expect a cited OpenAI answer
4. Upload should be disabled
5. Excess questions return **429** with a demo-budget message (raise `QUERY_*` temporarily on interview day)

Never commit or paste your OpenAI key into the README, screenshots, or client-side code.

### Zero-cost local-demo host (no OpenAI)

If you only want evidence excerpts without a key: `DEMO_MODE=true`, leave `OPENAI_API_KEY` empty, keep `PUBLIC_DEMO=true`.

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
| Query returns 429 | Per-IP or daily demo budget hit — wait, or raise `QUERY_RATE_LIMIT_PER_IP` / `QUERY_DAILY_GLOBAL_LIMIT` |
| Badge still says Local on Render | Set `DEMO_MODE=false` **and** a non-empty `OPENAI_API_KEY` |
| `type "vector" does not exist` on Neon | Run `CREATE EXTENSION vector` (or use a Neon image/role that allows it) |
| Port already in use | Set `PORT=8001` (or another free port) |

---

## License / attribution

Portfolio project for demonstration. Sample “Contoso North” policies are fictional.
