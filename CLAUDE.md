# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A greenfield RAG platform: upload a PDF → parse with a VLM → chunk with **Contextual Retrieval** (Anthropic technique) → index into Qdrant → ask questions in a Playground. All LLM/VLM/embedding calls go to **FPT AI Marketplace** (OpenAI-compatible API) via the `openai` library. Backend is FastAPI + SQLAlchemy 2 + SQLite; frontend is React + Vite + TypeScript.

Note: code comments, docstrings, prompts, and the README are written in Vietnamese. User-facing responses (LLM answers, error messages) are also Vietnamese by design.

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
frontend/src/
  api/client.ts        backend client
  pages/               Upload, Documents, Playground
infra/                 MLflow + RustFS + Postgres compose (independent of app)
```

## Load-bearing config (read before touching model calls)

Model IDs and vector dimension come from `.env` via `config.py`. Two settings break the pipeline silently if wrong:

- **`EMBED_DIM`** must match the embedding model's output dimension, or Qdrant upsert fails (collection is created once at this size; changing it later means recreating the collection).
- **`FPT_VLM_MODEL`** must be a genuine **vision** model (accepts `image_url`); a chat-only model silently returns empty text. `PARSE_TEXT_FALLBACK=true` falls back to the PDF text layer when the VLM returns empty.
- **`FPT_ENABLE_PROMPT_CACHE`** — keep `false`; FPT hasn't confirmed `cache_control` support.

## Key invariants

- **Two-store design**: SQLite holds all raw text (documents, per-page/-chunk text). Qdrant holds only vectors + a *small* payload (`document_id, chunk_id, chunk_index, title, final_content`). Never move bulk raw text into Qdrant. `document_id` is a keyword index for filtered delete.
- **Pipeline** runs in the background via `BackgroundTasks` (own DB session); reprocess wipes old pages/chunks + Qdrant points first, so it's idempotent.
- **LLM boundary**: add new model interactions in `llm_client.py`, not by calling `openai` directly elsewhere.
- **Tests** (`backend/tests/`) are pure offline unit tests over `chunking_service`; keep new tests offline (FPT-dependent paths aren't covered).

## Known v1 shortcuts (per README)
`BackgroundTasks` instead of Celery; `create_all` instead of Alembic; CORS `allow_origins=["*"]`; Vite dev server instead of a static nginx build. Don't treat these as bugs unless the task is specifically to harden them.
