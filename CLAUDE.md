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

# Backend local (needs .env in backend/ or exported env vars)
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Backend tests (no external API calls — pure unit tests)
cd backend && pytest
cd backend && pytest tests/test_chunking.py::test_split_text -v   # single test

# Frontend local
cd frontend && npm install && npm run dev
cd frontend && npm run build   # tsc -b && vite build (also the typecheck)
```

## Configuration is load-bearing — read before touching model calls

Model IDs and vector dimension are **never hardcoded**; everything comes from `.env` via `app/config.py` (`pydantic-settings`). Two settings break the pipeline silently if wrong:

- **`EMBED_DIM`** must exactly match the embedding model's output dimension, or Qdrant upsert fails (the collection is created once with this size; changing it later requires recreating the collection).
- **`FPT_VLM_MODEL`** must be a genuine **vision** model (accepts `image_url`). A chat-only model (e.g. plain GLM-5.x) silently ignores the page image and returns empty text. The pipeline guards against this: if all pages parse empty it raises a loud, actionable error. `PARSE_TEXT_FALLBACK=true` falls back to the PDF text layer per-page when the VLM returns empty.
- **`FPT_ENABLE_PROMPT_CACHE`** — keep `false`; FPT hasn't confirmed `cache_control` support. `llm_client.chat()` attaches Anthropic-style `cache_control` when enabled and auto-retries without it if the server rejects the field.

## Architecture

### Two-store design (important invariant)
- **SQLite** holds all raw text: documents, per-page `parsed_text`, and per-chunk `raw_text` / `contextual_prefix` / `final_content`.
- **Qdrant** holds only vectors + a *small* payload (`document_id, chunk_id, chunk_index, title, final_content`). Never move bulk raw text into Qdrant payloads. `document_id` is a keyword payload index used for filtered delete.

### The pipeline (`services/pipeline.py`)
Runs in the background via FastAPI `BackgroundTasks` (opens its own DB session, separate from the request session). Drives the document through the `DocumentStatus` enum: `uploaded → parsing → parsed → chunking → indexing → indexed` (or `failed` with `error_message`). The three stages:

- **A. Parsing (`parsing_service.py`)** — each PDF page rendered to PNG via `pdfplumber`, sent to the VLM (`ThreadPoolExecutor`, `VLM_MAX_CONCURRENCY`), with per-page retry (`tenacity`) and code-fence stripping. Empty VLM output falls back to the PDF text layer if enabled.
- **B. Chunking + Contextual (`chunking_service.py`)** — `SentenceSplitter` (llama-index) splits by `CHUNK_SIZE`/`CHUNK_OVERLAP`. For each chunk, the LLM generates a locating "contextual prefix" using the *full document* as a cacheable message prefix. `final_content = title + prefix + "\n\n" + raw_text` — this is what gets embedded. A single chunk's context failure is logged and skipped, not fatal.
- **C. Indexing (`qdrant_service.py` + `embedding_service.py`)** — batch-embed all `final_content`, upsert to Qdrant with `qdrant_point_id` (a UUID stored on the Chunk row).

Reprocess (`_reset_document`) wipes old pages/chunks + Qdrant points before re-running so the pipeline is idempotent.

### LLM boundary (`services/llm_client.py`)
The single choke point for all FPT calls: `chat` / `chat_stream` / `vision` / `embed`. All construct an `OpenAI` client pointed at `settings.fpt_base_url`. Errors wrap into `LLMError`; token usage (including cached tokens) is logged per call. Add new model interactions here rather than calling `openai` directly elsewhere.

### API (`routers/`, prefix `/api`)
- `documents.py` — upload (writes PDF to `DATA_DIR/uploads`, triggers pipeline), list (paginated), detail (pages + chunks), status (for polling), reprocess, delete (Qdrant points → PDF file → DB cascade).
- `playground.py` — `/api/playground/query`: embed question → Qdrant `top_k` search → build grounded prompt → LLM answer. `stream: true` returns SSE (`type: citations` first, then `type: token` deltas, then `[DONE]`).

### DB notes (`db.py`)
- SQLite uses `check_same_thread=False` (background threads share the engine) and a `connect` event turns on `PRAGMA foreign_keys=ON` so the `cascade="all, delete-orphan"` relationships (Document → Pages/Chunks) actually cascade.
- Schema is created with `Base.metadata.create_all` on startup (no migrations). Changing a model requires deleting the SQLite file or adding Alembic. In Docker the DB lives in the `backend_data` volume at `/data/rag.db`.

## Testing conventions
Tests (`backend/tests/`) are pure unit tests over `chunking_service` (`split_text`, `build_final_content`) — no network, no DB. Keep new tests offline; the FPT-dependent paths aren't covered by automated tests.

## Known v1 shortcuts (per README)
`BackgroundTasks` instead of Celery; `create_all` instead of Alembic; CORS `allow_origins=["*"]`; Vite dev server instead of a static nginx build. Don't treat these as bugs unless the task is specifically to harden them.
