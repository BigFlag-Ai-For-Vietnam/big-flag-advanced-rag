# eval-rag — CLI đánh giá RAG (RAGAS + MLflow)

CLI đánh giá chất lượng RAG, tách thành **2 lệnh cấp cao nhất** mirror đúng 2 process riêng biệt:
`python -m eval dataset …` (Build/Generate TestDataset: sinh testset tiếng Việt single-hop +
multi-hop từ tài liệu đã index, upload thẳng vào 1 MLflow Evaluation Dataset đặt tên — đường
chính rev 3, FR-16; SME duyệt/promote trong MLflow vẫn là đường tùy chọn `should`, §2) và
`python -m eval judge …` (Eval/Judge: chạy kỹ thuật RAG đã chọn — registry `--technique`,
mặc định `trivial`, FR-17 — + ragas metrics trên 1 dataset, log trace/assessment/breakdown
vào MLflow). Chạy từ `backend/` trên host. **Lệnh phẳng cũ** (`generate`, `run`, ... ở cấp
cao nhất) không còn tồn tại — bị argparse từ chối là lệnh không hợp lệ.

## 1. CLI reference

Mọi lệnh dưới đây cần cài `requirements-eval.txt` (`pip install -r requirements-eval.txt`)
và `.env` với `FPT_API_KEY` hợp lệ; hầu hết cũng cần MLflow đang chạy (§6 nói về networking).

### `dataset generate` — sinh testset + upload dataset MLflow
```bash
python -m eval dataset generate --all --size 20 --personas eval/personas.json --dataset my-dataset
```
| Flag | Ý nghĩa |
|---|---|
| `--documents id[,id...]` | Danh sách document id cụ thể — id không tồn tại → lỗi; tài liệu chưa `indexed` → lỗi nêu rõ trạng thái (FR-1). |
| `--all` | Dùng mọi tài liệu đã `indexed` (thay cho `--documents`). |
| `--size N` (mặc định 20) | Tổng số câu hỏi sinh ra, chia đều cho các persona (FR-4). |
| `--personas <path>` (**bắt buộc**) | File `personas.json` — thiếu file → CLI thoát lỗi nêu tên `personas.json` (FR-4, §5). |
| `--dataset <name>` (**bắt buộc**) | Tên MLflow Evaluation Dataset để upload thẳng mẫu sinh ra (FR-16, đường chính rev 3 — xem dưới). |
| `--out-dir` (mặc định `eval_runs/generate`) | Thư mục ghi `kg.json` / `silver.jsonl` trước khi log lên MLflow. |
| `--kg-file <path>` (tùy chọn) | KG ngoài theo contract v1 (FR-2, §4) — bỏ qua transforms tự dựng khi được truyền. |

KG được dựng từ chunk SQLite bằng transforms mặc định của ragas
(`default_transforms_for_prechunked`, `eval/dataset_source.py::build_kg`) — không cần bước
adapt prompt riêng — trừ khi `--kg-file` được truyền (§4), khi đó KG ngoài thay hoàn toàn cho
bước dựng transforms. Phân bổ loại câu hỏi mặc định `0.5 / 0.25 / 0.25` giữa
`SingleHopSpecificQuerySynthesizer` / `MultiHopAbstractQuerySynthesizer` /
`MultiHopSpecificQuerySynthesizer` (FR-3). Nếu KG (tự dựng hoặc `--kg-file`) không tạo được
cluster nào cho 1 synthesizer multi-hop, `generate` **không** raise lỗi giữa chừng — trọng số
của synthesizer đó được dồn về trivial (single-hop), in cảnh báo ra console và ghi
`multihop_backfill_report.json` làm run artifact (FR-3 r2,
`eval/distribution.py::apply_backfill`). Mỗi run log lên MLflow: `kg.json`, `personas.json`,
`silver.jsonl`, và `dataset_upload.jsonl` (snapshot đúng những gì đã merge vào `--dataset`) —
đầy đủ để trace lại dataset từ đâu ra (NFR-4).

Toàn bộ mẫu sinh ra được upload thẳng vào MLflow Evaluation Dataset tên `--dataset` qua
create-or-get + `merge_records` (`eval/dataset_upload.py`, FR-16) — đây là đường chính rev 3,
**không cần** bước silver-trace/SME/promote (§2 vẫn là đường tùy chọn `should`). Chạy lại
`generate` với cùng `--dataset` merge chứ không nhân đôi record (cùng cơ chế `promote` dùng —
xem cảnh báo record-identity ở cuối mục này).

