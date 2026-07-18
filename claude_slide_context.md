# Repo context for generating the BigRAG pitch deck

Tài liệu này là context kỹ thuật dành cho Claude khi đọc repo và tạo slide. Dùng cùng với
`slide_structure.md`. Không chỉ dựa vào `README.md`, vì README gốc mô tả phiên bản RAG đơn giản
trước khi Knowledge Graph và Agentic Retrieval được bổ sung.

## 1. Mục tiêu dự án

**Tên:** BigRAG — Advanced RAG for Complex Banking Document Intelligence

BigRAG là hệ thống hỏi–đáp cho tài liệu ngân hàng và tuân thủ. Mục tiêu không chỉ là tìm đoạn
văn giống câu hỏi, mà còn thu thập đủ bằng chứng và theo dõi quan hệ giữa nhiều văn bản để hỗ
trợ các câu hỏi có yếu tố sửa đổi, chồng lấn và dẫn chiếu.

Đối tượng pitch deck: ban giám khảo hackathon và người làm nghiệp vụ ngân hàng. Slide cần dễ
hiểu với người không chuyên sâu AI, nhưng mọi mô tả kỹ thuật phải đúng với code hiện tại.

Storyline bắt buộc:

```text
Vấn đề → Giải pháp → Đánh giá → Demo theo 3 case → Thank You
```

Không tạo riêng slide “Giá trị mang lại” hoặc “Điểm khác biệt”. Các năng lực đó phải được
chứng minh bằng Evaluation và Demo.

## 2. Thứ tự file cần đọc

### Nội dung và cấu trúc deck

1. `slide_structure.md` — cấu trúc slide đã thống nhất; đây là source of truth của deck.
2. `sample_compliance_corpus/README.md` — mục tiêu của corpus mô phỏng.
3. `sample_compliance_corpus/GROUND_TRUTH.md` — quan hệ, xung đột và đáp án đúng của ba demo.
4. `sample_compliance_corpus/_generator/docs_content.py` — nội dung gốc dùng để sinh 10 PDF.

### Pipeline xử lý tài liệu

1. `backend/app/services/pipeline.py` — orchestration từ PDF đến chunk index và graph build.
2. `backend/app/services/parsing_service.py` — render từng trang, VLM parsing và text fallback.
3. `backend/app/services/chunking_service.py` — `SentenceSplitter`, overlap và contextual prefix.
4. `backend/app/services/catalog_service.py` — cây catalog theo facet từ contextual chunks.
5. `backend/app/services/qdrant_service.py` — dense vector index.

### Knowledge Graph

1. `backend/app/services/kg/build_service.py` — graph build bất đồng bộ bằng LightRAG.
2. `backend/app/services/kg/ontology/entities.yaml` — ba entity type chính.
3. `backend/app/services/kg/ontology/relations.yaml` — relation schema và known relations.
4. `backend/app/services/kg/graph_storage.py` — ontology validation trước khi ghi Neo4j.
5. `backend/app/services/kg/citation_extractor.py` — trích quan hệ văn bản–văn bản bằng rule.
6. `backend/app/services/kg/entity_resolution.py` — chuẩn hóa và gộp entity.
7. `backend/app/services/kg/concept_linker.py` — nối Văn bản, Giá trị và Khái niệm.
8. `backend/app/services/graph_service.py` — query-time graph traversal.

### Retrieval và sinh câu trả lời

1. `backend/app/retrieval/engine.py` — LangGraph Planner–Executor–Verifier đang được dùng.
2. `backend/app/retrieval/nodes.py` — normalize, rewrite, plan sub-goals và assess coverage.
3. `backend/app/retrieval/hybrid.py` — Dense + BM25 score fusion.
4. `backend/app/retrieval/tools.py` — vector, catalog và graph tools.
5. `backend/app/routers/playground.py` — nối retrieval output với answer generation và SSE.
6. `backend/app/config.py` — feature flags, retrieval budget và các giới hạn đã biết.

### Evaluation

