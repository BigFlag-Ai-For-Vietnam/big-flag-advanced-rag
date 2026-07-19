# Cấu trúc pitch deck BigRAG

> Khi dùng Claude để tạo slide, gửi kèm `claude_slide_context.md` và yêu cầu đọc file đó
> trước khi thiết kế. File context chứa source-of-truth kỹ thuật, demo cases và các claim
> không được tự suy diễn.

## Storyline tổng thể

1. **Vấn đề** — Slide 2–4: bối cảnh (kèm quote mentor + dataset giả định), ba bài toán nghiệp vụ và giới hạn của RAG truyền thống (kèm diagram RAG truyền thống).
2. **Giải pháp** — Slide 5–8: kiến trúc tổng thể (3 lớp Ingestion/Retrieval/Observe&Evaluation), lớp Ingestion, và lớp Retrieval theo hướng Abstraction → Detail.
3. **Đánh giá** — Slide 9 (Lớp Evaluation): LLM sinh Silver Dataset theo ba pain point và kết quả benchmark của BigRAG (Context Precision/Recall + Answer Accuracy).
4. **Demo** — Slide 10–12: ba case tương ứng trực tiếp với ba vấn đề nghiệp vụ; ảnh chụp hệ thống sẽ được paste sau.
5. **Công việc tương lai** — Slide 13: những mảng còn thiếu để lên production (kỹ thuật + nghiệp vụ).
6. **Kết thúc** — Slide 14: Thank You / Q&A.

Không tạo thêm slide “Giá trị mang lại” hoặc “Điểm khác biệt”. Hai nội dung này phải được chứng minh bằng Evaluation và Demo, không tách thành claim độc lập.

## Slide 1 — Title

BigRAG
Advanced RAG for Complex Banking Document Intelligence
Hiểu đúng quy định — Theo đúng liên kết — Trả lời có căn cứ

## Slide 2 — Bối cảnh

Kho tri thức ngân hàng ngày càng phức tạp
Ngân hàng phải quản lý khối lượng lớn văn bản nội bộ và bên ngoài: quy định, quy trình, thông tư, nghị định, biểu mẫu và hướng dẫn nghiệp vụ.
Thông tin liên quan đến một câu hỏi thường phân tán trong nhiều văn bản và nhiều phiên bản khác nhau.
Hình minh họa: Nhiều loại tài liệu hội tụ về một nhân viên ngân hàng đang tìm kiếm thông tin.

**Quote mentor (đã simplify intent):** đặt trong card kiểu quote, border-left nhấn accent.
> "Với đơn vị nhiều văn bản như SBH, RAG chưa thực sự hiệu quả: văn bản liên tục được thêm mới và cập nhật từ nhiều bộ phận, dễ gây xung đột thông tin. Kho tri thức thiếu tổ chức khiến mỗi khi có thông tư, nghị định mới từ SBV hay Chính phủ, phải mất nhiều thời gian để xác định văn bản nào cần chỉnh sửa."
> — Anh Nguyễn Chiến Thắng · Mentor (SBH)

**Strip dataset giả định (cuối slide):** bộ **51 văn bản mô phỏng** của DongDoBank (DDB) — nghị định / thông tư NHNN + quy định nội bộ, ~500–1.000 chunks; cố ý mang đủ ba tính chất: nhiều phiên bản & thay thế một phần · chồng lấn / khác phạm vi · dẫn chiếu 2–3 bước. (Ví dụ "conflict khi áp dụng" đã chuyển sang Slide 3 để tránh lặp.)

## Slide 3 — Ba bài toán nghiệp vụ

Tìm thấy tài liệu chưa đồng nghĩa với tìm được quy định đúng

### Thay đổi theo thời gian

Văn bản có thể được sửa đổi hoặc thay thế toàn bộ hay một phần.

**Ví dụ mô phỏng:** QĐ 342/2024 thay thế QĐ 215/2022 về An toàn thông tin, nhưng Phụ lục 02 — Danh mục hệ thống trọng yếu của văn bản cũ vẫn còn hiệu lực.

**Minh họa:** Timeline `QĐ 215/2022 — ATTT v1.0 → QĐ 342/2024 — ATTT v2.0`; gạch bỏ các điều khoản cũ nhưng giữ lại Phụ lục 02 bằng màu xanh.

