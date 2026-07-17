# eval-rag — CLI đánh giá RAG (RAGAS + MLflow)

CLI đánh giá chất lượng RAG: sinh testset tiếng Việt (single-hop + multi-hop) từ tài liệu
đã index, để SME duyệt trong MLflow, rồi chạy eval thật (RAG + ragas metrics) trên bộ dữ liệu
đã duyệt (golden). Chạy từ `backend/` trên host: `python -m eval <lệnh>`.

## 1. CLI reference

Cả 5 lệnh dưới đây cần cài `requirements-eval.txt` (`pip install -r requirements-eval.txt`)
và `.env` với `FPT_API_KEY` hợp lệ; hầu hết cũng cần MLflow đang chạy (§5 nói về networking).

### `generate` — sinh testset silver
```bash
python -m eval generate --all --size 20 --personas eval/personas.json --prompts-dir eval/prompts/vi
```
| Flag | Ý nghĩa |
|---|---|
| `--documents id[,id...]` | Danh sách document id cụ thể — id không tồn tại → lỗi; tài liệu chưa `indexed` → lỗi nêu rõ trạng thái (FR-1). |
| `--all` | Dùng mọi tài liệu đã `indexed` (thay cho `--documents`). |
| `--size N` (mặc định 20) | Tổng số câu hỏi sinh ra, chia đều cho các persona (FR-4). |
| `--personas <path>` (**bắt buộc**) | File `personas.json` — thiếu file → CLI thoát lỗi nêu tên `personas.json` (FR-4, §4). |
| `--prompts-dir <dir>` (mặc định `eval/prompts/vi`) | Thư mục prompt tiếng Việt đã adapt — nạp bởi `adapt-prompts` (FR-5). |
| `--max-exclusion-rate` (mặc định `0.2`) | Ngưỡng loại tối đa của cổng ngôn ngữ (NFR-5). |
| `--out-dir` (mặc định `eval_runs/generate`) | Thư mục ghi `kg.json` / `language_gate_report.json` / `silver.jsonl` trước khi log lên MLflow. |
| `--kg-file <path>` (tùy chọn) | KG ngoài theo contract v1 (FR-2, §3) — bỏ qua transforms tự dựng khi được truyền. |

Phân bổ loại câu hỏi mặc định `0.5 / 0.25 / 0.25` giữa `SingleHopSpecificQuerySynthesizer` /
`MultiHopAbstractQuerySynthesizer` / `MultiHopSpecificQuerySynthesizer` (FR-3). Mỗi run log
lên MLflow: `kg.json`, `language_gate_report.json`, `personas.json`, thư mục `prompts/` đã
dùng, và `silver.jsonl` — đầy đủ để trace lại dataset từ đâu ra (NFR-4). Cổng ngôn ngữ loại
mẫu không phải tiếng Việt trước khi ghi silver; loại > 20% → thoát lỗi + tag
`quality_gate=failed` (FR-5, NFR-5).

### `adapt-prompts` — adapt prompt sang tiếng Việt (chạy 1 lần)
```bash
python -m eval adapt-prompts --prompts-dir eval/prompts/vi
```
Adapt prompt của 3 synthesizer + 4 extractor LLM-based (SummaryExtractor/ThemesExtractor/
NERExtractor/CustomNodeFilter) sang tiếng Việt qua `adapt_prompts("vietnamese", llm=...)`,
lưu xuống `--prompts-dir` để `generate` tái sử dụng. **Lưu ý**: chất lượng adapt phụ thuộc
LLM — có thể lệch ngôn ngữ (caveat đã biết của ragas); cổng ngôn ngữ trong `generate` là lưới
an toàn cho việc này, không phải cơ chế chính để đảm bảo chất lượng.