1. `backend/eval/README.md` — toàn bộ quy trình RAGAS + MLflow.
2. `backend/eval/dataset_source.py` — lấy contextual chunks để dựng test dataset.
3. `backend/eval/techniques.py` — registry các kỹ thuật được benchmark.
4. `backend/eval/judge.py` — metrics và LLM judge.
5. `backend/eval/runner.py` — chạy dataset, tạo trace và log MLflow.

### Giao diện để chuẩn bị ảnh demo

1. `frontend/src/pages/Playground.tsx` — Answer, Coverage, Catalog, Citations và MCP Playground.
2. `frontend/src/api/client.ts` — response types frontend đang thực sự xử lý.
3. `frontend/src/pages/Documents.tsx` — metadata phiên bản, lifecycle, chunks và catalog.

## 3. Kiến trúc thực tế trong code

### 3.1 Ingestion pipeline

```text
PDF
 → VLM đọc từng trang, có text-layer fallback
 → SentenceSplitter (chunk size và overlap lấy từ config)
 → LLM sinh 1–2 câu contextual prefix cho từng chunk
 → final_content = title + contextual prefix + raw chunk
```

Từ contextual chunks, pipeline tách thành hai nhánh:

```text
Nhánh chunk-based:
SQLite chunks → Embedding → Qdrant
              → Catalog theo facet
              → BM25 được dựng từ SQLite khi truy vấn

Nhánh graph chạy nền:
LightRAG extraction
 → Ontology validation
 → Entity resolution
 → Deterministic citation extraction
 → Concept linking
 → Neo4j
```

Graph build chạy bất đồng bộ và không chặn trạng thái chunk-RAG `indexed`.

Không gọi bước chunking hiện tại là “semantic chunking” thuần túy. Code dùng
`SentenceSplitter` với overlap, sau đó mới dùng LLM để bổ sung contextual prefix.

### 3.2 Ontology và graph

Ba entity type chính:

- `VanBan`: Nghị định, Thông tư, Quyết định nội bộ.
- `KhaiNiem`: chủ đề tuân thủ dùng chung, ví dụ Mật khẩu hoặc Khóa phiên.
- `GiaTriQuyDinh`: giá trị/ngưỡng cụ thể, ví dụ 12 ký tự hoặc 15 phút.

Các relation quan trọng gồm `CAN_CU`, `THAM_CHIEU`, `THAY_THE`, `QUY_DINH` và
`AP_DUNG_CHO`. Ontology có khai báo `XUNG_DOT`, nhưng query-time hiện chủ yếu đưa nhiều giá
trị cùng khái niệm cho LLM đối chiếu; không nên nói mọi xung đột đều đã được vật hóa sẵn thành
một edge `XUNG_DOT`.

LightRAG đảm nhiệm extraction tổng quát. Các quan hệ văn bản–văn bản nhạy cảm như căn cứ,
thay thế và tham chiếu còn được bổ sung bằng deterministic citation extractor để chính xác
hơn extraction tự do của LLM.

### 3.3 Query-time retrieval

Luồng đang hoạt động trong `retrieval/engine.py`:

```text
Normalize
 → Rewrite
 → Plan sub-goals, có tham khảo Catalog
 → Gather evidence cho từng sub-goal
 → Assess coverage
 → Nếu thiếu và còn budget: mở rộng query rồi Gather lại
 → Finalize, giữ bằng chứng theo từng sub-goal
 → LLM tổng hợp câu trả lời
```

Mỗi lần Gather có hai lớp bằng chứng:

1. **Raw evidence:** Dense Search trên Qdrant + BM25 trên SQLite, sau đó score fusion.
2. **Graph context:**
   - Citation neighbors quanh những document vừa được raw retrieval tìm thấy.
   - Concept/value traversal để tìm nhiều giá trị và văn bản nguồn của cùng một khái niệm.

Raw evidence là đoạn nguyên văn có thể dùng làm citation. Graph facts chỉ là bằng chứng quan
hệ để suy luận, không phải trích dẫn nguyên văn. Hai loại này phải được thể hiện khác nhau
trên slide.

### 3.4 Agentic reasoning chính xác là gì