### Quy định chồng lấn

Nhiều văn bản cùng đề cập một vấn đề nhưng khác về giá trị, phạm vi hoặc đối tượng áp dụng.

**Ví dụ mô phỏng:** Cùng quy định về mật khẩu, QĐ 342/2024 yêu cầu tối thiểu **12 ký tự**, còn QĐ 401/2024 nêu **8 ký tự**. Tuy nhiên QĐ 401 đồng thời quy định rằng khi có khác biệt thì ưu tiên áp dụng QĐ 342, vì vậy kết luận đúng là **12 ký tự**.

**Minh họa:** Hai card cùng trỏ vào chủ thể “Độ dài mật khẩu”: `QĐ 342 — 12 ký tự` và `QĐ 401 — 8 ký tự`. Đặt biểu tượng conflict ở giữa, sau đó dùng mũi tên `Ưu tiên QĐ 342` dẫn tới kết luận `Áp dụng 12 ký tự`.

### Quan hệ đa văn bản

Câu trả lời có thể nằm trong chuỗi liên kết giữa nghị định, thông tư và quy định nội bộ.

**Ví dụ mô phỏng:** QĐ 342/2024 về An toàn thông tin nội bộ tuân thủ TT 09/2024/TT-NHNN; TT 09/2024 tiếp tục căn cứ NĐ 88/2024/NĐ-CP.

**Minh họa:** Đồ thị ba tầng `NĐ 88/2024 → TT 09/2024/TT-NHNN → QĐ 342/2024/QĐ-DDB`, với nhãn quan hệ “căn cứ” và “tuân thủ”.

**Bố cục slide:** Ba card đặt ngang tương ứng Timeline — Overlap — Relationship Graph. Mỗi card gồm tên bài toán, một câu mô tả, ví dụ rút gọn và sơ đồ trực quan. Ghi chú nhỏ ở cuối slide: “Ví dụ mô phỏng từ bộ tài liệu tuân thủ DongDoBank (DDB).”

## Slide 4 — Vì sao RAG truyền thống chưa đủ?

RAG truyền thống tìm các đoạn giống câu hỏi, nhưng chưa thực sự hiểu quan hệ giữa chúng
Truy xuất từng đoạn tài liệu riêng lẻ.
Khó theo dõi liên kết giữa nhiều văn bản.
Kết quả top-k có thể bỏ sót một khía cạnh của câu hỏi.
Có nguy cơ sử dụng nội dung cũ hoặc thiếu phạm vi áp dụng.
LLM vẫn có thể tổng hợp câu trả lời dù bằng chứng chưa đầy đủ.

**Bố cục:** 2 cột — bullet bên trái, **diagram RAG truyền thống** bên phải (linear, tông raw):
`Câu hỏi → Embed → Vector Search (top-k) → LLM → Câu trả lời`, chú thích "1 lượt · chunk rời rạc · không theo quan hệ · không kiểm tra đã đủ bằng chứng".

## Slide 5 — Kiến trúc tổng thể BigRAG (MỚI)

**Ba lớp — Ingestion · Retrieval · Observe & Evaluation**

Overview toàn hệ thống trước khi đi vào chi tiết; mỗi lớp là một band ngang, **chỉ hiển thị component (không có tên stack/tool) để tránh rối**. Giữa các band là mũi tên + nhãn thể hiện **mối quan hệ giữa các lớp**:

- **Ingestion:** PDF → Parse → Chunk → Contextualize → Embed → Vector Index · Keyword Index · Catalog · Knowledge Graph (chạy nền).
- **Retrieval:** Retrieval Engine — Plan → Gather → Assess → ↺ → Finalize; Hybrid Retrieval · Graph Retrieval → Sufficiency Check → Answer + Citations.
- **Observe & Evaluation:** Tracing / Telemetry · Silver Dataset · Evaluation Metrics — quan sát & đo toàn pipeline.

```text
[ Ingestion ]  PDF → Parse → Chunk → Contextualize → Embed
               → Vector Index · Keyword Index · Catalog · Knowledge Graph
     ↓  Retrieval đọc Index · Catalog · Graph
[ Retrieval ]  Retrieval Engine — Plan→Gather→Assess→↺→Finalize
               Hybrid Retrieval · Graph Retrieval → Sufficiency Check → Answer + Citations
     ↓  Answer + traces → đo lường & quan sát
[ Observe & Evaluation ]  Tracing / Telemetry · Silver Dataset · Evaluation Metrics
```

