# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A greenfield RAG platform: upload a PDF → parse with a VLM → chunk with **Contextual Retrieval** (Anthropic technique) → index into Qdrant → ask questions in a Playground. Retrieval is agentic: a LangGraph **Retrieval Engine** (`app/retrieval/`, running as its own `retrieval-mcp` service, called over MCP) does plan → gather → assess → loop → finalize, hybrid dense+BM25 per sub-goal. For `tuan_thu` (compliance) documents, ingestion also builds a **Neo4j knowledge graph** (LightRAG + ontology validation, `app/services/kg/`) in the background alongside Qdrant indexing; at query time the engine gathers graph facts (document relations, cross-document value bundles) as a *second, separate* evidence channel next to chunks, so the assess/answer step can reason about conflicts/supersession across documents — see "Graph boundary" below. All LLM/VLM/embedding calls go to **FPT AI Marketplace** (OpenAI-compatible API) via the `openai` library. Backend is FastAPI + SQLAlchemy 2 + SQLite; frontend is React + Vite + TypeScript.

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
| Neo4j | Knowledge graph (compliance documents/concepts/values) |
| LangGraph + MCP | Retrieval Engine (agentic plan/gather/assess loop), own `retrieval-mcp` service |
| LlamaIndex | `SentenceSplitter` chunking |
| LightRAG | Ontology-guided KG extraction (`app/services/kg/`, ingest-time only) |
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
| Neo4j | Runs in `infra/` stack; graph reads/writes are backend/retrieval-mcp responsibility |

## Commands

```bash
# Full stack (recommended) — needs .env with FPT_API_KEY + model IDs
make env   # creates .env + infra/.env from the examples
make up    # starts infra/ (Qdrant + Neo4j + MLflow + RustFS + Postgres) detached, then backend + frontend
# The app compose has NO qdrant/neo4j service: backend AND retrieval-mcp both join the infra
# stack's attachable `rag-infra` network and reach qdrant:6333 / neo4j:7687 / mlflow:5000 by
# service name, so the infra stack must be up first (make up handles the ordering).
# Qdrant dashboard: :6333/dashboard | Neo4j Browser: :7474 | App + Swagger: http(s)://localhost
# và /docs — nginx (infra/) là đường vào duy nhất trên 80/443, serve frontend + proxy /api;
# backend/frontend/retrieval-mcp không publish :8000/:5173 ra host (retrieval-mcp publishes
# :8100 for direct debugging) | MLflow: :5000

# Backend local
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
# Ingest-time KG build (LightRAG) needs the heavier deps — only when KG_ENABLE_BUILD=true:
cd backend && pip install -r requirements-kg.txt
cd backend && pytest                                              # offline unit tests

# Frontend local
cd frontend && npm install && npm run dev
cd frontend && npm run build   # tsc -b && vite build (also the typecheck)

# Infra stack (Qdrant + Neo4j + MLflow + RustFS + Postgres) — separate compose in infra/
cd infra && cp .env.example .env && docker compose up --build   # or: make infra-up
```

## Project structure

```
backend/app/
  config.py            pydantic-settings — all model IDs + EMBED_DIM from .env (never hardcoded)
  db.py                SQLite engine, create_all on startup (no migrations)
  main.py              FastAPI app
  models/              SQLAlchemy: document (+ DocumentStatus, GraphStatus), page, chunk
  schemas/             Pydantic request/response (playground.py: Citation, GraphFact, ...)
  routers/             /api endpoints: documents, playground
  retrieval/           LangGraph Retrieval Engine — runs as its OWN service (retrieval-mcp),
                       called over MCP by routers/playground.py (app.retrieval.mcp.client)
    engine.py          outer graph: normalize→rewrite→plan→gather→assess→loop→finalize;
                       gather queries BOTH chunks (_search) and graph facts (_graph_search)
    nodes.py           deterministic + LLM steps (assess renders both evidence channels)
    tools.py           query_vector_store, query_catalog, query_graph_knowledge
    mcp/               server.py (FastMCP, service entrypoint) + client.py (used by backend)
  services/
    pipeline.py        background orchestrator (uploaded → parsed → chunking → indexing → indexed);
                       also triggers KG build (kg.build_service) in a separate background thread
                       for tuan_thu documents when KG_ENABLE_BUILD=true — does NOT block indexing
    parsing_service.py PDF page → PNG → VLM
    chunking_service.py SentenceSplitter + LLM contextual prefix
    embedding_service.py + qdrant_service.py  embed + upsert/search
    graph_service.py   query-time Neo4j reads (citation_neighbors, concept_matches) — light,
                       safe in both `backend` and `retrieval-mcp` images, see "Graph boundary"
    kg/                ingest-time KG build (LightRAG + ontology), heavy deps (requirements-kg.txt);
                       build_service.py orchestrates ainsert → entity resolution → citation
                       extraction → concept linking; NEVER imported from app/retrieval/*
    llm_client.py      single choke point for all FPT calls (chat/stream/vision/embed)
    storage_service.py single choke point for all blob I/O (PDF + page PNGs); local|s3 backend
frontend/src/
  api/client.ts        backend client
  pages/               Upload, Documents, Playground
infra/                 Qdrant + Neo4j + MLflow + RustFS + Postgres compose (network `rag-infra`,
                       attachable). MLflow uses RustFS for artifacts; the app can optionally
                       reuse RustFS for document blobs (STORAGE_BACKEND=s3).
```

