# PoC — Giảm noise cho knowledge graph (LightRAG + ontology)

PoC độc lập, **chưa wire vào `app/services/pipeline.py`** — không đụng luồng ingest thật.
Mục tiêu: chứng minh việc ép một *ontology* (entity type + relation type có kiểm soát)
vào bước build knowledge graph bằng LightRAG giúp giảm noise so với extract tự do.

## Vì sao cần ontology

LightRAG mặc định extract entity theo 11 type generic (`Person, Organization, Location,
Event, Concept, Method, Content, Data, Artifact, NaturalObject, ...`) và relation là
free-text keywords không ràng buộc gì. Với tài liệu tài chính/bảo hiểm tiếng Việt (bảng
biểu phí, nhiều con số/điều kiện gần giống nhau) kiểu extract này sinh rất nhiều node
trùng lặp/rác: số tiền bị tách thành entity `Data` riêng, cùng 1 loại phí bị tách thành
2-3 node do cách viết khác nhau, quan hệ vô nghĩa giữa các con số...

Tham khảo 2 nguồn (đọc thêm bằng từ khoá **"ontology operating system knowledge graph"**,
**"reduce noise knowledge graph GraphRAG"**, **entity resolution**):

- [Ontology-Driven GraphRAG: A Framework for Zero-Noise Knowledge Extraction — A. Goyal, Medium](https://medium.com/@aiwithakashgoyal/beyond-simple-extraction-how-production-grade-ontologies-transform-graphrag-from-prototype-to-333742fa41a6)
  (khái niệm "Ontology Operating System": entity/relation type là schema bắt buộc, không
  khớp schema thì không được vào graph; noise điển hình: duplicate entity, đồng nghĩa,
  mất traceability).
- [arXiv:2507.06107 — Khan & Bartolini](https://arxiv.org/pdf/2507.06107) (kiến trúc
  "unified ontology" 4 bước: Schema Definition → Extraction → **Validation & Filtering**
  → Graph Assembly; noise bị chặn ở bước Validation, không sửa ở bước Extraction).

Cả 2 nguồn đều quy về cùng 1 ý: **ontology không chỉ là prompt guidance lúc extract, mà
còn phải là 1 bước validate/filter riêng SAU KHI extract** — vì LLM không tuân thủ 100%
hướng dẫn trong prompt.

## LightRAG hỗ trợ ontology tới đâu (đã verify trên `lightrag-hku==1.5.4`)

| Lever | LightRAG có native hỗ trợ? |
|---|---|
| Constrain **entity type** lúc extract | ✅ `addon_params["entity_types_guidance"]` (free-text, LightRAG nhét thẳng vào `---Entity Types---` của system prompt) |
| Constrain **relation type** lúc extract | ❌ `relationship_keywords` là free-text tự do, không có khái niệm relation-type schema |
| Validate/filter graph sau khi extract (loại node/edge sai schema) | ❌ không có |
| Entity resolution / dedup theo tên chuẩn hoá | ⚠️ LightRAG có dedup nội bộ theo tên khớp *chính xác* qua các lần gleaning, không xử lý biến thể viết hoa/khoảng trắng giữa nhiều lần insert |

→ File `ontology.py` cung cấp cả 2 phần: entity types (feed thẳng vào LightRAG) **và**
relation types + allowed-triples (LightRAG không hỗ trợ, tự validate ở `noise_filter.py`).

## Cấu trúc

```
poc/kg_ontology/
  ontology.py       # ENTITY_TYPES, RELATION_TYPES, ALLOWED_TRIPLES (schema) — domain
                     # tài chính/bảo hiểm VN, bám theo facet đã dùng ở app/catalog_presets.py
  llm_adapter.py     # nối LightRAG -> FPT AI Marketplace (đọc app.config.settings)
  noise_filter.py    # canonicalize_graph (entity resolution) + apply_ontology_filter
                      # (type validation + relation validity + prune orphan)
  sample_input.py     # text mẫu (trích thật từ backend/docs/Biểu phí - 23.6.26.pdf)
  visualize.py         # export graph -> HTML tự chứa (pyvis, không cần internet để mở)
  run_poc.py            # entrypoint: build baseline vs ontology-guided vs ontology+filter
```

## Chạy

```bash
cd backend
pip install -r requirements-poc.txt     # thêm lightrag-hku, pyvis, networkx lên requirements.txt hiện có
python -m poc.kg_ontology.run_poc       # cần FPT_API_KEY + FPT_CHAT_MODEL + FPT_EMBED_MODEL trong .env
```

Output tại `poc/kg_ontology/_poc_storage/out/` (không commit — đã thêm vào `.gitignore`):

- `baseline.html` — graph LightRAG mặc định, không ontology.
- `ontology_raw.html` — graph với entity type bị constrain, CHƯA post-filter.
- `ontology_filtered.html` — (2) + canonicalize + relation-schema filter = pipeline đề xuất.
- `metrics.json` — số node/edge/entity-type trước-sau mỗi bước + danh sách ví dụ node/edge
  bị loại (để soi bằng mắt filter có hợp lý không, tránh loại oan).

Mở 3 file `.html` bằng trình duyệt để so sánh trực quan — node tô màu theo `entity_type`,
hover vào node/edge xem description gốc do LightRAG sinh ra.

## Giới hạn đã biết (PoC, chưa production-ready)

- `classify_relation_keyword()` trong `ontology.py` là substring-match tiếng Việt/Anh đơn
  giản trên `relationship_keywords`, không phải NLP thật — production nên thay bằng
  embedding similarity hoặc 1 lượt LLM classify relation riêng.
- `canonicalize_graph()` chỉ gộp node khi normalize (casefold + gộp khoảng trắng) trùng
  *tuyệt đối* — không xử lý viết tắt/đồng nghĩa (vd "T2D" vs "Type 2 Diabetes" trong ví dụ
  gốc của bài Medium). Cần thêm fuzzy-match hoặc embedding-based entity resolution.
  `test_infra_pins.py`/`rapidfuzz` đã có sẵn trong `requirements-eval.txt` — có thể tái
  dùng `rapidfuzz` cho bước này nếu đi tiếp.
- Ontology (`ENTITY_TYPES`/`RELATION_TYPES`/`ALLOWED_TRIPLES`) hiện hardcode tay cho domain
  thẻ tín dụng/bảo hiểm, dựa theo 1 sample duy nhất — chưa generalize cho category khác
  trong `catalog_presets.py` (bảo hiểm, quy trình...).
- Chưa đánh giá retrieval quality (không so sánh graph này ảnh hưởng gì tới câu trả lời
  cuối) — PoC chỉ đo *hình dạng graph* (số node/edge/type), chưa đo *ích lợi* cho RAG.
- `llm_adapter.py` gọi thẳng `openai_complete_if_cache`/`openai_embed` của LightRAG thay
  vì qua `app/services/llm_client.py` — có chủ đích (LightRAG tự lái concurrency/retry
  riêng), nhưng nếu PoC này được wire vào app thật thì cần bàn lại chỗ này so với
  "LLM boundary" invariant trong CLAUDE.md.
- Đã verify PoC bằng chạy thật (FPT_API_KEY thật, model GLM-5.2 / Vietnamese_Embedding)
  trên `SAMPLE_TEXT`. 2 bug phát hiện trong lúc verify, đã fix trong code hiện tại:
  1. `apply_ontology_filter` so `entity_type` case-sensitive trong khi LightRAG tự
     lowercase entity_type khi ghi vào graph (`"SanPham"` -> `"sanpham"`) — khiến TOÀN
     BỘ node bị loại oan ở lần chạy đầu. Fix: `ontology.canonical_entity_type()` so khớp
     case-insensitive rồi ghi lại type chuẩn PascalCase lên node.
  2. `llm_model_func` ban đầu không tắt GLM reasoning ("thinking") — khiến build 1
     document 2 chunk mất >15 phút (LightRAG gọi extract + gleaning + continue-extraction
     nhiều lần/chunk, mỗi lần model "nghĩ" trước khi trả lời). Fix: thêm
     `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`, giống hệt
     `_thinking_extra()` trong `llm_client.py` — sau fix, build 1 document ~2-3 phút.
  Sau 2 fix trên, kết quả 1 lần chạy thật (có thể lệch ±vài node/edge giữa các lần chạy
  do LLM không hoàn toàn deterministic): `baseline` 26 node/12 edge (22/26 node type
  `concept` — gần như không phân biệt được gì); `ontology_raw` 52 node/84 edge (đã tách
  đúng `LoaiPhi`/`MucGiaTri`/`SanPham`/`DieuKienApDung`/`ToChuc`/`DieuKhoan` nhưng còn
  quan hệ vô nghĩa, vd `SHBFinance -[thuoc_ve]-> Gói Sung Túc Hàng Năm` — tổ chức "thuộc
  về" sản phẩm là ngược, đúng ra phải là `SanPham -[phat_hanh_boi]-> ToChuc`);
  `ontology_filtered` 40 node/33 edge (loại 44 cạnh sai triple + 7 cạnh không map được
  relation type + 12 node mồ côi phát sinh sau đó) — đúng những quan hệ vô nghĩa nêu trên
  bị loại, xem `dropped_edge_examples` trong `metrics.json` để soi chi tiết.
- Log chạy thật còn 1 warning/error KHÔNG liên quan tới ontology, đến từ chính LightRAG:
  bước flush vector-DB cuối (`NanoVectorDBStorage[entities] index flush failed:
  Embedding dimension mismatch ... expected dimension (1536)`) dù `nano-vectordb:Init`
  log đúng `embedding_dim: 1024`. Đây là lỗi/quirk nội bộ của `lightrag-hku==1.5.4` ở
  bước flush cuối cùng (KHÔNG phải do `llm_adapter.py` cấu hình sai — `EmbeddingFunc`
  truyền đúng `embedding_dim=1024` xuyên suốt), xảy ra SAU KHI graph đã ghi xong
  (`"Writing graph with N nodes, M edges"` luôn log trước lỗi này) — nên KHÔNG ảnh hưởng
  tới graph mà `run_poc.py` đọc lại (đọc thẳng file `.graphml`, không qua vector-DB của
  LightRAG). Chưa root-cause sâu vì không chặn PoC; nếu đi tiếp lên production nên trace
  lại chỗ này trước.