### `review-queue --dataset <name>` — tạo hàng đợi SME duyệt (`should`, FR-7)
```bash
python -m eval review-queue --dataset <dataset_name>
```
Tạo MLflow Review Queue (experimental, MLflow 3.14) trên mọi trace silver có tag
`dataset_name` khớp, với 3 câu hỏi: `approve` (pass/fail), `expected_response` (sửa text),
`reference_contexts` (sửa text). Vì tính năng này còn experimental, xem §2 cho quy trình dự
phòng ổn định.

### `promote --dataset <name>` — gom mẫu đã duyệt vào golden dataset (FR-8)
```bash
python -m eval promote --dataset <dataset_name>
```
Tìm trace có feedback `approve = pass`, ưu tiên expectation nguồn **HUMAN** (SME sửa) hơn
**LLM_JUDGE** (do generate sinh), merge vào MLflow Evaluation Dataset `golden-<name>` +
JSONL snapshot artifact. Chạy lại `promote` **không** tạo bản sao — `merge_records` upsert
theo `inputs` (đã xác nhận sống trên MLflow 3.14: xem cảnh báo record-identity ở cuối §1).

### `run --dataset <golden-name | đường dẫn silver JSONL>` — chạy eval thật (FR-9)
```bash
python -m eval run --dataset golden-<name>          # hoặc: --dataset eval_runs/generate/silver.jsonl
```
| Flag | Ý nghĩa |
|---|---|
| `--dataset` (**bắt buộc**) | Tên golden dataset trong MLflow, HOẶC đường dẫn file `.jsonl` silver cục bộ. |
| `--top-k` (mặc định `5`) | Số chunk retrieval — khớp mặc định `QueryRequest.top_k` của playground. |

**Dùng tích hợp native của MLflow + ragas** (`mlflow.genai.evaluate()` +
`mlflow.genai.scorers.ragas`), không tự gọi `ragas.evaluate()` thủ công và không tự
`log_params`/`log_metrics`/`log_table` — MLflow tự tạo view **Evaluations** cho run, tự log
assessment lên từng trace.

Với mỗi sample: chạy retrieval + answer **thật** qua `qa_service` (cùng service router
`/api/playground/query` dùng — FR-11), ghi lại thành 1 MLflow trace: span gốc bọc 1 span
`RETRIEVER` (output đúng dạng `[{"page_content": ...}]` — bắt buộc để MLflow trích được
`retrieved_contexts`, xác nhận sống). Nếu sample có `reference`, ghi thêm 1 expectation
`expected_output` lên trace (nguồn LLM_JUDGE) — MLflow tự đọc lại thành trường `reference`
cho scorer khi eval. Sau đó `mlflow.genai.evaluate(data=traces, scorers=[...])` chấm 5 metric
(`Faithfulness`, `AnswerRelevancy`, `ContextPrecision`, `ContextRecall`, `FactualCorrectness`)
với judge FPT truyền dạng model URI `openai:/<model>` (xem §5b — MLflow chỉ nhận URI, tự
dựng client qua litellm/openai SDK bên trong, không tiêm được qua `llm_client` factory).

**Giới hạn đã biết**: MLflow rút cả `retrieved_contexts` lẫn `reference_contexts` từ CÙNG
1 span `RETRIEVER` của trace — không có cách truyền "true" reference context độc lập từ
golden dataset. `ContextPrecision`/`ContextRecall` vì vậy so khớp retrieval với chính nó
(tự tham chiếu) thay vì với ngữ cảnh chuẩn thật sự — chỉ `Faithfulness` (câu trả lời có bám
sát ngữ cảnh đã lấy không) và `AnswerRelevancy` (câu trả lời có đúng trọng tâm câu hỏi không)
là hoàn toàn đáng tin trong tích hợp native này; `FactualCorrectness` dùng `reference` (không
bị ảnh hưởng bởi giới hạn trên) nên vẫn đáng tin.