## Load-bearing config (read before touching model calls)

Model IDs and vector dimension come from `.env` via `config.py`. Two settings break the pipeline silently if wrong:

- **`EMBED_DIM`** must match the embedding model's output dimension, or Qdrant upsert fails (collection is created once at this size; changing it later means recreating the collection).
- **`FPT_VLM_MODEL`** must be a genuine **vision** model (accepts `image_url`); a chat-only model silently returns empty text. `PARSE_TEXT_FALLBACK=true` falls back to the PDF text layer when the VLM returns empty.
- **`FPT_ENABLE_PROMPT_CACHE`** — keep `false`; FPT hasn't confirmed `cache_control` support.
- **`STORAGE_BACKEND`** — `local` (default; blobs on disk under `DATA_DIR`) or `s3` (RustFS / any S3-compatible endpoint). `s3` needs `S3_ENDPOINT_URL` + keys + `S3_BUCKET` reachable — RustFS runs in `infra/` on `:9000`. The dockerized backend already joins the infra stack's `rag-infra` network, so use `http://rustfs:9000` there (`http://localhost:9000` for a host-local backend). The app bucket (`rag-documents`) is deliberately separate from MLflow's `mlflow` bucket.
- **`KG_ENABLE_BUILD`** / **`RETRIEVAL_ENABLE_GRAPH`** — two independent flags, both default `false`. `KG_ENABLE_BUILD` turns on ingest-time graph building (only for `KG_CATEGORIES`, default `["tuan_thu"]`); `RETRIEVAL_ENABLE_GRAPH` turns on query-time graph reads in the Retrieval Engine. Turn on build first, verify `graph_service.stats()` isn't empty, only then flip the query-time flag — otherwise the engine "reasons" over an empty graph, which is worse than not asking at all.
- **`NEO4J_URI`/`NEO4J_USERNAME`/`NEO4J_PASSWORD`** must match between the root `.env` (used by `backend`/`retrieval-mcp`) and `infra/.env` (used by the actual `neo4j` container) — there's no cross-check, a mismatch just fails silently into `graph_service`'s degrade-to-empty behavior.

## Key invariants

- **Three-store design**: SQLite holds all raw text (documents, per-page/-chunk text). Qdrant holds only vectors + a *small* payload (`document_id, chunk_id, chunk_index, title, final_content`) — never move bulk raw text into Qdrant; `document_id` is a keyword index for filtered delete. Blobs (source PDF + rendered page PNGs) live in **object/FS storage** via `storage_service`, keyed as `uploads/{id}.pdf` and `images/{id}/page_*.png`; `Document.file_path` / `Page.image_ref` store these **storage keys**, not absolute paths.
- **Pipeline** runs in the background via `BackgroundTasks` (own DB session); reprocess wipes old pages/chunks + Qdrant points first, so it's idempotent.
- **LLM boundary**: add new model interactions in `llm_client.py`, not by calling `openai` directly elsewhere. `app/services/kg/llm_adapter.py` is a deliberate, documented exception (LightRAG drives its own concurrency/retry against FPT — still reads model IDs/keys from `settings`, never hardcodes).
- **Storage boundary**: add new blob reads/writes/deletes in `storage_service.py`, not by calling `boto3`/`open()` directly elsewhere. Keeps `local`/`s3` swappable and offline tests boto3-free.
- **Graph boundary**: query-time graph reads go ONLY through `graph_service.py` (thin, `neo4j` driver only — safe in both the `backend` and `retrieval-mcp` images). Ingest-time graph building (LightRAG, ontology validation, entity resolution — heavy deps) lives ONLY in `app/services/kg/`, and is imported ONLY from `pipeline.py` (lazily, inside the `KG_ENABLE_BUILD` branch) — never from `app/retrieval/*`. This keeps `retrieval-mcp` free of `lightrag-hku`. Citations (`Citation`, exact chunk quotes) and graph facts (`GraphFact`, relations the LLM reasons over) are always kept in separate response fields, never merged into one list — see `playground.py::_build_messages`.
- **Tests** (`backend/tests/`) are pure offline unit tests over `chunking_service`/`graph_service`/`citation_extractor`/etc; keep new tests offline (FPT-dependent and Neo4j/LightRAG-orchestration paths aren't covered — verify those by running against a real stack).

## Known v1 shortcuts (per README)
`BackgroundTasks` instead of Celery; `create_all` instead of Alembic; CORS `allow_origins=["*"]`; Vite dev server instead of a static nginx build. Graph-build also runs as a bare `ThreadPoolExecutor` outside `run_pipeline()`'s lifecycle: a process restart mid-build leaves `Document.graph_status` stuck at `"building"` forever for that document (no crash recovery — reprocess the document to retry). Don't treat these as bugs unless the task is specifically to harden them.
