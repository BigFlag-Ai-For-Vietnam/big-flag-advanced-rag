# BigRAG — Advanced RAG for Complex Banking Document Intelligence

> **Hiểu đúng quy định — Theo đúng liên kết — Trả lời có căn cứ.**
> *From document retrieval to connected, verifiable banking intelligence.*

BigRAG là một nền tảng **Advanced RAG** cho bài toán hỏi–đáp trên **văn bản tuân thủ ngân hàng**
(banking compliance): upload PDF → parse bằng VLM → chunking với **Contextual Retrieval**
(Anthropic) → index vào Qdrant, đồng thời dựng **Knowledge Graph** (Neo4j) cho nhóm văn bản tuân
thủ. Ở tầng truy vấn, một **agentic Retrieval Engine** (LangGraph, chạy như service `retrieval-mcp`
riêng, gọi qua **MCP**) thực hiện vòng lặp có kiểm soát `plan → gather → assess → loop → finalize`,
gom **hai kênh bằng chứng** song song — *chunk trích dẫn nguyên văn* và *graph facts* — rồi mới
tổng hợp câu trả lời có nguồn dẫn.

Mọi lời gọi LLM / VLM / Embedding đi qua **FPT AI Marketplace** (OpenAI-compatible). Backend là
FastAPI + SQLAlchemy 2 + SQLite; frontend là React + Vite + TypeScript.

> Comment / docstring / prompt / văn bản người dùng đều bằng **tiếng Việt** theo thiết kế; thuật
> ngữ kỹ thuật giữ nguyên tiếng Anh.

---

## 1. Bài toán nghiệp vụ (Business goal)

**Bối cảnh.** Kho tri thức ngân hàng ngày càng phức tạp: quy định nội bộ + văn bản Nhà nước
(Nghị định / Chính phủ, Thông tư / NHNN), liên tục được thêm mới và cập nhật từ nhiều bộ phận.
Thông tin cho **một** câu hỏi thường phân tán trong **nhiều văn bản và nhiều phiên bản**, dễ gây
xung đột. **Người dùng** — nhân viên compliance / vận hành — cần tìm ra **quy định đang áp dụng**,
không chỉ tìm ra một tài liệu liên quan.

**Luận điểm cốt lõi:** *"Tìm thấy tài liệu chưa đồng nghĩa với tìm được quy định đúng."*