Tên stack thực tế (FPT VLM/LLM/Embed, LlamaIndex, Qdrant, SQLite/BM25, LightRAG+Ontology, Neo4j, LangGraph/MCP, RAGAS, MLflow, OTEL) được giữ ở chi tiết từng lớp (Slide 6–9), không nhồi vào overview. Nội dung "hai lớp bằng chứng" (Raw Evidence vs Graph Context) ở Slide 7.

## Slide 6 — Lớp Ingestion

**Tạo ra các chunk self-contained, context-aware và sẵn sàng cho production retrieval**

Luồng xử lý chung:

```text
PDF → VLM đọc từng trang → Sentence-aware Chunking → Contextual Enrichment
```

Sau bước contextual enrichment, pipeline tách thành hai nhánh:

```text
                                   ┌─ Embed → Qdrant Dense Index
Contextual Chunks ─────────────────┼─ SQLite Chunks → BM25 khi truy vấn
                                   └─ Catalog theo facet

Contextual Chunks ── chạy nền ─→ LightRAG Extraction → Ontology Validation
                              → Entity Resolution + Citation Linking → Neo4j Knowledge Graph
```

Điểm nổi bật:
- `SentenceSplitter` giữ ngữ cảnh lân cận bằng chunk overlap.
- LLM bổ sung 1–2 câu định vị để mỗi chunk vẫn có nghĩa khi đứng độc lập.
- Graph được xây dựng bất đồng bộ, không chặn chunk-based RAG sẵn sàng phục vụ.
- Ontology giới hạn graph vào ba nhóm chính: **Văn bản – Khái niệm – Giá trị quy định**.

**Kết luận:** Mỗi chunk không chỉ chứa nội dung gốc mà còn mang theo tên tài liệu, chủ thể và vị trí điều khoản. Nhờ đó chunk có thể đứng độc lập mà vẫn giữ đúng context khi được truy xuất.

**Hình minh họa:** Pipeline dạng “một đầu vào, hai đầu ra”. Bên trái là PDF; ở giữa phóng to một chunk với phần `Contextual Prefix` được highlight; bên phải chia thành **Search Index** và **Knowledge Graph**. Dùng nét đứt hoặc biểu tượng background task cho nhánh graph.

## Slide 7 — Lớp Retrieval (Abstraction)

**Hai kênh bằng chứng, một vòng suy luận có kiểm soát** — mức *cái gì / vì sao* (gộp nội dung slide 5 cũ + thông điệp hybrid).

Ba card khái niệm + sơ đồ agentic overview:
- **Raw Evidence · Chunk-based Hybrid RAG:** Dense Search + BM25 — đoạn có thể trích dẫn nguyên văn.
- **Graph Context · Knowledge Graph:** quan hệ giữa văn bản / khái niệm / giá trị — để đối chiếu, suy luận.
- **Agentic Planner–Executor–Sufficiency:** lập kế hoạch, truy xuất theo mục tiêu, kiểm tra đã đủ trước khi tổng hợp.

```text
                                      ┌─ Hybrid Chunk Retrieval ─→ Đoạn trích nguyên văn ─┐
Câu hỏi → Agentic Planner → Executor ─┤                                                    ├→ Sufficiency Checker
                                      └─ Knowledge Graph ────────→ Quan hệ và ngữ cảnh ───┘          │
                                                                                   thiếu ────────────┘
                                                                                                      ↓
                                                                                   Câu trả lời + nguồn dẫn
```

Hai lane tách màu: **Raw Evidence** — đoạn trích dẫn được; **Graph Context** — quan hệ để suy luận, không trình bày như trích dẫn nguyên văn. Thông điệp: *Raw evidence provides precision. Graph context provides completeness.*

## Slide 8 — Retrieval (Detail implementation)

**Hybrid fusion + ReAct-style Planner–Executor–Sufficiency trên LangGraph** — mức *làm như thế nào* (gộp cơ chế dual-lane của slide 7 cũ + agentic loop của slide 8 cũ).

Bố cục 2 cột: trái = cơ chế Hybrid (2 lane), phải = agentic loop.