### `dataset review-queue --dataset <name>` — tạo hàng đợi SME duyệt (`should`, FR-7)
```bash
python -m eval dataset review-queue --dataset <dataset_name>
```
Tạo MLflow Review Queue (experimental, MLflow 3.14) trên mọi trace silver có tag
`dataset_name` khớp, với 3 câu hỏi: `approve` (pass/fail), `expected_response` (sửa text),
`reference_contexts` (sửa text). Vì tính năng này còn experimental, xem §2 cho quy trình dự
phòng ổn định.

### `dataset promote --dataset <name>` — gom mẫu đã duyệt vào golden dataset (FR-8)
```bash
python -m eval dataset promote --dataset <dataset_name>
```
Tìm trace có feedback `approve = pass`, ưu tiên expectation nguồn **HUMAN** (SME sửa) hơn
**LLM_JUDGE** (do generate sinh), merge vào MLflow Evaluation Dataset `golden-<name>` +
JSONL snapshot artifact. Chạy lại `promote` **không** tạo bản sao — `merge_records` upsert
theo `inputs` (đã xác nhận sống trên MLflow 3.14: xem cảnh báo record-identity ở §3).

### `judge --dataset <golden-name | đường dẫn silver JSONL>` — chạy eval thật (FR-9)
```bash
python -m eval judge --dataset golden-<name>          # hoặc: --dataset eval_runs/generate/silver.jsonl
python -m eval judge --dataset golden-<name> --technique trivial   # --technique mặc định 'trivial'
```
Lệnh cấp cao nhất (không nằm dưới `dataset`) — chỉ phụ thuộc vào tên/đường dẫn dataset, không
phụ thuộc trạng thái build dataset (chạy được trên bất kỳ golden dataset hoặc silver JSONL nào).
| Flag | Ý nghĩa |
|---|---|
| `--dataset` (**bắt buộc**) | Tên golden dataset trong MLflow, HOẶC đường dẫn file `.jsonl` silver cục bộ. |
| `--top-k` (mặc định `5`) | Số chunk retrieval — khớp mặc định `QueryRequest.top_k` của playground. |
| `--technique` (mặc định `trivial`) | Kỹ thuật RAG chấm — tra registry `eval/techniques.py` (FR-17). Tên không đăng ký → lỗi liệt kê tên hợp lệ, không chạy gì. |

**Technique registry** (`eval/techniques.py`, FR-17): mọi kỹ thuật RAG đứng sau 1 interface
`(question, top_k) -> (response, retrieved_contexts)`; v1 chỉ có `trivial` (bọc
`qa_service.answer`, đúng flow playground). Thêm kỹ thuật mới (`agentic`,
`agentic-kg-vector`, tính năng tương lai) chỉ là thêm 1 entry vào `TECHNIQUES` — không đổi
dataset hay judge. Kết quả `judge` được tag `technique=<tên>` để so sánh combo
dataset × technique (FR-12 r3).

**Dùng tích hợp native của MLflow + ragas** (`mlflow.genai.evaluate()` +
`mlflow.genai.scorers.ragas`), không tự gọi `ragas.evaluate()` thủ công và không tự
`log_params`/`log_metrics`/`log_table` — MLflow tự tạo view **Evaluations** cho run, tự log
assessment lên từng trace.