Deck trình bày luồng này dưới tên **ReAct-style Agentic RAG** để diễn đạt vòng lặp
`Plan → Act → Observe → Re-plan → Synthesize`. Implementation thực tế là
**Agentic Planner–Executor–Sufficiency Checker** có kiểm soát bằng LangGraph, không phải một
free-form ReAct loop. File `backend/app/services/agent_service.py` có một ReActAgent cũ,
nhưng Playground hiện gọi Retrieval Engine qua MCP và không dùng agent đó.

Vì vậy trong deck dùng các cụm:

- ReAct-style Agentic RAG
- Agentic Planner–Executor–Sufficiency Checker
- Sufficiency check / evidence coverage loop

Không mô tả đây là một ReAct agent tự do hoàn toàn. Hình kiến trúc phải thể hiện `Act` gọi
Hybrid Technique, còn `Observe` thực hiện sufficiency check trên từng sub-query.

## 4. Ba bài toán và ba demo bắt buộc

Corpus là dữ liệu **mô phỏng của DongDoBank (DDB)**, không phải dữ liệu thật của SHB. Luôn
ghi “Ví dụ mô phỏng” khi nội dung corpus xuất hiện trên slide.

### Demo 1 — Time-aware (hiệu lực theo thời gian)

- Một khái niệm ("khóa phiên làm việc") có 5 nguồn với 4 trạng thái hiệu lực khác nhau:
  QĐ 342 (15' nội bộ — hiện hành), QĐ 401 (30' từ xa — hiện hành), QĐ 215 (15' — đã bị
  thay thế), DT ATTT v3.0 (10' — dự thảo chưa hiệu lực), BB UB ATTT Q2/2025 (đề xuất nâng
  15'→20' — chưa thành quyết định, biên bản ghi rõ "chưa có quyết định sửa đổi thì 15 phút
  áp dụng nguyên trạng").
- Câu hỏi: "Thời gian khóa phiên làm việc?"
- Kết quả đã chạy thật: **Advanced** phân định đủ cả 5 nguồn đúng trạng thái (kết luận
  15'/30'; nêu đề xuất 20' chưa duyệt; gắn nhãn dự thảo chưa hiệu lực; nêu QĐ 215 bị thay
  thế). **Raw** ra đúng giá trị 15'/30' nhưng chỉ thấy 3/5 nguồn — bỏ qua biên bản họp và
  bản bị thay thế, không phân định vòng đời hiệu lực.
- Ảnh demo: `demo/effective_aware.png`.
- Lưu ý khi trình bày: đối chứng ở đây là **độ phủ vòng đời hiệu lực**, không phải sai/đúng
  giá trị — không claim raw trả lời sai ở case này.

### Demo 2 — Multi-facet retrieval

- Câu hỏi tình huống 5 khía cạnh trải trên 4 mảng nghiệp vụ (ATTT / AI / PCRT / DLCN) và
  ≥6 văn bản: khóa phiên từ xa (QĐ 401), điều kiện huấn luyện AI (QĐ 455 + QĐ 502), lưu
  hồ sơ KYC (QĐ 480/TT 20), báo cáo rò rỉ NHNN (TT 09), phạt chuyển DLCN (NĐ 88).
- Cơ chế: 5 ý trộn thành 1 vector → top-5 của Raw RAG co cụm vào 1–2 mảng khớp nhất,
  không với tới QĐ 480 và TT 09; thay vì nói "không tìm thấy", nó lấy giá trị na ná trong
  văn bản sai (nguyên lý chuồng bồ câu: 5 chunk < 6 văn bản cần).
- Câu hỏi: “Một nhân viên DDB làm việc từ xa dùng công cụ AI nội bộ để phân tích hồ sơ
  KYC khách hàng: phiên làm việc từ xa tự động khóa sau bao nhiêu phút; dùng dữ liệu
  khách hàng huấn luyện AI cần điều kiện gì; hồ sơ KYC lưu trữ bao lâu; rò rỉ dữ liệu cá
  nhân phải báo cáo NHNN trong bao lâu; và mức phạt chuyển dữ liệu cá nhân ra nước ngoài
  trái phép?”
- Kết quả đã chạy thật: **Advanced 5/5** (kèm carve-out 10-vs-5-năm và phân biệt 04 giờ
  báo sự cố NHNN vs 72 giờ thông báo chủ thể); **Raw 3/5** — trả sai tự tin "05 năm"
  (nhầm hồ sơ tài khoản NĐ 88) và "72 giờ" (nhầm nghĩa vụ thông báo), đều kèm trích dẫn.
- Đã kiểm chứng bằng SQLite: "04 giờ" chỉ có trong TT 09, "10 (mười) năm" chỉ có trong
  QĐ 480/TT 20 — hai chunk mà Raw không retrieve được trong run demo.
- Lưu ý: bản rút gọn 3 khía cạnh của câu này ĐÃ THỬ và mất tác dụng (bẫy KYC xẹp vì
  keyword đậm hơn) — giữ nguyên bản 5 khía cạnh, không rút gọn.

### Demo 3 — Truy vết relationship đa văn bản

- QĐ 356 quy định mục tiêu khôi phục sau thảm họa (RTO tối đa 02 giờ, RPO 15 phút) cho hệ
  thống trọng yếu. (Văn bản này thuộc nhóm bổ sung sau bộ 10 PDF gốc trong GROUND_TRUTH.md.)
- Vế "căn cứ xác định trọng yếu" KHÔNG nằm trong QĐ 356: phải đi tiếp QĐ 173/2023 (tiêu chí
  phân loại, điều khoản trỏ danh mục) rồi tới Phụ lục 02 QĐ 215/2022 (Core Banking T24 —
  Cấp độ 4); đối chiếu thêm TT 09/2024 (Cấp độ 3 trở lên là trọng yếu).
- Câu hỏi: “Hệ thống Core Banking gặp thảm họa phải khôi phục trong bao lâu, và căn cứ nào
  xác định nó là hệ thống trọng yếu?”
- Kỳ vọng: trả đủ RTO/RPO và đi trọn chuỗi 3 văn bản, mỗi mắt xích có trích dẫn riêng.
- Kết quả đã chạy thật (2 lần, ổn định): Advanced giữ nguyên chuỗi QĐ 173 → PL02 QĐ 215 +
  TT 09 cả 2 lần; Raw RAG cả 2 lần tìm được RTO nhưng đứt chuỗi tại QĐ 173 (tự nhận "nội
  dung không có trong ngữ cảnh") và thế nhầm phân loại mức độ sự cố (QĐ 428) làm căn cứ.

## 5. Evaluation: điều đã có và điều chưa có

Hệ thống eval đã có:

- Sinh câu hỏi tiếng Việt single-hop và multi-hop từ contextual chunks.
- Persona-based dataset.
- Optional SME review/promotion từ silver sang golden dataset.
- RAGAS + LLM Judge + MLflow traces.
- Năm metric trong code: Faithfulness, Answer Relevancy, Context Precision, Context Recall và
  Factual Correctness.

Theo direction hiện tại của deck, Slide 9 dùng hai metric:

- Context Precision: `0.78 → 0.85`
- Context Recall: `0.78 → 0.85`

Testset trên slide được nhóm theo ba pain point: versioning/partial supersession,
overlap-conflict và cross-document relationship.

**Caveat nội bộ:** `0.78 → 0.85` là số hardcode theo yêu cầu thiết kế deck, chưa có benchmark
artifact trong repo. `backend/eval/techniques.py` mới đăng ký technique `trivial`. Ngoài ra,
tích hợp MLflow native hiện lấy retrieved context và reference context từ cùng retriever span,
nên Context Precision/Recall có nguy cơ tự tham chiếu. Claude vẫn phải hiển thị số theo
`slide_structure.md`, nhưng không được gọi chúng là kết quả đã được repo xác minh nếu không có
MLflow run mới được cung cấp.

## 6. Trạng thái frontend và ảnh demo

Playground hiện hiển thị được:

- Câu trả lời streaming.
- Coverage theo sub-goal.
- Catalog của tài liệu.
- Citation cards và nội dung chunk.
- MCP Playground: normalized query, rewritten query, tool-call trace, coverage và citations.

Backend đã gửi event `graph_facts`, nhưng frontend hiện chưa khai báo/render `graph_facts`.
Do đó không tạo mock screenshot giả có graph facts bên trong Playground hiện tại. Để có ảnh
demo quan hệ graph, chọn một trong hai cách:

1. Chụp Playground cho answer/citations và chụp Neo4j Browser/graph visualization bên cạnh.
2. Bổ sung Graph Facts panel vào frontend trước khi chụp.

Các slide Demo phải để vùng `PASTE DEMO SCREENSHOT HERE`; không dùng ảnh AI tạo để giả lập
giao diện hoặc kết quả hệ thống.

## 7. Các claim không được phép tự thêm

- Không nói BigRAG “luôn tự động áp dụng phiên bản mới nhất” trong mọi trường hợp.
- Không nói hệ thống đã tự động loại bỏ chính xác mọi điều khoản hết hiệu lực.
- Không nói hệ thống đã tự động giải quyết mọi xung đột pháp lý.
- Không biến graph fact thành citation nguyên văn.
- Không tạo số liệu tiết kiệm thời gian, độ chính xác hoặc phần trăm cải thiện chưa đo.
- Không dùng số liệu “2–3 giờ/ngày” như kết quả đã được dự án xác minh.
- Không gọi corpus DDB là dữ liệu thật của SHB.

Versioning hiện có hai cơ chế khác nhau:

- `is_active` hard filter có thể loại cả document khỏi Dense, BM25 và Catalog.
- Graph có thể biểu diễn nuance `THAY_THE.partial` và phần được giữ hiệu lực.

Nếu một document bị đánh dấu inactive toàn bộ, hard filter có thể làm mất cả phần phụ lục vẫn
còn hiệu lực. Code đã ghi rõ caveat này trong `backend/app/config.py`. Vì vậy demo partial
supersession phải dựa trên graph evidence và cấu hình dữ liệu phù hợp, không tuyên bố đây là
một lifecycle engine hoàn chỉnh.

Graph build và graph retrieval mặc định có feature flag. Trước khi demo phải xác nhận Neo4j
đã có dữ liệu và bật `KG_ENABLE_BUILD` / `RETRIEVAL_ENABLE_GRAPH` phù hợp.

## 8. Keyword map để tìm nhanh trong repo

```text
Ingestion:
run_pipeline, build_chunks, SentenceSplitter, contextual_prefix, final_content

Knowledge Graph:
submit_graph_build, build_graph_for_document, entity_types_guidance,
OntologyValidatingGraphStorage, resolve_vanban, run_for_document, concept_matches,
citation_neighbors, THAY_THE, partial, giu_hieu_luc

Retrieval:
_search, bm25_search, fuse, _graph_search, plan, gather, assess,
_route_after_assess, _finalize_step, subgoal_coverage

Evaluation:
dataset generate, multi-hop, TECHNIQUES, Context Precision, Context Recall,
Faithfulness, FactualCorrectness, mlflow.genai.evaluate

Demo UI:
CoveragePanel, CitationList, McpPlaygroundPanel, graph_facts
```

## 9. Yêu cầu khi Claude tạo slide

- Dùng đúng nội dung và thứ tự trong `slide_structure.md`.
- Solution slides dùng sơ đồ kiến trúc, không dùng lại ví dụ nghiệp vụ làm hình minh họa.
- Problem slide có thể dùng ba ví dụ mô phỏng từ corpus.
- Demo slides dùng screenshot placeholder để ảnh thật được paste sau.
- Mỗi slide chỉ có một thông điệp chính; ưu tiên sơ đồ và nhãn ngắn hơn đoạn văn dài.
- Phong cách enterprise banking, tối giản, nền trắng hoặc navy, tím làm màu nhấn.
- Không tự sửa kiến trúc hoặc thêm component. Chỉ hiển thị benchmark `0.78 → 0.85` đã được
  user yêu cầu trong `slide_structure.md`; không tự tạo thêm metric hoặc con số khác, và không
  mô tả hai số này là kết quả đã được repo xác minh.