**Cơ chế Hybrid (cột trái):**

```text
                         ┌─ Dense · Qdrant ─┐
Query ───────────────────┤                  ├→ Score fusion → Đoạn trích nguyên văn ─┐
                         └─ BM25 · SQLite ──┘                                        │
                                                                                     ├→ Hybrid Evidence · mỗi sub-goal
Query → Neo4j → Citation neighbors + concept/value traversal → Graph Facts ──────────┘
```

**Agentic loop (cột phải):**

BigRAG sử dụng ReAct-style agentic flow được kiểm soát bằng LangGraph:
- **Planning:** hiểu câu hỏi và chia thành các sub-query độc lập.
- **Act / Retrieve:** gọi Hybrid Technique ở Slide 7 cho từng sub-query.
- **Observe / Sufficiency Check:** kiểm tra mỗi mục tiêu đã có đủ raw evidence và relationship context hay chưa.
- **Re-plan:** nếu thiếu, bổ sung hướng tìm kiếm rồi truy xuất lại trong giới hạn budget.
- **Synthesize:** hợp nhất kết quả của tất cả sub-query, tạo câu trả lời và nguồn dẫn.

**Hình minh họa — ReAct-style Agentic Retrieval loop:**

```text
Question → PLAN / Break Sub-queries
                 ↓
       ACT / Hybrid Retrieval
                 ↓
    OBSERVE / Sufficiency Checker
          │                 │
        Missing           Sufficient
          │                 │
      Re-plan ───────────────┘
                            ↓
              SYNTHESIZE ALL RESULTS
                            ↓
                 Answer + Citations
```

Nếu một mục tiêu còn thiếu, hệ thống dùng ghi chú từ bước đánh giá để mở rộng truy vấn và tìm lại. Khi hết ngân sách truy xuất mà vẫn thiếu bằng chứng, phần thiếu được đánh dấu để mô hình không tự suy diễn.

Không đưa câu hỏi ví dụ hoặc tên văn bản vào hình. Thiết kế như một ReAct loop có kiểm soát; `Act` luôn gọi Hybrid Technique, `Observe` chính là Sufficiency Checker, và bước cuối tổng hợp kết quả từ toàn bộ sub-query.

## Slide 9 — Lớp Evaluation

**Mục đích của lớp:** tạo **vòng phản hồi** để cải tiến lớp Ingestion và Retrieval — *cái gì đo lường được thì cải tiến được*.

- **LLM sinh Silver Dataset** từ contextual chunks — ba nhóm câu hỏi tương ứng ba pain point: (1) sửa đổi / thay thế một phần; (2) chồng lấn / conflict giữa nhiều văn bản cùng chủ thể; (3) relationship qua nhiều tầng văn bản.
- **Golden Dataset:** khi có **Domain Expert** bổ sung câu hỏi hoặc review Silver → nâng thành Golden Dataset.
- **Chấm điểm:** dùng **LLM-as-judge** (framework RAGAS), lưu lại trace và kết quả (không nêu tên tool lưu trữ trên slide); công đoạn này cũng cần **Domain Expert review**.

Ba metric đã benchmark của **Advanced BigRAG** (không so sánh với baseline trên slide):
- **Context Precision:** `0.85`
- **Context Recall:** `0.85`
- **Answer Accuracy:** `86%`

**Hình minh họa — benchmark pipeline + feedback:**

```text
Indexed Documents
       ↓
Silver / Golden Dataset
       ↓
BigRAG Full Pipeline
       ↓
Evaluation · LLM-as-judge (RAGAS)
       ↓
↺ Observation + Evaluation Feedback → cải tiến Indexed Documents (Ingestion) & BigRAG Pipeline (Retrieval)
```

**Yêu cầu cho Claude:** Ba metric cards hiển thị trực tiếp `0.85`, `0.85`, `86%`. Bên dưới đặt ba tag nhỏ: `Versioning`, `Conflict`, `Cross-document`. Node "Testset" đổi thành **Silver / Golden Dataset**; cuối sơ đồ là box feedback quay lại Ingestion & Retrieval.

**Ghi chú nội bộ, không đưa lên slide:** `0.85 / 0.85 / 86%` là số user cung cấp cho deck, chưa phải kết quả benchmark có artifact trong repo. Cần thay hoặc xác nhận bằng MLflow run trước khi trình bày như kết quả đo thật.