**Tốc độ**: mỗi sample chạy tuần tự qua cả 5 scorer (không song song) — đo được ~4-5 phút/mẫu
khi cả 5 metric cùng chấm 1 câu hỏi qua FPT. Với dataset nhiều mẫu, cân nhắc `--size` nhỏ khi
test hoặc chấp nhận thời gian chạy dài hơn tương ứng.

**Cảnh báo record-identity** (quan trọng khi tự chỉnh sửa `promote`/`generate`): danh tính
của một golden record là toàn bộ nội dung dict `inputs` — MLflow so khớp bằng nội dung, không
phân biệt thứ tự key, nhưng **bất kỳ key nào khác trong `inputs`** (kể cả các trường không ổn
định như `trace_id`) sẽ khiến 2 mẫu ngữ nghĩa giống nhau bị coi là 2 record khác nhau. `inputs`
chỉ nên chứa đúng `{"question", "persona_name"}` — mọi thứ khác (câu trả lời sửa, ngữ cảnh,
nguồn gốc) phải nằm trong `expectations`/`tags`.

## 2. Quy trình silver → SME → golden (từng bước)

1. `adapt-prompts` (chạy 1 lần, hoặc lại khi cần) → `eval/prompts/vi/`.
2. `generate --all --personas eval/personas.json --prompts-dir eval/prompts/vi` → sinh
   silver JSONL cục bộ **và** ghi trace silver vào MLflow (mỗi mẫu 1 trace, kèm expectation
   `expected_response`/`reference_contexts` nguồn LLM_JUDGE).
3. Mở MLflow UI, experiment `advanced-rag-eval`.
4. **Đường chính** (nếu Review Queue khả dụng): `review-queue --dataset <name>`, SME trả lời
   3 câu hỏi cho từng trace trong Review Queue (UI).
   **Đường dự phòng** (Review Queue experimental/lỗi — ổn định từ MLflow 3.2): SME mở từng
   trace, vào tab **Assessments**, tự sửa `expected_response`/`reference_contexts` (ghi đè
   nguồn HUMAN bên cạnh LLM_JUDGE cũ) và thêm feedback `approve` = pass/fail thủ công.
5. `promote --dataset <name>` → gom trace đã `approve=pass`, ưu tiên giá trị HUMAN, merge vào
   `golden-<name>` + JSONL snapshot. Chạy lại an toàn — không nhân đôi record (xem cảnh báo
   record-identity ở §1).
6. `run --dataset golden-<name>` → xem breakdown metric theo synthesizer/persona, báo cáo
   NaN, và trace retriever+LLM lồng nhau trong MLflow UI.

## 3. External KnowledgeGraph contract (v1)

Đồng nghiệp đang xây một knowledge graph (entities + relations) riêng, chưa xong tại
thời điểm v1 được implement. `python -m eval generate --kg-file <path>` cho phép nạp
graph đó thay vì để `generate` tự dựng KG từ chunk (mặc định).

**Schema chính thức**: `backend/eval/schemas/kg_contract_v1.schema.json` (JSON Schema draft 2020-12).

**Hình dạng file** (`--kg-file`):

```json
{
  "version": 1,
  "entities": [
    {
      "id": "e1",
      "name": "Phí thường niên",
      "type": "Fee",
      "description": "Mô tả tùy chọn",
      "chunk_ids": ["<chunk-uuid-trong-SQLite>", "..."]
    }
  ],
  "relations": [
    {"source": "e1", "target": "e2", "type": "applies_to", "description": "Mô tả tùy chọn"}
  ]
}
```

- `version`: bắt buộc, phải bằng `1`.
- `entities[].id/name/type`: bắt buộc. `description` tùy chọn. `chunk_ids`: danh sách UUID chunk (bảng `chunks` SQLite) mà entity này xuất hiện — tùy chọn, mặc định rỗng.
- `relations[].source/target/type`: bắt buộc. `source`/`target` phải trỏ tới một `entities[].id` đã khai báo. `description` tùy chọn.

