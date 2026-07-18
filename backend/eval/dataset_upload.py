"""Upload thẳng testset (post-gate) lên MLflow Evaluation Dataset đặt tên (FR-16, rev 3).

Đường chính rev 3: `dataset generate --dataset <name>` merge mẫu retained thẳng vào dataset,
KHÔNG cần bước silver-trace/SME/promote (T16-T18, vẫn còn nhưng là đường tùy chọn `should`).
Record shape khớp `promote.py` (T18) để tương thích khi refine golden sau này — `inputs`
CHỈ chứa `{question, persona_name}` (bất biến record-identity, xem README §1); mọi field khác
(câu trả lời, ngữ cảnh) nằm trong `expectations`.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

EXP_RESPONSE = "expected_response"    # expectation key: câu trả lời tham chiếu (README §3)
EXP_CONTEXTS = "reference_contexts"   # expectation key: ngữ cảnh tham chiếu — dùng chung với promote.py (T18)

# Namespace cố định cho sample_id — ĐỔI giá trị này sẽ đổi toàn bộ id, phá mọi so sánh
# giữa các eval run cũ/mới. uuid5 (không phải uuid4): id phải deterministic theo đúng
# record-identity (question, persona_name) mà merge_records upsert theo, để re-run
# `dataset generate` không sinh id mới cho cùng một record.
_SAMPLE_ID_NAMESPACE = uuid.UUID("5c1f3b9e-7c1a-4b6f-9d2e-8a4f6c0d1e2b")


def sample_id(question: str | None, persona_name: str | None = None) -> str:
    """UUID deterministic của 1 sample, dẫn xuất từ (question, persona_name) — cùng cặp
    identity mà MLflow merge_records dùng để upsert. Judge tag id này lên trace nên các
    eval run (khác technique/thời điểm) join được theo từng sample."""
    key = json.dumps([question, persona_name], ensure_ascii=False)
    return str(uuid.uuid5(_SAMPLE_ID_NAMESPACE, key))


def hop_type(synthesizer_name: str | None) -> str:
    """Loại record theo số bước truy hồi: 'single-hop' | 'multi-hop' | 'unknown'.
    Suy ra từ synthesizer ragas (single_hop_* vs multi_hop_*)."""
    s = synthesizer_name or ""
    if s.startswith("single_hop"):
        return "single-hop"
    if s.startswith("multi_hop"):
        return "multi-hop"
    return "unknown"


def build_records(samples: list[dict], *, model: str | None = None) -> list[dict]:
    """Sample silver (post-gate, dict với user_input/reference/reference_contexts) -> record
    MLflow Evaluation Dataset. Hàm thuần, không import mlflow — dễ test.

    Mọi record đều mang `expectations` (reference sinh bởi LLM) nên MLflow's own
    `_infer_source_types` sẽ tự gán `source_type=HUMAN` nếu bỏ mặc định (sai — record
    này không do người tạo). `source`/`tags` được set tường minh ở đây để ghi đúng nguồn
    gốc `llm` + model đã sinh ra record (không dựa vào suy luận ngầm của MLflow)."""
    return [
        {
            "inputs": {
                "question": s.get("user_input"),
                "persona_name": s.get("persona_name"),
            },
            "expectations": {
                EXP_RESPONSE: s.get("reference"),
                EXP_CONTEXTS: s.get("reference_contexts", []),
            },
            "source": {
                "source_type": "CODE",
                "source_data": {"generator": "llm", "model": model} if model else {"generator": "llm"},
            },
            "tags": {
                "source": "llm",
                # sample_id nằm trong tags (KHÔNG vào inputs): inputs là record-identity
                # của merge_records — thêm field vào đó sẽ phá upsert idempotent.
                "sample_id": sample_id(s.get("user_input"), s.get("persona_name")),
                # Loại record: single-hop vs multi-hop (dẫn xuất từ synthesizer ragas).
                "hop_type": hop_type(s.get("synthesizer_name")),
                "synthesizer_name": s.get("synthesizer_name") or "",
                **({"generation_model": model} if model else {}),
            },
        }
        for s in samples
    ]


def records_to_jsonl(records: list[dict]) -> str:
    """Contract JSONL dùng chung bởi đường FR-16 (đây) và FR-8 optional (`promote.py`)."""
    return "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in records)


@dataclass
class UploadResult:
    dataset_name: str
    records: list[dict]
    jsonl: str


def upload(dataset_name: str, samples: list[dict], *, model: str | None = None) -> UploadResult:
    """Create-or-get MLflow Evaluation Dataset `dataset_name` (dùng experiment đang active,
    đã set qua mlflow.set_experiment trước đó) rồi merge_records — upsert theo nội dung
    `inputs` (T06 spike), re-run không nhân đôi record. `model` = id LLM đã sinh dataset
    (stamped vào `source`/`tags` mỗi record, xem `build_records`)."""
    from mlflow.exceptions import MlflowException
    from mlflow.genai.datasets import create_dataset, get_dataset

    records = build_records(samples, model=model)
    try:
        dataset = get_dataset(name=dataset_name)
    except MlflowException:
        dataset = create_dataset(name=dataset_name)
    dataset.merge_records(records)
    return UploadResult(dataset_name=dataset_name, records=records, jsonl=records_to_jsonl(records))
