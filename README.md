# RAG Platform (FastAPI + React + Qdrant + FPT AI Marketplace)

Nền tảng RAG greenfield: upload PDF → parse chất lượng cao bằng VLM → chunking +
**Contextual Retrieval** (Anthropic) → index vào Qdrant → hỏi–đáp ở Playground.

## Kiến trúc
- **Backend**: FastAPI + SQLAlchemy 2 + SQLite (metadata / parse pages / chunks).
- **Vector DB**: Qdrant — CHỈ giữ vector + payload nhỏ (`document_id, chunk_id, chunk_index, title, final_content`). Raw text nằm ở SQLite.
- **LLM/VLM/Embedding**: FPT AI Marketplace (OpenAI-compatible) qua thư viện `openai`.
- **Frontend**: React + Vite + TypeScript (3 trang: Upload, Documents, Playground).

```
backend/app
├─ config.py        # pydantic-settings đọc .env
├─ db.py            # engine/session/Base + create_all
├─ models/          # document, page, chunk (SQLAlchemy 2, cascade delete)
├─ schemas/         # Pydantic v2
├─ routers/         # documents.py, playground.py
└─ services/
   ├─ llm_client.py        # chat/chat_stream/vision/embed + wrapper prompt caching
   ├─ parsing_service.py   # pdfplumber → PNG → VLM → markdown
   ├─ chunking_service.py  # SentenceSplitter + câu định vị + final_content
   ├─ embedding_service.py # embed batch
   ├─ qdrant_service.py    # ensure/upsert/search/delete
   └─ pipeline.py          # A(parse) → B(chunk+context) → C(index)
```

## ⚠️ Cần cấu hình trước khi chạy
Sao chép `.env.example` → `.env` và điền:

| Biến | Ý nghĩa | Ghi chú |
|------|---------|---------|
| `FPT_API_KEY` | API key FPT AI Marketplace | Bắt buộc |
| `FPT_VLM_MODEL` | Model vision (GLM) đọc ảnh page | Lấy **đúng ID** trên [marketplace.fptcloud.com](https://marketplace.fptcloud.com); confirm biến thể vision |
| `FPT_CHAT_MODEL` | Model chat (contextual + QA) | vd `GLM-5.1` |
| `FPT_EMBED_MODEL` | Model embedding | Gợi ý tiếng Việt: `Vietnamese_Embedding`, `bge-m3`, `multilingual-e5-large` |
| `EMBED_DIM` | Số chiều vector | **Phải khớp** model embedding (vd bge-m3 = 1024) |
| `FPT_ENABLE_PROMPT_CACHE` | Bật cache_control | Để `false` — FPT chưa xác nhận hỗ trợ |

> Model ID và `EMBED_DIM` **không hardcode** trong code — luôn đọc từ `.env`.
> `EMBED_DIM` sai sẽ khiến Qdrant upsert lỗi.

## Chạy bằng Docker (khuyến nghị)
```bash
cp .env.example .env      # rồi điền FPT_API_KEY + model IDs
docker compose up --build
```
- Qdrant: http://localhost:6333/dashboard
- Backend (Swagger): http://localhost:8000/docs
- Frontend: http://localhost:5173

## Chạy local (không Docker)
```bash
# Qdrant
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload   # cần .env ở thư mục backend hoặc export biến

# Frontend
cd frontend && npm install && npm run dev
```

## Luồng end-to-end
1. **Upload** một PDF → pipeline chạy nền (`BackgroundTasks`):
   `uploaded → parsing → parsed → chunking → indexing → indexed`.
2. **Documents**: xem `parsed_text` từng page + danh sách chunks (`final_content` = title + câu định vị + chunk). Nút Reprocess / Xoá.
3. **Playground**: nhập câu hỏi → embed → Qdrant search top_k → LLM trả lời (stream) + hiển thị nguồn chunk.

## API chính (prefix `/api`)
| Method | Path | Mô tả |
|--------|------|------|
| POST | `/api/documents` | Upload PDF, trigger pipeline |
| GET | `/api/documents` | List (phân trang) |
| GET | `/api/documents/{id}` | Chi tiết + pages + chunks |
| GET | `/api/documents/{id}/status` | Poll trạng thái pipeline |
| POST | `/api/documents/{id}/reprocess` | Chạy lại pipeline |
| DELETE | `/api/documents/{id}` | Xoá document + pages + chunks + Qdrant points |
| POST | `/api/playground/query` | RAG query (`stream: true` → SSE) |

## Test
```bash
cd backend && pytest
```
Test cover: `split_text` (chunk_size/overlap/separator) và `build_final_content` (định dạng title + câu định vị + raw_text). Không gọi API ngoài.

## Hướng nâng cấp (v2)
- Thay `BackgroundTasks` bằng **Celery** để xử lý nền bền vững.
- Alembic migration thay `create_all`.
- Serve frontend build tĩnh qua nginx thay vì vite dev server.