**Cách import hoạt động** (`backend/eval/kg_contract.py`): mỗi entity được gắn vào các node CHUNK khớp `chunk_ids` (property `entities` + `kg_entities`); mỗi relation sinh ra một `Relationship` kiểu `entities_overlap` giữa mọi cặp chunk mà 2 đầu (source/target) của relation trỏ tới — đây chính là loại quan hệ mà `MultiHopSpecificQuerySynthesizer` dùng để tìm cluster, nên một relation nối 2 chunk là đủ để multi-hop specific sinh câu hỏi trên graph ngoài.

File không hợp lệ (thiếu `version`/`entities`/`relations`, thiếu field bắt buộc trong từng entity/relation, hoặc `source`/`target` không khớp `id` nào) sẽ raise `KGContractError` nêu rõ field sai/thiếu — fail fast, không sinh testset một phần.

Khi `--kg-file` được truyền, `generate` bỏ qua bước dựng transforms (summary/theme/NER extractor tiếng Việt) cho KG — chunk node vẫn được tạo từ SQLite (T08) nhưng KHÔNG áp transforms tự động; entities/relations của contract là nguồn duy nhất cho cấu trúc đồ thị. Khi không có `--kg-file`, hành vi mặc định (KG tự dựng qua transforms đã adapt tiếng Việt) không đổi.

## 4. `personas.json` — định dạng "user background"

```json
[
  {
    "name": "Khách hàng cá nhân",
    "role_description": "Người dùng thẻ tín dụng lần đầu, quan tâm phí và lãi suất."
  }
]
```

Danh sách persona, mỗi phần tử gồm `name` + `role_description` bằng tiếng Việt (map trực
tiếp sang ragas `Persona`). `generate` chạy 1 batch sinh riêng cho mỗi persona (`--size`
chia đều) rồi gắn `persona_name` lên từng sample — ragas **không** tự lưu persona vào output,
đây là bước bù đắp cần thiết. Thiếu file → CLI thoát lỗi nêu rõ tên `personas.json` (FR-4).
File mẫu tham khảo: `backend/eval/personas.example.json`.

## 5. `MLFLOW_TRACKING_URI` — networking

- **CLI chạy trên host** (`generate`/`adapt-prompts`/`review-queue`/`promote`/`run`): mặc
  định `http://localhost:5000` hoạt động thẳng — CLI với tới MLflow (`infra/`, cổng 5000) và
  Qdrant (`localhost:6333`) trực tiếp, không cần đổi mạng compose nào.
- **Backend chạy trong container** (chỉ ảnh hưởng API chỉ-đọc `/api/eval/*`, FR-13): giá trị
  mặc định `localhost` **không** phân giải được tới host từ bên trong container — phải
  override `MLFLOW_TRACKING_URI` thành `http://host.docker.internal:5000`, hoặc nối app
  compose với mạng của `infra/` compose (2 stack tách biệt theo mặc định — xem
  `docker-compose.yml`, phần comment cạnh `environment:` của service `backend`).
  `GET /api/eval/datasets`/`/runs` trả `503` (thông báo tiếng Việt) khi không kết nối được
  MLflow.

### 5b. Judge FPT cho `run` — biến môi trường OpenAI, không qua `llm_client`

`mlflow.genai.scorers.ragas` (dùng bởi `run`, xem §1) chỉ nhận judge dạng model URI string
(`"openai:/<model>"`), tự dựng client bên trong (qua native provider gateway hoặc litellm) —
**không có cách tiêm một client object đã cấu hình sẵn**. Vì vậy `cmd_run` set trực tiếp
`OPENAI_API_KEY=FPT_API_KEY`, `OPENAI_API_BASE`/`OPENAI_BASE_URL=FPT_BASE_URL` làm biến môi
trường tiến trình trước khi gọi `mlflow.genai.evaluate()`. Đây là **ngoại lệ đã xác nhận và
có chủ đích** đối với bất biến "mọi lời gọi FPT qua `llm_client.make_openai_client()`" —
giới hạn nằm ở chính tích hợp native của MLflow, không phải lựa chọn thiết kế ở đây. Việc dựng
embeddings cho `AnswerRelevancy` vẫn đi qua `make_openai_client()` bình thường (được truyền
trực tiếp dưới dạng object, không qua biến môi trường).