Với mỗi sample: chạy kỹ thuật RAG đã chọn (`--technique`, mặc định `trivial` = `qa_service`,
cùng service router `/api/playground/query` dùng — FR-11/FR-17), ghi lại thành 1 MLflow trace:
span gốc bọc 1 span `RETRIEVER` (output đúng dạng `[{"page_content": ...}]` — bắt buộc để
MLflow trích được `retrieved_contexts`, xác nhận sống); trace được gắn tag
`synthesizer_name`/`persona_name` nếu sample có (để breakdown sau, FR-12 r3). Nếu sample có
`reference`, ghi thêm 1 expectation `expected_output` lên trace (nguồn LLM_JUDGE) — MLflow tự
đọc lại thành trường `reference` cho scorer khi eval. Sau đó
`mlflow.genai.evaluate(data=traces, scorers=[...])` chấm 5 metric (`Faithfulness`,
`AnswerRelevancy`, `ContextPrecision`, `ContextRecall`, `FactualCorrectness`) với judge FPT
truyền dạng model URI `openai:/<model>` (xem §6b — MLflow chỉ nhận URI, tự dựng client qua
litellm/openai SDK bên trong, không tiêm được qua `llm_client` factory). Sau khi chấm,
`eval/judge_logging.py` đọc lại trace đã được MLflow gắn assessment, tính breakdown NaN-mean
theo `synthesizer_name` (tier) và `persona_name`, rồi log params + tag `technique=<tên>` +
breakdown metrics vào cùng run (`log_run_metadata`, resume run qua `run_id` vì
`mlflow.genai.evaluate()` tự đóng run của nó) — phần `mlflow.genai.evaluate()` không tự làm
(FR-12 r3).

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

Record shape (`inputs`/`expectations`) và cảnh báo record-identity khi merge: xem §3.

## 2. Quy trình silver → SME → golden (từng bước)

1. `dataset generate --all --personas eval/personas.json --dataset <name>` → sinh silver JSONL
   cục bộ **và** ghi trace silver vào MLflow (mỗi mẫu 1 trace, kèm expectation
   `expected_response`/`reference_contexts` nguồn LLM_JUDGE).
2. Mở MLflow UI, experiment `advanced-rag-eval`.
3. **Đường chính** (nếu Review Queue khả dụng): `dataset review-queue --dataset <name>`, SME
   trả lời 3 câu hỏi cho từng trace trong Review Queue (UI).
   **Đường dự phòng** (Review Queue experimental/lỗi — ổn định từ MLflow 3.2): SME mở từng
   trace, vào tab **Assessments**, tự sửa `expected_response`/`reference_contexts` (ghi đè
   nguồn HUMAN bên cạnh LLM_JUDGE cũ) và thêm feedback `approve` = pass/fail thủ công.
4. `dataset promote --dataset <name>` → gom trace đã `approve=pass`, ưu tiên giá trị HUMAN,
   merge vào `golden-<name>` + JSONL snapshot. Chạy lại an toàn — không nhân đôi record (xem
   cảnh báo record-identity ở §3).
5. `judge --dataset golden-<name>` → xem breakdown metric theo synthesizer/persona, báo cáo
   NaN, và trace retriever+LLM lồng nhau trong MLflow UI.

## 3. Dataset record contract (MLflow Evaluation Dataset)

Cả `dataset generate --dataset <name>` (FR-16, đường chính, `eval/dataset_upload.py`) và
`dataset promote` (FR-8, đường SME tùy chọn, `eval/promote.py`) merge record vào MLflow
Evaluation Dataset theo CÙNG 1 shape — để golden dataset tương thích dù mẫu đi đường nào:

```json
{
  "inputs": {"question": "Phí thường niên bao nhiêu?", "persona_name": "Khách hàng cá nhân"},
  "expectations": {
    "expected_response": "Phí thường niên là 500.000đ",
    "reference_contexts": ["Điều 3: phí thường niên 500.000đ"]
  }
}
```

- **`inputs` CHỈ chứa đúng `{question, persona_name}`** — không thêm field nào khác (kể cả
  `trace_id`, `synthesizer_name`). MLflow `merge_records` upsert theo TOÀN BỘ nội dung dict
  `inputs` (record identity, không phân biệt thứ tự key — xác nhận sống trên MLflow 3.14): bất
  kỳ field thừa nào khiến 2 mẫu ngữ nghĩa giống nhau bị coi là 2 record khác nhau
  — chạy lại `generate`/`promote` sẽ **nhân đôi** record thay vì merge.
- **`expectations` chứa mọi thứ khác**: câu trả lời tham chiếu (`expected_response`), ngữ
  cảnh tham chiếu (`reference_contexts`). Field không nằm trong `inputs` ở trên (câu trả lời
  SME sửa, nguồn gốc, …) phải nằm ở đây hoặc `tags`, không bao giờ ở `inputs`.
