# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A greenfield RAG platform: upload a PDF → parse with a VLM → chunk with **Contextual Retrieval** (Anthropic technique) → index into Qdrant → ask questions in a Playground. All LLM/VLM/embedding calls go to **FPT AI Marketplace** (OpenAI-compatible API) via the `openai` library. Backend is FastAPI + SQLAlchemy 2 + SQLite; frontend is React + Vite + TypeScript.

Note: code comments, docstrings, prompts, and the README are written in Vietnamese. User-facing responses (LLM answers, error messages) are also Vietnamese by design.

## Tech stack
Core frameworks/systems only; versions are pinned in `requirements.txt` / `package.json`, and model IDs + `EMBED_DIM` come from `.env` (never hardcoded).

**Backend**

| Tech | Role |
|------|------|
| FastAPI | REST API framework |
| SQLAlchemy 2 + SQLite | ORM + relational store (all raw text) |
| Pydantic 2 | Request/response schemas + `.env` config |
| Qdrant | Vector database (vectors + small payload) |
| LlamaIndex | `SentenceSplitter` chunking |
| OpenAI SDK | Client for all FPT AI Marketplace calls |
| pdfplumber | PDF page render + text-layer fallback |

**Frontend**

| Tech | Role |
|------|------|
| React 18 | UI (Upload / Documents / Playground) |
| Vite | Dev server + build/typecheck |
| TypeScript | Static typing |

**External / Infra**

| Tech | Role |
|------|------|
| FPT AI Marketplace | OpenAI-compatible LLM/VLM/embedding provider |
| Docker Compose | App + infra orchestration |
| MLflow | Experiment tracking (`infra/` stack) |
| RustFS | S3-compatible object storage (MLflow artifacts + optional app blobs) |
| Postgres | MLflow backend store (`infra/` stack) |

## Commands

```bash
# Full stack (recommended) — needs .env with FPT_API_KEY + model IDs
cp .env.example .env
docker compose up --build
# Qdrant dashboard: :6333/dashboard | Backend Swagger: :8000/docs | Frontend: :5173

# Backend local
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
cd backend && pytest                                              # offline unit tests

# Frontend local
cd frontend && npm install && npm run dev
cd frontend && npm run build   # tsc -b && vite build (also the typecheck)

# Infra stack (MLflow + RustFS + Postgres) — separate compose
cd infra && cp .env.example .env && docker compose up --build
```

## Project structure

```
backend/app/
  config.py            pydantic-settings — all model IDs + EMBED_DIM from .env (never hardcoded)
  db.py                SQLite engine, create_all on startup (no migrations)
  main.py              FastAPI app
  models/              SQLAlchemy: document, page, chunk
  schemas/             Pydantic request/response
  routers/             /api endpoints: documents, playground
  services/
    pipeline.py        background orchestrator (uploaded → parsed → chunking → indexing → indexed)
    parsing_service.py PDF page → PNG → VLM
    chunking_service.py SentenceSplitter + LLM contextual prefix
    embedding_service.py + qdrant_service.py  embed + upsert/search
    llm_client.py      single choke point for all FPT calls (chat/stream/vision/embed)
    storage_service.py single choke point for all blob I/O (PDF + page PNGs); local|s3 backend
frontend/src/
  api/client.ts        backend client
  pages/               Upload, Documents, Playground
infra/                 MLflow + RustFS + Postgres compose. MLflow uses RustFS for artifacts;
                       the app can optionally reuse RustFS for document blobs (STORAGE_BACKEND=s3).
```

## Load-bearing config (read before touching model calls)

Model IDs and vector dimension come from `.env` via `config.py`. Two settings break the pipeline silently if wrong:

- **`EMBED_DIM`** must match the embedding model's output dimension, or Qdrant upsert fails (collection is created once at this size; changing it later means recreating the collection).
- **`FPT_VLM_MODEL`** must be a genuine **vision** model (accepts `image_url`); a chat-only model silently returns empty text. `PARSE_TEXT_FALLBACK=true` falls back to the PDF text layer when the VLM returns empty.
- **`FPT_ENABLE_PROMPT_CACHE`** — keep `false`; FPT hasn't confirmed `cache_control` support.
- **`STORAGE_BACKEND`** — `local` (default; blobs on disk under `DATA_DIR`, Docker volume `backend_data`) or `s3` (RustFS / any S3-compatible endpoint). `s3` needs `S3_ENDPOINT_URL` + keys + `S3_BUCKET` reachable — RustFS runs in `infra/` on `:9000` (`http://rustfs:9000` inside a shared compose network). The app bucket (`rag-documents`) is deliberately separate from MLflow's `mlflow` bucket. The compose files are independent by default, so `s3` mode requires you to make RustFS reachable from the backend (shared network / external endpoint).

## Key invariants

- **Three-store design**: SQLite holds all raw text (documents, per-page/-chunk text). Qdrant holds only vectors + a *small* payload (`document_id, chunk_id, chunk_index, title, final_content`) — never move bulk raw text into Qdrant; `document_id` is a keyword index for filtered delete. Blobs (source PDF + rendered page PNGs) live in **object/FS storage** via `storage_service`, keyed as `uploads/{id}.pdf` and `images/{id}/page_*.png`; `Document.file_path` / `Page.image_ref` store these **storage keys**, not absolute paths.
- **Pipeline** runs in the background via `BackgroundTasks` (own DB session); reprocess wipes old pages/chunks + Qdrant points first, so it's idempotent.
- **LLM boundary**: add new model interactions in `llm_client.py`, not by calling `openai` directly elsewhere.
- **Storage boundary**: add new blob reads/writes/deletes in `storage_service.py`, not by calling `boto3`/`open()` directly elsewhere. Keeps `local`/`s3` swappable and offline tests boto3-free.
- **Tests** (`backend/tests/`) are pure offline unit tests over `chunking_service`; keep new tests offline (FPT-dependent paths aren't covered).

## Known v1 shortcuts (per README)
`BackgroundTasks` instead of Celery; `create_all` instead of Alembic; CORS `allow_origins=["*"]`; Vite dev server instead of a static nginx build. Don't treat these as bugs unless the task is specifically to harden them.