## 6. Ghi nhận quyết định các spike

- **T04 — FPT structured output cho judge**: model `FPT_CHAT_MODEL` (GLM-5.x) là model
  reasoning — `llm_factory` mặc định trả content rỗng (thinking ăn hết output). **Chọn**:
  `llm_factory(model, client=..., extra_body={"chat_template_kwargs": {"enable_thinking":
  False}})` — cả 2 tầng test (structured generate + metric `Faithfulness` thật) đều pass.
  Không dùng `mode=instructor.Mode.MD_JSON` (lỗi `TypeError` trên ragas 0.4.3) hay
  `LangchainLLMWrapper` legacy (hoạt động nhưng bị deprecation-wrap). Chi tiết:
  `backend/eval/spikes/DECISION-structured-output.md`.
- **T06 — `merge_records` semantics**: xác nhận sống trên MLflow 3.14 — `merge_records` là
  **upsert theo nội dung dict `inputs`** (không phân biệt thứ tự key), **không phải append**;
  sửa `expectations` trên record trùng `inputs` sẽ ghi đè toàn bộ (không merge từng key).
  Bất kỳ key thừa nào trong `inputs` (kể cả `trace_id`) sẽ tạo record mới — đây là lý do
  `inputs` chỉ được chứa đúng `{"question", "persona_name"}` (xem cảnh báo ở §1). Chi tiết:
  `meokit/eval-rag/tasks/T06-spike-merge-records.md` (mục Findings).
- **T07 — `mlflow-skinny` coverage**: **GO** — `mlflow-skinny==3.14.0` đủ cho cả 2 API
  (`mlflow.genai.datasets.search_datasets` + `MlflowClient.search_runs`), `pip check` sạch
  với pin backend, không kéo pandas/langchain. Backend thêm thẳng `mlflow-skinny==3.14.0`
  vào `backend/requirements.txt` (không phải `requirements-eval.txt` — đây là dep của app,
  không phải của CLI eval). Lưu ý: `EvaluationDataset.to_df()` cần pandas (skinny không có)
  — dùng `.to_dict()["records"]` thay thế. Chi tiết:
  `meokit/eval-rag/tasks/T07-spike-mlflow-skinny.md` (mục Decision).

## Bất biến kiến trúc (đọc trước khi sửa code eval)

- Mọi lời gọi FPT đi qua factory public của `llm_client.py` (`make_openai_client`) —
  **không bao giờ** tự dựng `openai.OpenAI` trong `backend/eval/` (trừ spike script, đã
  ghi chú rõ trong chính file đó).
- Dep nặng (`ragas`, `mlflow` đầy đủ, `langchain`) chỉ nằm trong `backend/requirements-eval.txt`.
  `backend/requirements.txt` chỉ có `mlflow-skinny` (cho API chỉ-đọc, T20/T07).
- Dataset/trace/run sống trong MLflow — không có thay đổi schema SQLite/Qdrant.
- **MLflow export trace bất đồng bộ**: nếu code của bạn gọi `log_expectation`/`log_feedback`
  ngay sau khi đóng 1 span, gọi `mlflow.flush_trace_async_logging()` trước — nếu không có
  thể gặp lỗi sống `RESOURCE_DOES_NOT_EXIST` (phát hiện khi verify T16/T18 live).
- Cú pháp filter MLflow 3.14 dùng entity type **số ít**: `feedback.<name>`, không phải
  `feedbacks.<name>` (phát hiện khi verify T18 live — server trả `INVALID_PARAMETER_VALUE`
  với dạng số nhiều).