**Ba pain point** mà BigRAG nhắm tới (minh hoạ bằng bộ dữ liệu mô phỏng DongDoBank — xem [§10](#10-dataset-mẫu--giới-hạn-đã-biết-honest-limitations)):

| # | Pain point | Ví dụ mô phỏng |
|---|------------|----------------|
| **P1** | **Thay đổi theo thời gian** — văn bản bị sửa đổi / thay thế toàn bộ hoặc **một phần** (partial supersession). | `QĐ 342/2024` thay thế `QĐ 215/2022` về ATTT, nhưng **Phụ lục 02** (danh mục hệ thống trọng yếu) của bản cũ **vẫn còn hiệu lực**. |
| **P2** | **Quy định chồng lấn / conflict** — cùng chủ thể, khác giá trị / phạm vi / đối tượng. | Độ dài mật khẩu: `QĐ 342` yêu cầu **12 ký tự**, `QĐ 401` nêu **8 ký tự** — nhưng `QĐ 401` quy định khi khác biệt thì **ưu tiên `QĐ 342`** → kết luận đúng là **12**. Kèm **bẫy ngược**: lưu trữ KYC 10 năm vs DLCN 5 năm **KHÔNG** phải xung đột (carve-out pháp luật chuyên ngành). |
| **P3** | **Quan hệ đa văn bản** — câu trả lời nằm ở cuối một **chuỗi dẫn chiếu 2–3 bước**. | `QĐ 342/2024` *tuân thủ* `TT 09/2024/TT-NHNN` *căn cứ* `NĐ 88/2024/NĐ-CP`. |

**Vì sao RAG truyền thống chưa đủ.** RAG top-k tìm các đoạn *giống* câu hỏi nhưng: (1) truy xuất
chunk **rời rạc**, không theo quan hệ giữa văn bản; (2) top-k có thể **bỏ sót một khía cạnh** khi
câu hỏi trải nhiều facet; (3) có nguy cơ dùng nội dung **đã hết hiệu lực**; (4) LLM vẫn **tổng hợp
câu trả lời tự tin** dù bằng chứng chưa đầy đủ — loại lỗi nguy hiểm nhất với nghiệp vụ tuân thủ.

> Giá trị của BigRAG được **chứng minh bằng Evaluation ([§7](#7-lớp-observe--evaluation)) và
> Showcase Demo ([§8](#8-showcase-demo-advanced-vs-raw))**, không phải bằng claim rời rạc.

---

## 2. Kiến trúc tổng thể — ba lớp

```text
┌─ INGESTION ──────────────────────────────────────────────────────────────┐
│ PDF → VLM parse → Contextual Chunking → Embed                             │
│   ├─→ Qdrant Dense Index   ┐                                              │
│   ├─→ BM25 (SQLite chunks) ├─ Search Index  (chunk-RAG sẵn sàng phục vụ)  │
│   ├─→ Catalog (facet tree) ┘                                              │
│   └─→ (chạy nền, chỉ van_ban_tuan_thu) LightRAG + Ontology → Neo4j KG     │
└───────────────────────────────────────────────────────────────────────────┘
        │  Retrieval đọc Index · Catalog · Graph
        ▼
┌─ RETRIEVAL ──────────────────────────────────────────────────────────────┐
│ Retrieval Engine (LangGraph, service retrieval-mcp qua MCP):             │
│   normalize → rewrite → plan → gather → assess → (loop | finalize)        │
│   gather: Hybrid (dense+BM25) mỗi sub-goal  +  Graph facts (kênh 2)       │
│   → Sufficiency check → Answer + Citations + GraphFacts                   │
└───────────────────────────────────────────────────────────────────────────┘
        │  Answer + traces
        ▼
┌─ OBSERVE & EVALUATION ───────────────────────────────────────────────────┐
│ MLflow tracing · Silver/Golden Dataset (RAGAS) · agentic-vs-raw judge     │
└───────────────────────────────────────────────────────────────────────────┘
```

**Hai kênh bằng chứng, tách biệt theo thiết kế.** BigRAG luôn giữ **`Citation`** (đoạn chunk trích
dẫn **nguyên văn**) và **`GraphFact`** (quan hệ / entity **suy luận** từ graph) ở **hai trường
riêng**, không gộp:

> *Raw evidence provides precision. Graph context provides completeness.*

**Mô hình ba kho lưu trữ (three-store):**
- **SQLite** giữ **toàn bộ raw text** (documents, per-page text, chunks).
- **Qdrant** chỉ giữ **vector + payload nhỏ** (`document_id, chunk_id, chunk_index, title,
  final_content`) — không bao giờ đẩy bulk raw text vào Qdrant.
- **Blob storage** (PDF gốc + ảnh page PNG) qua `storage_service` — backend `local` (đĩa, mặc
  định) hoặc `s3` (RustFS / S3-compatible). `Document.file_path` / `Page.image_ref` lưu **storage
  key**, không phải path tuyệt đối.

---

## 3. Lớp Ingestion

Pipeline chạy nền (`BackgroundTasks`, `app/services/pipeline.py`) với vòng đời trạng thái:

```text
uploaded → parsing → parsed → chunking → indexing → indexed
```

1. **Parse (`parsing_service.py`)** — render từng trang PDF → PNG → gửi **VLM** đọc thành markdown.
   `PARSE_TEXT_FALLBACK=true` dùng text-layer PDF (pdfplumber) làm dự phòng khi VLM trả rỗng.
2. **Contextual Chunking (`chunking_service.py`)** — `SentenceSplitter` (LlamaIndex) giữ ngữ cảnh
   lân cận bằng overlap; LLM thêm **1–2 câu định vị** để mỗi chunk **tự đứng độc lập** vẫn đủ nghĩa.
   `final_content` = title + câu định vị + raw text.
3. **Indexing (`embedding_service.py` + `qdrant_service.py`)** — embed batch → upsert Qdrant kèm cờ
   `is_active` (phục vụ versioning). Song song, **Catalog** theo facet được dựng để planner biết một
   tài liệu có bao nhiêu mục (phục vụ câu hỏi liệt kê / tổng hợp).

**Một đầu vào, hai đầu ra.** Sau bước contextual, ngoài Search Index (dense + BM25 + catalog),
với document thuộc `KG_CATEGORIES` (mặc định `["van_ban_tuan_thu"]`) pipeline **fork một
background KG build** trong lúc chunking — **không chặn** Qdrant indexing. Trạng thái graph được
theo dõi **riêng** bằng `GraphStatus`:

```text
not_built → building → ready | failed
```

`GraphStatus` **tách rời** `DocumentStatus`: `indexed` là tín hiệu duy nhất cho "chunk-RAG dùng
được", không bao giờ chờ graph. Nếu process restart giữa chừng, `recover_interrupted_graph_builds()`
(chạy lúc startup) chuyển các row kẹt `building` sang `failed` (reprocess để thử lại).

---

## 4. Knowledge Graph (compliance)

Xây **chỉ cho `van_ban_tuan_thu`** — nơi suy luận vốn **cross-document**. Graph vật chất hoá những
thứ vector search đơn thuần không nắm được (`app/services/kg/build_service.py`):

**Ontology 3 entity** (`VanBan` — văn bản · `KhaiNiem` — khái niệm · `GiaTriQuyDinh` — giá trị quy
định) và **4 loại cạnh dẫn chiếu** giữa văn bản:

| Edge | Ý nghĩa |
|------|---------|
| `CAN_CU` | căn cứ pháp lý |
| `THAY_THE` | thay thế (mang thuộc tính `partial` + `giu_hieu_luc` cho supersession một phần) |
| `THAM_CHIEU` | tham chiếu |
| `UU_TIEN_HON` | ưu tiên hơn khi xung đột |

**Graph cho phép:**
- **Supersession / versioning** — biết `QĐ 342` thay thế `QĐ 215` nhưng Phụ lục 02 còn hiệu lực.
- **Value bundle** — một `KhaiNiem` (vd "Mật khẩu", "Thời hạn lưu trữ") nối tới **mọi**
  `GiaTriQuyDinh` cụ thể trên **tất cả** văn bản, mỗi giá trị gắn văn bản nguồn. Trả lời được
  "tổ chức yêu cầu gì cho X, theo văn bản nào, các nguồn có mâu thuẫn không?".
- **Citation chain** — truy vết chuỗi dẫn chiếu nhiều tầng cho P3.

> **Thiết kế có chủ đích:** graph **KHÔNG** vật chất hoá cạnh "xung đột". Thay vào đó
> `concept_matches` phơi bày **mọi giá trị khác nhau** của cùng một khái niệm để **engine tự suy
> luận** conflict / precedence ở tầng truy vấn — tránh đóng cứng phán quyết vào lúc build.

**Build flow (ingest-time, deps nặng — `requirements-kg.txt`):** LightRAG `ainsert` (trích entity /
relation tự do, có `entity_types_guidance` từ ontology) → **entity resolution** VanBan theo *số hiệu*
→ **citation extraction** (regex + phân loại verb-context, viết 4 cạnh trên) → **concept/value
resolution & linking** (khử trùng theo diacritics rồi fuzzy có LLM xác nhận). **Ontology validation**
chạy **ngay trong write path** (`OntologyValidatingGraphStorage`): entity / triple ngoài ontology bị
loại **trước khi** ghi vào Neo4j.

**Query-time reads (`app/services/graph_service.py`)** — module nhẹ (chỉ driver `neo4j`, an toàn
trong cả image `backend` lẫn `retrieval-mcp`, **không** import `app/services/kg/*`):
`citation_neighbors(titles, hops)`, `concept_matches(query, top_k)`, `stats()`. **Degrade an toàn:**
mọi hàm guard `is_configured()` và try/except → trả `[]` nếu graph trống / Neo4j lỗi; graph là
**bổ trợ**, không bao giờ làm hỏng query chính.

**Hai cờ độc lập — thứ tự rollout an toàn:**
1. Bật `KG_ENABLE_BUILD=true` → ingest để graph được dựng.
2. Kiểm tra `graph_service.stats()` **không rỗng**.
3. Chỉ khi đó mới bật `RETRIEVAL_ENABLE_GRAPH=true` (query-time reads) — tránh cửa sổ "engine suy
   luận trên graph rỗng", còn tệ hơn không hỏi graph. Cả hai mặc định **`false`** (feature dark by
   default).

---

## 5. Lớp Retrieval — agentic engine

`app/retrieval/engine.py` là một **LangGraph** kiểu **Planner–Executor–Sufficiency-checker** có
kiểm soát (chủ đích **không** phải free-form ReAct agent — nghiệp vụ compliance cần bảo đảm
completeness). Sơ đồ:

```text
START → normalize → rewrite → plan → gather → assess ─┬─(all satisfied | hops≥max)→ finalize → END
                                        ▲             │
                                        └──── loop ───┘  (broaden query bằng note từ assess)
```

- **normalize** — dọn whitespace (deterministic).
- **rewrite** — 1 LLM call làm rõ / mở rộng câu hỏi cho semantic search (lỗi → fallback, không fatal).
- **plan** — tách câu hỏi thành **sub-goal** (nguyên tắc *một entity × một aspect = một sub-goal*),
  dùng catalog outline để biết số mục cần phủ. Chặn `RETRIEVAL_PLAN_MAX_SUBGOALS` (mặc định 6).
- **gather** — với mỗi sub-goal **chưa thoả**: (a) **Hybrid retrieval** — dense (Qdrant) fuse với
  **BM25** (corpus dựng in-memory từ chunks SQLite) theo `alpha·dense + (1-alpha)·bm25`; (b) nếu
  bật, **graph facts** (`citation_neighbors` + `concept_matches`). Bằng chứng ttrack **theo từng
  sub-goal** nên không facet nào bị "đói" vì một global top-k. Các hop sau **mở rộng query** bằng
  `note` từ assess (nêu tên văn bản / khía cạnh còn thiếu).
- **assess** — 1 LLM-judge coverage mỗi sub-goal. Thiên về **dừng** khi đủ, **trừ** khi graph cho
  thấy quan hệ `THAY_THE` / `UU_TIEN_HON` trỏ tới văn bản **chưa có** trong text evidence → **buộc
  chưa thoả** (trả lời từ điều khoản đã bị thay thế là sai). Lỗi LLM → fallback theo điểm số
  (`RETRIEVAL_COVERAGE_MIN_SCORE`, mặc định 0.35).
- **loop / finalize** — dừng khi **tất cả sub-goal thoả** HOẶC `hops ≥ RETRIEVAL_MAX_HOPS`
  (mặc định 3). Khi hết budget mà vẫn thiếu, phần thiếu **được đánh dấu** để model **không tự suy
  diễn**. Finalize gom Citation (dedup theo `chunk_id`) và GraphFact (dedup theo `fact_id`) trên
  **hai kênh riêng**, kèm **coverage** từng sub-goal.

**MCP boundary.** Engine chạy như **service `retrieval-mcp`** riêng (FastMCP, đúng **một** tool
`retrieve(question, top_k)`, cổng **8100**, `app/retrieval/mcp/server.py`). Ngay cả backend cũng gọi
qua **MCP client** (`app/retrieval/mcp/client.py`), **không** import engine trực tiếp — giữ image
`retrieval-mcp` sạch và tách deps. Progress được stream ra SSE cho UI debug. Nếu MCP down, playground
**fallback** về dense Qdrant search (`_simple_retrieve`) và báo warning.

---

## 6. Tech stack

**Backend**

| Tech | Vai trò |
|------|---------|
| FastAPI | REST API framework |
| SQLAlchemy 2 + SQLite | ORM + kho quan hệ (toàn bộ raw text) |
| Pydantic 2 | Schema request/response + đọc `.env` |
| Qdrant | Vector database (vector + payload nhỏ) |
| Neo4j | Knowledge Graph (văn bản / khái niệm / giá trị) |
| LangGraph + MCP | Retrieval Engine agentic, service `retrieval-mcp` riêng |
| LlamaIndex | `SentenceSplitter` cho chunking |
| LightRAG | Ontology-guided KG extraction (ingest-time, `app/services/kg/`) |
| OpenAI SDK | Client cho mọi lời gọi FPT AI Marketplace |
| pdfplumber | Render page PDF + text-layer dự phòng |

**Frontend**

| Tech | Vai trò |
|------|---------|
| React 18 | UI (Upload / Documents / Playground / Showcase) |
| Vite | Dev server + build/typecheck |
| TypeScript | Kiểu tĩnh |

**External / Infra**

| Tech | Vai trò |
|------|---------|
| FPT AI Marketplace | Nhà cung cấp LLM / VLM / Embedding (OpenAI-compatible) |
| Docker Compose | Điều phối app + infra |
| MLflow | Tracing + experiment tracking (stack `infra/`) |
| RustFS | Object storage S3-compatible (artifact MLflow + blob app tuỳ chọn) |
| Postgres | Backend store của MLflow (stack `infra/`) |

> Model ID + `EMBED_DIM` đọc từ `.env` (không hardcode); version pin trong `requirements.txt` /
> `package.json`.

---

## 7. Lớp Observe & Evaluation

**Tracing.** `TRACING_ENABLED=true` ghi span MLflow cho parsing / embedding / playground vào
experiment riêng (best-effort — tự tắt nếu MLflow không kết nối, không chặn request).

**Eval harness (`backend/eval/`, RAGAS + MLflow — chi tiết ở [`backend/eval/README.md`](backend/eval/README.md)).**
CLI hai lệnh: `python -m eval dataset generate …` (sinh testset) và `python -m eval judge …`
(chấm điểm). Đặc điểm phương pháp:

- **5 metric RAGAS**: `Faithfulness`, `AnswerRelevancy`, `ContextPrecision`, `ContextRecall`,
  `FactualCorrectness`.
- **Silver → Golden dataset**: LLM sinh câu hỏi tiếng Việt single-hop + multi-hop từ contextual
  chunks (phân bổ 0.5 / 0.25 / 0.25), persona-based; SME có thể review-queue → promote thành
  `golden-<name>`.
- **De-referenced query generation**: prompt sinh câu hỏi **cấm nêu số hiệu văn bản / Điều / Khoản /
  nhãn phiên bản** — người hỏi chỉ hỏi theo nội dung / tình huống (ngưỡng, thời hạn, được / không
  được). Câu trả lời vẫn phải bám context → **retrieval không thể "ăn gian"** nhờ ID trong câu hỏi.
- **So sánh `agentic` vs `trivial`**: technique registry map tên → `(question, top_k) → (response,
  contexts)`. `trivial` = dense Qdrant + `qa_service.answer` (baseline). `agentic` = **đúng flow
  production** (Retrieval Engine qua MCP, cùng SYSTEM_PROMPT với router). Run được tag `technique=…`
  để so combo dataset × technique.
- **Hardened judge**: luôn truyền tường minh judge LLM + embeddings (chặn RAGAS lặng lẽ fallback về
  `gpt-4o-mini`); tắt thinking của GLM (`enable_thinking=false`) để không trả content rỗng; nâng
  `max_tokens` tránh verdict bị cắt.

> **Giới hạn đã biết (nêu để trung thực):** trong tích hợp MLflow + RAGAS native, `retrieved_contexts`
> và `reference_contexts` cùng rút từ **một** span RETRIEVER → `ContextPrecision` / `ContextRecall`
> **tự tham chiếu**. Chỉ `Faithfulness`, `AnswerRelevancy`, và `FactualCorrectness` (dùng `reference`)
> là hoàn toàn đáng tin trong đường này.

---

## 8. Showcase Demo (Advanced vs Raw)

`POST /api/showcase/compare` (`app/routers/showcase.py`) chạy **song song** hai pipeline trên cùng
câu hỏi qua một SSE stream, mỗi event mang trường `pipeline` ("advanced" / "raw") để hai cột cập
nhật độc lập; lỗi một bên **không** giết bên kia. **Advanced không bao giờ lặng lẽ fallback về raw**
(sẽ làm hỏng phép so sánh).

- **Raw** (`_run_raw`): embed → Qdrant dense top-k → stream answer; trace = [embedding, top-k,
  hit_count].
- **Advanced** (`_run_advanced`): gọi Retrieval Engine (MCP) với live progress; phát
  `pipeline_context` gồm **citations, graph_facts, catalogs, normalized/rewritten question,
  tool_calls trace, subgoals (coverage)** rồi stream answer.

Frontend `frontend/src/pages/Showcase.tsx` render hai cột **"Advanced RAG" vs "Raw Vector RAG"**,
mỗi cột có pipeline trace, coverage panel, citation list, graph evidence và hàng latency
**Retrieve / First token / Total**.

**Ba case demo** ánh xạ trực tiếp ba pain point (ảnh: [`demo/`](demo/)):

| Demo | Case | Advanced | Raw (đối chứng) |
|------|------|----------|-----------------|
| **1 — Time-aware** (P1) | "Thời gian khoá phiên làm việc?" — 1 khái niệm trong 5 nguồn, 4 trạng thái hiệu lực | Phân định cả 5 trạng thái (hiện hành 15'/30', dự thảo, bị thay thế, đề xuất chưa duyệt) | Chỉ thấy 3/5 nguồn — đúng giá trị nhưng **không phân định vòng đời** |
| **2 — Multi-facet** (P2) | 1 câu hỏi 5 khía cạnh trên ≥6 văn bản | Phủ **5/5** kèm carve-out (KYC 10 năm; 04 giờ báo NHNN vs 72 giờ thông báo chủ thể) | **3/5**, trả **sai** ("05 năm", "72 giờ") **một cách tự tin, có trích dẫn** |
| **3 — Cross-doc chain** (P3) | Core Banking RTO/RPO + "căn cứ nào là trọng yếu?" | Truy vết `QĐ 356 → QĐ 173/2023 → Phụ lục 02 QĐ 215/2022`, đối chiếu `TT 09` | Lấy được số RTO nhưng **đứt chuỗi tại QĐ 173** |

---

## 9. Chạy & cấu hình

### 9.1 Cấu hình `.env` (đọc trước khi chạy)

Sao chép `.env.example` → `.env`. Các biến **load-bearing** (sai là hỏng pipeline một cách âm thầm):

| Biến | Ý nghĩa | Ghi chú |
|------|---------|---------|
| `FPT_API_KEY` | API key FPT AI Marketplace | **Bắt buộc** |
| `FPT_VLM_MODEL` | Model **vision** đọc ảnh page | Phải là model vision thật (nhận `image_url`); chat-only → trả rỗng |
| `FPT_CHAT_MODEL` | Model chat (contextual + QA) | vd `GLM-5.x` |
| `FPT_EMBED_MODEL` | Model embedding | Tiếng Việt: `Vietnamese_Embedding`, `bge-m3`, `multilingual-e5-large` |
| `EMBED_DIM` | Số chiều vector | **Phải khớp** model embedding (bge-m3 = 1024); sai → Qdrant upsert lỗi |
| `FPT_DISABLE_THINKING` | Tắt thinking của GLM | Để `true` cho RAG (thinking ngốn max_tokens → content rỗng) |
| `FPT_ENABLE_PROMPT_CACHE` | Đính `cache_control` thủ công | Để `false` — FPT chưa xác nhận hỗ trợ |
| `STORAGE_BACKEND` | Nơi lưu blob | `local` (mặc định) hoặc `s3` (RustFS) |
| `KG_ENABLE_BUILD` | Bật KG build (ingest-time) | Mặc định `false`; chỉ áp dụng cho `KG_CATEGORIES` |
| `RETRIEVAL_ENABLE_GRAPH` | Bật graph reads (query-time) | Mặc định `false`; **bật SAU** khi graph đã có dữ liệu ([§4](#4-knowledge-graph-compliance)) |
| `RETRIEVAL_ENABLE_HYBRID` | Dense + BM25 fusion | Mặc định `true` (`RETRIEVAL_HYBRID_ALPHA=0.5`) |
| `RETRIEVAL_MAX_HOPS` | Budget vòng gather→assess | Mặc định 3 |
| `NEO4J_URI` / `_USERNAME` / `_PASSWORD` | Kết nối Neo4j | **Phải khớp** `infra/.env`; lệch → degrade âm thầm về graph rỗng |

### 9.2 Chạy bằng Docker (khuyến nghị)

```bash
make env    # tạo .env + infra/.env từ .env.example — rồi điền FPT_API_KEY + model IDs
make up     # up infra (Qdrant + Neo4j + MLflow + RustFS + Postgres) detached, rồi app stack
```

`make up` up **infra trước** (app nối vào network `rag-infra` để gọi service theo tên), rồi build
`backend` + `retrieval-mcp` + `frontend`. URL:

| Service | URL |
|---------|-----|
| Frontend (Vite) | http://localhost:5173 |
| Backend + Swagger | http://localhost:8000 · http://localhost:8000/docs |
| retrieval-mcp (debug) | http://localhost:8100 |
| Qdrant dashboard | http://localhost:6333/dashboard |
| Neo4j Browser | http://localhost:7474 |
| MLflow | http://localhost:5000 |

> Bản production (`docker-compose.prod.yml` + nginx trong `infra/`) đặt nginx làm **đường vào duy
> nhất** trên 80/443 (serve frontend + proxy `/api`); backend / frontend không publish trực tiếp.

### 9.3 Chạy local (không Docker)

```bash
# 1) Infra (Qdrant + Neo4j + MLflow + RustFS + Postgres)
cd infra && cp .env.example .env && docker compose up --build   # hoặc: make infra-up

# 2) Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload
# KG build (LightRAG) cần deps nặng — chỉ khi KG_ENABLE_BUILD=true:
cd backend && pip install -r requirements-kg.txt

# 3) retrieval-mcp (Retrieval Engine, cổng 8100)
cd backend && python -m app.retrieval.mcp.server

# 4) Frontend
cd frontend && npm install && npm run dev
```

---

## 10. Luồng end-to-end & API

**Luồng:**
1. **Upload** PDF → pipeline nền: `uploaded → parsing → parsed → chunking → indexing → indexed`
   (KG build fork nền cho `van_ban_tuan_thu`).
2. **Documents** — xem `parsed_text` từng page + chunks (`final_content`), trạng thái graph; nút
   Reprocess / Xoá.
3. **Playground** — hỏi → Retrieval Engine (agentic, qua MCP) → answer stream + citations +
   graph facts + coverage.
4. **Showcase** — chạy Advanced vs Raw cạnh nhau, so trace / coverage / nguồn / latency ([§8](#8-showcase-demo-advanced-vs-raw)).

**API chính (prefix `/api`):**

| Method | Path | Mô tả |
|--------|------|------|
| POST | `/api/documents` | Upload PDF, trigger pipeline |
| GET | `/api/documents` | List (phân trang) |
| GET | `/api/documents/{id}` | Chi tiết + pages + chunks |
| GET | `/api/documents/{id}/status` | Poll trạng thái pipeline (+ graph_status) |
| POST | `/api/documents/{id}/reprocess` | Chạy lại pipeline (idempotent) |
| DELETE | `/api/documents/{id}` | Xoá document + pages + chunks + Qdrant points (+ graph) |
| POST | `/api/playground/query` | RAG query (`stream: true` → SSE) |
| POST | `/api/playground/mcp-retrieve/stream` | Debug Retrieval Engine qua MCP, progress SSE theo bước |
| POST | `/api/showcase/compare` | SSE so sánh Advanced RAG vs Raw Vector RAG trên cùng input |

---

## 11. Test

```bash
cd backend && pytest
```

Test là **unit test offline thuần** trên `chunking_service` / `graph_service` /
`citation_extractor`… — **không** gọi API ngoài. Các đường phụ thuộc FPT và orchestration
Neo4j / LightRAG **không** được cover ở đây; verify chúng bằng cách chạy trên stack thật.

---

## 12. Dataset mẫu & giới hạn đã biết (honest limitations)

**Dataset mẫu** — [`sample_compliance_corpus/`](sample_compliance_corpus/): **51 PDF hư cấu** mô
phỏng ngân hàng "DongDoBank (DDB)" (~500–1.000 chunks). Docs 01–10 là bộ gốc; 11–51 là bộ mở rộng
tăng *retrieval pressure* (chuỗi phiên bản, scope variant, văn bản nhiễu: dự thảo / biên bản / FAQ /
thông báo tạm). 4 văn bản Nhà nước (NĐ 88, TT 09, TT 04, TT 20) + Quyết định nội bộ DDB. Đáp án ở
`GROUND_TRUTH.md`.

**Cần nêu rõ (không overclaim):**
- Bộ dữ liệu là **mô phỏng, hư cấu** — mọi số hiệu / nội dung / người ký đều giả lập, **không** phải
  văn bản pháp luật thật.
- Hệ thống **phơi bày** conflict / version để LLM **suy luận**, **không** tự động phân xử mọi ca.
- Con số benchmark trong pitch deck (Context Precision / Recall / Answer Accuracy) là **mục tiêu
  thiết kế**, **chưa** phải artifact benchmark được verify trong repo — hãy chạy `python -m eval
  judge` để tạo số thật.

**Known v1 shortcuts:** `BackgroundTasks` thay Celery; `create_all` thay Alembic migration; CORS
`allow_origins=["*"]`; Vite dev server thay static nginx build; graph-build chạy ngoài lifecycle
`run_pipeline()` nên restart giữa build có thể để `graph_status` kẹt `building` (khắc phục bằng
crash-recovery lúc startup + reprocess).

---

## 13. Hướng nâng cấp (v2 — backlog để lên production)

**Kỹ thuật:** job queue (Celery) thay `BackgroundTasks` · Alembic migration · Postgres thay SQLite ·
crash-recovery đầy đủ cho graph build · engine vòng đời hiệu lực (partial supersession) thay
hard-filter · render Graph Facts trên UI · benchmark thật + continuous eval / regression gate ·
khắc phục self-reference của Context Precision/Recall · sizing & scale Qdrant / Neo4j, giám sát chi
phí LLM · bảo mật (RBAC, secret management, audit log, PII, siết CORS).

**Nghiệp vụ:** pilot trên corpus **thật** thay bộ mô phỏng DDB · hợp tác Domain Expert dựng Golden
Dataset & quy trình review · tuân thủ pháp lý (data residency, phê duyệt NHNN, on-prem) · chứng nhận
(ISO 27001 / SOC 2, pen-test) · tích hợp SSO / document management / core banking · mô hình kinh
doanh (pricing, ROI, SLA).

---

*BigRAG — From document retrieval to connected, verifiable banking intelligence.*
