# Cấu trúc pitch deck BigRAG

> Khi dùng Claude để tạo slide, gửi kèm `claude_slide_context.md` và yêu cầu đọc file đó
> trước khi thiết kế. File context chứa source-of-truth kỹ thuật, demo cases và các claim
> không được tự suy diễn.

## Storyline tổng thể

1. **Vấn đề** — Slide 2–4: bối cảnh, ba bài toán nghiệp vụ và giới hạn của RAG truyền thống.
2. **Giải pháp** — Slide 5–8: kiến trúc BigRAG, ingestion pipeline, retrieval và agentic reasoning.
3. **Đánh giá** — Slide 9: testset theo ba pain point và kết quả benchmark của BigRAG (Context Precision/Recall + Answer Accuracy).
4. **Demo** — Slide 10–12: ba case tương ứng trực tiếp với ba vấn đề nghiệp vụ; ảnh chụp hệ thống sẽ được paste sau.
5. **Kết thúc** — Slide 13: Thank You / Q&A.

Không tạo thêm slide “Giá trị mang lại” hoặc “Điểm khác biệt”. Hai nội dung này phải được chứng minh bằng Evaluation và Demo, không tách thành claim độc lập.

## Slide 1 — Title

BigRAG
Advanced RAG for Complex Banking Document Intelligence
Hiểu đúng quy định — Theo đúng liên kết — Trả lời có căn cứ

## Slide 2 — Bối cảnh

Kho tri thức ngân hàng ngày càng phức tạp
Ngân hàng phải quản lý khối lượng lớn văn bản nội bộ và bên ngoài: quy định, quy trình, thông tư, nghị định, biểu mẫu và hướng dẫn nghiệp vụ.
Thông tin liên quan đến một câu hỏi thường phân tán trong nhiều văn bản và nhiều phiên bản khác nhau.
**Ví dụ:** Nhiều văn bản cùng quy định một chủ thể hoặc khái niệm nhưng đưa ra nội dung, phạm vi hay điều kiện khác nhau, tạo ra conflict khi áp dụng.
Hình minh họa: Nhiều loại tài liệu hội tụ về một nhân viên ngân hàng đang tìm kiếm thông tin.

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

## Slide 5 — Giải pháp BigRAG

**Hai lớp bằng chứng, một quy trình suy luận có kiểm soát**

BigRAG kết hợp:
- **Chunk-based Hybrid RAG:** tìm chính xác nội dung, số liệu và điều khoản bằng Dense Search + BM25.
- **Knowledge Graph:** bổ sung quan hệ giữa văn bản, khái niệm và các giá trị quy định.
- **Agentic Planner–Executor–Sufficiency Checker:** lập kế hoạch, thực thi truy xuất theo từng mục tiêu và kiểm tra bằng chứng đã đủ trước khi tổng hợp.

**Hình minh họa — kiến trúc tổng thể:**

```text
                                      ┌─ Hybrid Chunk Retrieval ─→ Đoạn trích nguyên văn ─┐
Câu hỏi → Agentic Planner → Executor ─┤                                                    ├→ Sufficiency Checker
                                      └─ Knowledge Graph ────────→ Quan hệ và ngữ cảnh ───┘          │
                                                                                   thiếu ────────────┘
                                                                                                      ↓
                                                                                   Câu trả lời + nguồn dẫn
```

Thiết kế hai lane có màu khác nhau: **Raw Evidence** cho các đoạn văn bản có thể trích dẫn và **Graph Context** cho quan hệ dùng để suy luận. Không trình bày graph fact như một trích dẫn nguyên văn.

## Slide 6 — Production Parsing & Chunking Flow

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

## Slide 7 — Hybrid Technique kết hợp RAG và Graph

**Graph cung cấp relationship baseline; Contextual Chunk RAG cung cấp bằng chứng chính xác để trả lời**

- **Contextual Chunk RAG:** Dense Search + BM25 tìm nội dung cụ thể, số liệu và điều khoản chính xác trong các chunk đã được bổ sung context.
- **Knowledge Graph:** tạo baseline về văn bản, khái niệm, giá trị và các relationship liên quan để mở rộng phạm vi tìm kiếm.
- **Hybrid Evidence:** giữ raw chunk làm nguồn trả lời và graph facts làm ngữ cảnh để đối chiếu, không trộn lẫn hai loại bằng chứng.

**Hình minh họa — kiến trúc dual-lane retrieval:**

```text
                         ┌─ Dense Search / Qdrant ─┐
Query → Contextual RAG ──┤                         ├→ Exact Raw Evidence ──────┐
                         └─ BM25 / SQLite ─────────┘                           │
                                                                               ├→ Hybrid Evidence
Query → Knowledge Graph → Document + Concept + Value Relationships            │
                        → Relationship Baseline / Graph Facts ─────────────────┘
```

Không đưa ví dụ nghiệp vụ vào hình này. Dùng icon cho Qdrant, BM25 và Neo4j. Nhấn mạnh Graph giúp biết **cần tìm ở đâu và các văn bản liên quan thế nào**, còn Contextual Chunk cung cấp **nội dung cụ thể dùng để trả lời và trích dẫn**.

**Thông điệp chính:** *Raw evidence provides precision. Graph context provides completeness.*

## Slide 8 — ReAct-style Agentic RAG

**Plan → Break Sub-queries → Retrieve → Sufficiency Check → Synthesize**

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

## Slide 9 — Đánh giá hệ thống

**Đánh giá khả năng lấy đúng và lấy đủ context cho ba pain point nghiệp vụ**

