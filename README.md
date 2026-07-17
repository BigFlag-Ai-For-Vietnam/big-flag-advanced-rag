# RAG Platform (FastAPI + React + Qdrant + FPT AI Marketplace)

Nền tảng RAG greenfield: upload PDF → parse chất lượng cao bằng VLM → chunking +
**Contextual Retrieval** (Anthropic) → index vào Qdrant → hỏi–đáp ở Playground.

## Kiến trúc
Mô hình **ba kho lưu trữ**:
- **Backend**: FastAPI + SQLAlchemy 2 + SQLite (metadata / parse pages / chunks — toàn bộ raw text).
- **Vector DB**: Qdrant — CHỈ giữ vector + payload nhỏ (`document_id, chunk_id, chunk_index, title, final_content`). Raw text nằm ở SQLite.
- **Blob storage**: PDF gốc + ảnh page (PNG) đi qua `storage_service` — backend `local` (đĩa, mặc định) hoặc `s3` (RustFS / S3-compatible). Xem [Lưu trữ file](#lưu-trữ-file-storage).
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
   ├─ storage_service.py   # choke point blob I/O (PDF + ảnh page): backend local|s3
   └─ pipeline.py          # A(parse) → B(chunk+context) → C(index)
```

## Tech stack
Chỉ liệt kê framework / hệ thống cốt lõi; version pin trong `requirements.txt` và
`package.json`, model ID + `EMBED_DIM` đọc từ `.env` (không hardcode).

**Backend**

| Công nghệ | Vai trò |
|-----------|---------|
| FastAPI | Framework REST API |
| SQLAlchemy 2 + SQLite | ORM + kho quan hệ (toàn bộ raw text) |
| Pydantic 2 | Schema request/response + đọc cấu hình `.env` |
| Qdrant | Vector database (vector + payload nhỏ) |
| LlamaIndex | `SentenceSplitter` cho chunking |
| OpenAI SDK | Client cho mọi lời gọi FPT AI Marketplace |
| pdfplumber | Render page PDF + text-layer dự phòng |

**Frontend**

| Công nghệ | Vai trò |
|-----------|---------|
| React 18 | Giao diện (Upload / Documents / Playground) |
| Vite | Dev server + build/typecheck |
| TypeScript | Kiểu tĩnh |

**External / Infra**

| Công nghệ | Vai trò |
|-----------|---------|
| FPT AI Marketplace | Nhà cung cấp LLM/VLM/Embedding (OpenAI-compatible) |
| Docker Compose | Điều phối app + infra |
| MLflow | Theo dõi thí nghiệm (stack `infra/`) |
| RustFS | Object storage S3-compatible (artifact MLflow + blob app tuỳ chọn) |
| Postgres | Backend store của MLflow (stack `infra/`) |

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
| `STORAGE_BACKEND` | Nơi lưu blob PDF + ảnh page | `local` (mặc định) hoặc `s3` (RustFS). Xem [Lưu trữ file](#lưu-trữ-file-storage) |

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

## Lưu trữ file (storage)
PDF gốc và ảnh page (PNG render để gửi VLM) được lưu qua **`storage_service`** — một
choke point duy nhất, chọn backend bằng `STORAGE_BACKEND`:

- **`local`** (mặc định): ghi xuống đĩa dưới `DATA_DIR` (`uploads/{id}.pdf`,
  `images/{id}/page_*.png`). Trong Docker nằm ở named volume `backend_data`.
- **`s3`**: đẩy lên bucket S3 trên **RustFS** (hoặc bất kỳ endpoint S3-compatible). Bật bằng:

  ```env
  STORAGE_BACKEND=s3
  S3_ENDPOINT_URL=http://localhost:9000   # RustFS S3 API (infra); trong compose chung mạng: http://rustfs:9000
  S3_ACCESS_KEY=rustfsadmin
  S3_SECRET_KEY=rustfsadmin
  S3_BUCKET=rag-documents                 # tách khỏi bucket "mlflow" của infra; tự tạo nếu chưa có
  S3_REGION=us-east-1
  ```

`Document.file_path` và `Page.image_ref` lưu **storage key** (vd `uploads/{id}.pdf`),
không phải path tuyệt đối — `storage_service` phân giải theo backend. Cần `boto3` (đã có
trong `requirements.txt`) khi dùng `s3`.

> RustFS chạy trong stack `infra/` (mặc định tách mạng với app compose). Dùng `s3` cần cho
> backend truy cập được endpoint đó (chung Docker network hoặc endpoint ngoài).

## Infra stack (MLflow + RustFS + Postgres)
Stack quan sát/thí nghiệm **độc lập** với app, nằm ở `infra/` (compose riêng):

```bash
cd infra && cp .env.example .env && docker compose up --build
```

| Service        | URL                     | Ghi chú                          |
| -------------- | ----------------------- | -------------------------------- |
| MLflow UI      | http://localhost:5000   | tracking + artifact serving      |
| RustFS Console | http://localhost:9001   | login bằng RUSTFS_ACCESS/SECRET  |
| RustFS S3 API  | http://localhost:9000   | endpoint S3-compatible           |
| Postgres       | localhost:5432          | MLflow backend store (db `mlflow`) |

- **MLflow** dùng Postgres làm backend store và RustFS làm artifact store (`--serve-artifacts`).
- **RustFS** là object storage S3-compatible; ngoài MLflow, app có thể tái dùng cho blob tài
  liệu qua `STORAGE_BACKEND=s3` (bucket riêng `rag-documents`).
- Chi tiết đầy đủ: [`infra/README.md`](infra/README.md).

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
- Nối app compose với RustFS (chung network) để `STORAGE_BACKEND=s3` chạy liền mạch;
  hiện đã có storage layer (`storage_service`, `local|s3`) nhưng networking để tự cấu hình.