## Slide 10 — Demo 1: Time-aware (hiệu lực theo thời gian)

**Case:** Một khái niệm ("khóa phiên làm việc") xuất hiện trong **5 nguồn với 4 trạng thái hiệu lực khác nhau**: bản hiện hành (QĐ 342, QĐ 401), bản đã bị thay thế (QĐ 215), dự thảo chưa hiệu lực (DT ATTT v3.0 — 10 phút), và đề xuất trong biên bản họp chưa thành quyết định (BB UB ATTT Q2/2025 — nâng 15'→20'). Hệ thống phải trả giá trị **đang áp dụng** và phân định rõ trạng thái từng nguồn — không để dự thảo/đề xuất/bản cũ lẫn vào căn cứ.

**Câu hỏi demo:** “Thời gian khóa phiên làm việc?”

**Kỳ vọng cần chứng minh (Advanced đã cover trong demo run):**
- Kết luận đúng: **15 phút** máy trạm nội bộ (QĐ 342) · **30 phút** thiết bị từ xa (QĐ 401).
- Đề xuất 20 phút trong biên bản họp UB ATTT Q2/2025: nhận diện **chưa có quyết định sửa đổi → 15 phút áp dụng nguyên trạng**.
- Dự thảo ATTT v3.0 (10 phút): nhận diện là **dự thảo lấy ý kiến, chưa hiệu lực** — không dùng.
- QĐ 215/2022 (15 phút): nêu rõ **đã bị thay thế** bởi QĐ 342.
- Đối chứng: Raw RAG chỉ thấy 3/5 nguồn — ra đúng giá trị 15'/30' nhưng **bỏ qua đề xuất 20' và bản bị thay thế**, không phân định vòng đời hiệu lực.

**Bố cục:** Cột trái ~30% gồm câu hỏi + bảng 5 nguồn với nhãn trạng thái (DỰ THẢO ✗ / CHƯA DUYỆT ✗ / BỊ THAY THẾ ✗ / HIỆN HÀNH ✓) + checklist. Cột phải là ảnh demo (`demo/effective_aware.png`).

## Slide 11 — Demo 2: Multi-facet retrieval

**Case:** Một câu hỏi tình huống chứa 5 khía cạnh trải trên 4 mảng nghiệp vụ (ATTT / AI / PCRT / dữ liệu cá nhân) và ≥6 văn bản — vượt sức chứa của một lần top-k retrieval. Raw RAG không "thiếu" mà **thay đáp án đúng bằng giá trị na ná từ văn bản sai, kèm trích dẫn** — loại lỗi nguy hiểm nhất với nghiệp vụ tuân thủ.

**Câu hỏi demo:** “Một nhân viên DDB làm việc từ xa dùng công cụ AI nội bộ để phân tích hồ sơ KYC khách hàng: phiên làm việc từ xa tự động khóa sau bao nhiêu phút; dùng dữ liệu khách hàng huấn luyện AI cần điều kiện gì; hồ sơ KYC lưu trữ bao lâu; rò rỉ dữ liệu cá nhân phải báo cáo NHNN trong bao lâu; và mức phạt chuyển dữ liệu cá nhân ra nước ngoài trái phép?”

**Kỳ vọng cần chứng minh (Advanced đã cover đủ 5/5 trong demo run):**
- **Khóa phiên từ xa:** 30 phút (QĐ 401/2024).
- **Điều kiện huấn luyện AI:** đồng ý riêng (QĐ 455) / dữ liệu đã ẩn danh, lưu tối đa 24 tháng (QĐ 502).
- **Hồ sơ KYC:** 10 năm (QĐ 480 / TT 20) — kèm carve-out "thay cho 05 năm của QĐ 455 vì pháp luật chuyên ngành".
- **Báo cáo rò rỉ NHNN:** trong 04 giờ (TT 09) — phân biệt với 72 giờ thông báo chủ thể dữ liệu (NĐ 88).
- **Phạt chuyển DLCN trái phép:** 200–300 triệu đồng (NĐ 88 Đ14).
- Đối chứng: Raw RAG 3/5 — trả **"05 năm"** (nhầm hồ sơ tài khoản NĐ 88) và **"72 giờ"** (nhầm nghĩa vụ thông báo) một cách tự tin, có trích dẫn; nguồn top-5 co cụm vào 1–2 mảng, không với tới QĐ 480 và TT 09.