Testset được dựng từ ba nhóm câu hỏi tương ứng với ba pain point chính:
1. Văn bản được sửa đổi hoặc thay thế một phần.
2. Nội dung chồng lấn hoặc conflict giữa nhiều văn bản cùng nói về một chủ thể.
3. Câu hỏi cần truy vết relationship qua nhiều tầng văn bản.

Ba metric đã benchmark của **Advanced BigRAG** (không so sánh với baseline trên slide):
- **Context Precision:** `0.85`
- **Context Recall:** `0.85`
- **Answer Accuracy:** `86%`

**Hình minh họa — benchmark pipeline:**

```text
Indexed Documents
       ↓
Testset: Versioning | Conflict | Cross-document Relationship
       ↓
BigRAG Full Pipeline
       ↓
RAGAS + MLflow
       ↓
Context Precision | Context Recall | Answer Accuracy
```

**Yêu cầu cho Claude:** Ba metric cards hiển thị trực tiếp `0.85`, `0.85`, `86%`. Bên dưới đặt ba tag nhỏ: `Versioning`, `Conflict`, `Cross-document`.

**Ghi chú nội bộ, không đưa lên slide:** `0.85 / 0.85 / 86%` là số user cung cấp cho deck, chưa phải kết quả benchmark có artifact trong repo. Cần thay hoặc xác nhận bằng MLflow run trước khi trình bày như kết quả đo thật.

## Slide 10 — Demo 1: Văn bản thay đổi theo thời gian

**Case:** Một văn bản mới thay thế văn bản cũ nhưng vẫn giữ hiệu lực một phần nội dung.

**Câu hỏi demo:** “Quy chế An toàn thông tin nào đang có hiệu lực và phần nào của văn bản cũ vẫn được áp dụng?”

**Kỳ vọng cần chứng minh:**
- Xác định QĐ 342/2024 là phiên bản hiện hành.
- Nhận biết QĐ 215/2022 đã bị thay thế một phần.
- Không bỏ sót Phụ lục 02 vẫn còn hiệu lực.
- Hiển thị đoạn trích nguồn và quan hệ `THAY_THE` với thuộc tính partial.

**Bố cục:** Cột trái chiếm khoảng 30% cho câu hỏi và ba ý cần quan sát. Cột phải chiếm 70% để trống, có khung `PASTE DEMO SCREENSHOT HERE`. Ảnh sau này nên chứa câu trả lời, citations và graph facts; không dùng ảnh AI tạo.

## Slide 11 — Demo 2: Conflict khi sử dụng dữ liệu cho AI

**Case:** Hai văn bản cùng điều chỉnh việc sử dụng dữ liệu khách hàng để huấn luyện mô hình nhưng đưa ra điều kiện khác nhau và không tuyên bố ưu tiên.

**Câu hỏi demo:** “DDB có được sử dụng dữ liệu khách hàng để huấn luyện mô hình AI không?”

**Kỳ vọng cần chứng minh:**
- QĐ 455/2025 yêu cầu **sự đồng ý riêng** khi dùng dữ liệu cá nhân cho huấn luyện mô hình.
- QĐ 502/2025 cho phép dùng dữ liệu giao dịch **đã ẩn danh**, lưu tối đa **24 tháng**, nhưng không nói rõ yêu cầu đồng ý.
- Phát hiện đây là conflict/điểm chưa rõ thay vì tự kết luận một văn bản thắng.
- Kéo thêm định nghĩa và căn cứ từ NĐ 88/2024 và TT 04/2025 để làm rõ câu hỏi: dữ liệu đã ẩn danh còn được xem là dữ liệu cá nhân hay không.
- Trình bày cả hai hướng bằng chứng, cảnh báo người dùng và dẫn nguồn tương ứng.

**Bố cục:** Cột trái là câu hỏi và conflict rút gọn `Cần đồng ý riêng ↔ Được dùng nếu đã ẩn danh`. Cột phải là khung lớn `PASTE DEMO SCREENSHOT HERE`; ưu tiên ảnh có answer, citation cards của QĐ 455 và QĐ 502, cùng graph visualization nối sang NĐ 88 và TT 04.

## Slide 12 — Demo 3: Quan hệ đa văn bản

**Case:** Câu trả lời yêu cầu đi qua chuỗi văn bản nội bộ và văn bản pháp luật bên ngoài.

**Câu hỏi demo:** “Quy định An toàn thông tin của DDB dựa trên những văn bản pháp luật nào?”

**Kỳ vọng cần chứng minh:**
- Truy vết QĐ 342/2024 đến TT 09/2024/TT-NHNN.
- Tiếp tục mở rộng từ TT 09/2024 đến NĐ 88/2024/NĐ-CP.
- Phân biệt quan hệ graph dùng để suy luận với đoạn văn bản dùng để trích dẫn.
- Trình bày được chuỗi căn cứ nhiều tầng cùng nguồn kiểm chứng.

**Bố cục:** Bên trái là câu hỏi và chuỗi quan hệ rút gọn. Bên phải là khung `PASTE DEMO SCREENSHOT HERE`; ưu tiên ảnh Knowledge Graph visualization kết hợp câu trả lời và citations.

## Slide 13 — Thank You

BigRAG
From document retrieval to connected, verifiable banking intelligence.

**Thank you — Q&A**

Thiết kế tối giản, chỉ giữ logo/tên dự án, tagline và thông tin đội. Không lặp lại phần “Giá trị mang lại” hoặc “Điểm khác biệt”; các năng lực này phải được thể hiện bằng kết quả đánh giá và ba demo trước đó.
