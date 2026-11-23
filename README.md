# Enterprise Knowledge Assistant

Document Q&A over your own files: upload policies or notes, ask questions in plain language, and get answers grounded in retrieved passages with visible citations.

**Live demo:** [https://enterprise-knowledge-assistant-43nr.onrender.com](https://enterprise-knowledge-assistant-43nr.onrender.com)

**Stack:** Python 3.12 · FastAPI · LangChain · OpenAI · PostgreSQL · pgvector

> Single-tenant demo — no sign-in, RBAC, or tenant isolation. Do not load confidential data. Always check cited sources before trusting an answer.

---

## Features

- Upload PDF, DOCX, TXT, Markdown, and CSV with type/size checks, text extraction, overlapping chunks, embeddings, and pgvector storage
- Document status, chunk counts, and clear errors (including when scanned PDFs need OCR)
- RAG queries with optional department/category filters, relevance threshold, and citation validation
- Embedding isolation by provider + model (OpenAI and local vectors are never mixed)
- **OpenAI mode** for grounded chat answers, or **local demo mode** (no API key) with deterministic retrieval
- Optional Ollama path in local mode for grounded answers without OpenAI
- Browser UI + OpenAPI at `/docs`
- Docker Compose for API + Postgres
- `PUBLIC_DEMO` to lock uploads/deletes on shared hosts
- Per-IP and daily query limits to control OpenAI spend on public deployments

---

## Quick start (Docker Compose)

```bash
cp .env.example .env
# Optional: OPENAI_API_KEY=... and DEMO_MODE=false
docker compose up --build
```

- UI: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- API: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Default Compose DB credentials (`eka` / `eka_secret`) are for local use only — change them on any shared host.

---

## Local setup (venv + Postgres)

### 1. PostgreSQL with pgvector

```bash
docker compose up -d db
```

Or run your own Postgres with [pgvector](https://github.com/pgvector/pgvector) and point `DATABASE_URL` at it.

### 2. Python environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
# or: python -m app.main
```

---

## Configuration

See `.env.example`.

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI embeddings + chat when demo mode is off |
| `OPENAI_CHAT_MODEL` | Default `gpt-4o-mini` |
| `OPENAI_EMBEDDING_MODEL` | Default `text-embedding-3-small` |
| `DEMO_MODE` | `true` → local retrieval (no OpenAI chat) |
| `SEED_DEMO_DOCUMENTS` | Seed fictional Contoso North sample policies |
| `PUBLIC_DEMO` | Disable uploads and deletes |
| `DATABASE_URL` | `postgresql+asyncpg://…` |
| `QUERY_RATE_LIMIT_PER_IP` | Max queries per IP per hour (`0` = off; default `8`) |
| `QUERY_DAILY_GLOBAL_LIMIT` | Max queries per UTC day (`0` = off; default `40`) |
| `MAX_UPLOAD_BYTES` | Upload size limit (default 10 MB) |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Chunking |
| `TOP_K` / `RELEVANCE_THRESHOLD` | Retrieval |

### OpenAI mode

1. Set `OPENAI_API_KEY` and `DEMO_MODE=false`
2. Restart
3. Re-seed or re-upload under OpenAI mode so embeddings match the active provider

### Local demo mode

Leave the key empty and/or set `DEMO_MODE=true`. The UI shows a Local badge. Answers use retrieved excerpts (and Ollama when configured), not OpenAI chat.

---

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness + mode + DB check |
| `GET` | `/api/config` | Non-secret runtime config for the UI |
| `GET` | `/api/documents` | List documents |
| `POST` | `/api/documents` | Multipart upload (`file`, `department`, `category`) |
| `DELETE` | `/api/documents/{id}` | Delete document + chunks |
| `POST` | `/api/query` | `{question, department?, category?, top_k?}` |

```bash
curl -s http://127.0.0.1:8000/api/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"Is MFA required for VPN access?","department":"Security"}'
```

---

## Retrieval evaluation

```bash
python scripts/evaluate_retrieval.py --base-url http://127.0.0.1:8000
```

Covers sample PTO, security, travel, remote-work, and onboarding questions, plus an abstention case.

---

## Project layout

```
app/
  main.py              # FastAPI app + static UI
  config.py            # Settings from env
  database.py          # Async SQLAlchemy + pgvector
  models.py / schemas.py
  api/routes/          # health, documents, query
  services/            # extraction, chunking, embeddings, ingestion, rag, limits
  static/              # Browser UI
sample_docs/           # Fictional Contoso North policies
scripts/evaluate_retrieval.py
Dockerfile
docker-compose.yml
render.yaml
.env.example
```

---

## Security notes

- Secrets stay in environment variables; `.env` is gitignored
- Upload validation: extension allow-list, size limit, sanitized filenames
- API keys are never sent to the browser
- Model citation markers are checked against retrieved sources; fabricated markers are stripped
- Document text is treated as untrusted reference material in the prompt
- Not hardened for multi-user confidential workloads

---

## Deployment

The included setup targets **Render** (Docker web service) and **Neon** (Postgres + pgvector). Other Docker hosts work the same way: provide `DATABASE_URL`, set mode flags, and inject secrets in the platform — never in git.

### OpenAI cost controls on a public URL

1. Set a monthly budget / hard limit in the [OpenAI usage settings](https://platform.openai.com/settings/organization/limits)
2. Use `PUBLIC_DEMO=true` so anonymous users cannot upload large files
3. Keep `QUERY_RATE_LIMIT_PER_IP` and `QUERY_DAILY_GLOBAL_LIMIT` enabled (defaults: 8/hour, 40/day)
4. Prefer `gpt-4o-mini` and a modest `TOP_K` (e.g. `3`)

### Neon

1. Create a project and copy the connection string
2. Use `postgresql+asyncpg://…` and `ssl=require` (drop `channel_binding` if the driver rejects it)
3. The app runs `CREATE EXTENSION IF NOT EXISTS vector` on startup

### Render

1. New **Web Service** from this repo, runtime **Docker**, health check `/api/health`
2. Dockerfile path: `Dockerfile`
3. Environment (see also `render.yaml`):

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

Free Render instances sleep when idle; the first request after idle may take 30–60 seconds.

For a no-key public host: `DEMO_MODE=true`, empty `OPENAI_API_KEY`, `PUBLIC_DEMO=true`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `connection refused` to Postgres | Start DB / check `DATABASE_URL` |
| `type "vector" does not exist` | Enable pgvector (`CREATE EXTENSION vector`) |
| Empty PDF text | Scanned PDFs need OCR; this app reads digital text only |
| Local-style answers with a key set | Set `DEMO_MODE=false` and restart |
| No hits after switching modes | Re-seed or re-upload under the active embedding provider |
| Uploads return 403 | Expected when `PUBLIC_DEMO=true` |
| Query returns 429 | Rate or daily limit hit — wait or raise `QUERY_*` |
| Port in use | Set `PORT=8001` (or another free port) |

---

## License / attribution

Demonstration project. Sample “Contoso North” policies are fictional.