**Bố cục:** Cột trái ~32% gồm câu hỏi (font nhỏ hơn do dài) + checklist 5 khía cạnh + dòng đối chứng Raw. Cột phải là ảnh demo so sánh hai pipeline; không dùng ảnh AI tạo.

## Slide 12 — Demo 3: Truy vết relationship đa văn bản

**Case:** Câu trả lời nằm ở cuối một chuỗi dẫn chiếu ba văn bản — văn bản đầu chuỗi chỉ chứa con số (RTO/RPO), còn vế "căn cứ nào" buộc phải đi qua hai văn bản nữa mới tới danh mục gốc.

**Câu hỏi demo:** “Hệ thống Core Banking gặp thảm họa phải khôi phục trong bao lâu, và căn cứ nào xác định nó là hệ thống trọng yếu?”

**Kỳ vọng cần chứng minh (Advanced đã cover trong demo run, lặp lại ổn định 2 lần):**
- **RTO tối đa 02 giờ, RPO 15 phút** cho hệ thống trọng yếu (QĐ 356).
- Truy vết chuỗi dẫn chiếu: QĐ 356 → **QĐ 173/2023** (tiêu chí phân loại + điều khoản trỏ danh mục) → **Phụ lục 02 QĐ 215/2022** (Core Banking T24 — Cấp độ 4).
- Đối chiếu chuẩn Nhà nước: **TT 09/2024** — hệ thống Cấp độ 3 trở lên là trọng yếu.
- Mỗi mắt xích của chuỗi có trích dẫn riêng — không suy diễn ngoài nguồn.
- Đối chứng: Raw RAG tìm được con số RTO nhưng **đứt chuỗi tại QĐ 173** (thấy tên văn bản, tự nhận "nội dung không có trong ngữ cảnh") và vơ nhầm phân loại mức độ sự cố làm căn cứ.

**Bố cục:** Cột trái ~30% gồm câu hỏi + chuỗi dẫn chiếu rút gọn `QĐ 356 → QĐ 173 → Phụ lục 02 QĐ 215` + checklist kỳ vọng. Cột phải là ảnh demo so sánh hai pipeline; không dùng ảnh AI tạo.

## Slide 13 — Công việc tương lai

**Công việc tương lai — để trở thành sản phẩm production**

Liệt kê hai cột (không claim đã làm — đây là backlog để lên production):

- **Kỹ thuật (Technical):**
  - Hạ tầng & vận hành: job queue (Celery) thay BackgroundTasks · Alembic migrations · Postgres thay SQLite · crash-recovery cho graph build.
  - Bảo mật: xác thực & phân quyền (RBAC) · quản lý secret · audit log · xử lý PII · siết CORS.
  - Chất lượng & đánh giá: benchmark thật + continuous eval / regression gate · mở rộng testset · khắc phục self-reference của Precision/Recall.
  - Retrieval & dữ liệu: engine vòng đời hiệu lực (partial supersession) thay hard-filter · render Graph Facts trên UI · sizing & scale Qdrant / Neo4j, giám sát chi phí LLM.
- **Nghiệp vụ (Business):**
  - Dữ liệu thật: pilot trên corpus thật của ngân hàng thay bộ mô phỏng DDB.
  - Domain Expert: hợp tác chuyên gia dựng Golden Dataset & quy trình review định kỳ.
  - Tuân thủ pháp lý: data residency, phê duyệt NHNN, triển khai on-prem.
  - Bảo mật & chứng nhận: ISO 27001 / SOC 2, pen-test.
  - Tích hợp & vận hành: SSO, hệ thống quản lý văn bản, core banking · đào tạo & change management.
  - Mô hình kinh doanh: pricing, đo ROI & SLA, hỗ trợ khách hàng.

## Slide 14 — Thank You

BigRAG
From document retrieval to connected, verifiable banking intelligence.

**Thank you — Q&A**

Thiết kế tối giản, chỉ giữ logo/tên dự án, tagline và thông tin đội. Không lặp lại phần “Giá trị mang lại” hoặc “Điểm khác biệt”; các năng lực này phải được thể hiện bằng kết quả đánh giá và ba demo trước đó.