- `synthesizer_name` (tier) không có mặt trong record — nó chỉ tồn tại trên trace (tag, dùng
  cho breakdown ở `judge`, xem §1) và trong silver JSONL cục bộ, không merge vào dataset
  MLflow vì sẽ vi phạm bất biến `inputs` ở trên.
- `dataset_upload.py::build_records` (FR-16) và `promote.py::build_records` (FR-8) đều tự
  hiện thực shape này độc lập — input khác nhau (sample dict sinh trực tiếp vs. MLflow trace
  đã qua SME) nên không dùng chung 1 hàm, nhưng output PHẢI khớp contract ở trên.

## 4. External KnowledgeGraph contract (v1)

Đồng nghiệp đang xây một knowledge graph (entities + relations) riêng, chưa xong tại
thời điểm v1 được implement. `python -m eval dataset generate --kg-file <path>` cho phép
nạp graph đó thay vì để `generate` tự dựng KG từ chunk (mặc định).

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

Khi `--kg-file` được truyền, `generate` bỏ qua bước dựng transforms (KG tự dựng qua
`default_transforms_for_prechunked`) — chunk node vẫn được tạo từ SQLite (T08) nhưng KHÔNG áp
transforms tự động; entities/relations của contract là nguồn duy nhất cho cấu trúc đồ thị. Khi
không có `--kg-file`, hành vi mặc định (KG tự dựng qua transforms) không đổi.

## 5. `personas.json` — định dạng "user background"

```json
[
  {
    "name": "Khách hàng cá nhân",
    "role_description": "Người dùng thẻ tín dụng lần đầu, quan tâm phí và lãi suất."
  }
]
```

Danh sách persona, mỗi phần tử gồm `name` + `role_description` bằng tiếng Việt (map trực
tiếp sang ragas `Persona`). `dataset generate` chạy 1 batch sinh riêng cho mỗi persona
(`--size` chia đều) rồi gắn `persona_name` lên từng sample — ragas **không** tự lưu persona
vào output, đây là bước bù đắp cần thiết. Thiếu file → CLI thoát lỗi nêu rõ tên
`personas.json` (FR-4). File mẫu tham khảo: `backend/eval/personas.example.json`.

## 6. `MLFLOW_TRACKING_URI` — networking

- **CLI chạy trên host** (`dataset generate`/`dataset review-queue`/`dataset promote`/`judge`):
  mặc định `http://localhost:5000` hoạt động thẳng — CLI với tới
  MLflow (`infra/`, cổng 5000) và Qdrant (`localhost:6333`) trực tiếp, không cần đổi mạng
  compose nào.
- **Backend chạy trong container** (chỉ ảnh hưởng API chỉ-đọc `/api/eval/*`, FR-13): giá trị
  mặc định `localhost` **không** phân giải được tới host từ bên trong container — phải
  override `MLFLOW_TRACKING_URI` thành `http://host.docker.internal:5000`, hoặc nối app
  compose với mạng của `infra/` compose (2 stack tách biệt theo mặc định — xem
  `docker-compose.yml`, phần comment cạnh `environment:` của service `backend`).
  `GET /api/eval/datasets`/`/runs` trả `503` (thông báo tiếng Việt) khi không kết nối được
  MLflow.

### 6b. Judge FPT cho `judge` — biến môi trường OpenAI, không qua `llm_client`

`mlflow.genai.scorers.ragas` (dùng bởi `judge`, xem §1) chỉ nhận judge dạng model URI string
(`"openai:/<model>"`), tự dựng client bên trong (qua native provider gateway hoặc litellm) —
**không có cách tiêm một client object đã cấu hình sẵn**. Vì vậy `cmd_judge` set trực tiếp
`OPENAI_API_KEY=FPT_API_KEY`, `OPENAI_API_BASE`/`OPENAI_BASE_URL=FPT_BASE_URL` làm biến môi
trường tiến trình trước khi gọi `mlflow.genai.evaluate()`. Đây là **ngoại lệ đã xác nhận và
có chủ đích** đối với bất biến "mọi lời gọi FPT qua `llm_client.make_openai_client()`" —
giới hạn nằm ở chính tích hợp native của MLflow, không phải lựa chọn thiết kế ở đây. Việc dựng
embeddings cho `AnswerRelevancy` vẫn đi qua `make_openai_client()` bình thường (được truyền
trực tiếp dưới dạng object, không qua biến môi trường).

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
