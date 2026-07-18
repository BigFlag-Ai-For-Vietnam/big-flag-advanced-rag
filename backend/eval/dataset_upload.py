"""Upload thẳng testset (post-gate) lên MLflow Evaluation Dataset đặt tên (FR-16, rev 3).

Đường chính rev 3: `dataset generate --dataset <name>` merge mẫu retained thẳng vào dataset,
KHÔNG cần bước silver-trace/SME/promote (T16-T18, vẫn còn nhưng là đường tùy chọn `should`).
Record shape khớp `promote.py` (T18) để tương thích khi refine golden sau này — `inputs`
CHỈ chứa `{question, persona_name}` (bất biến record-identity, xem README §1); mọi field khác
(câu trả lời, ngữ cảnh) nằm trong `expectations`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

EXP_RESPONSE = "expected_response"    # expectation key: câu trả lời tham chiếu (README §3)
EXP_CONTEXTS = "reference_contexts"   # expectation key: ngữ cảnh tham chiếu — dùng chung với promote.py (T18)


def build_records(samples: list[dict]) -> list[dict]:
    """Sample silver (post-gate, dict với user_input/reference/reference_contexts) -> record
    MLflow Evaluation Dataset. Hàm thuần, không import mlflow — dễ test."""
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


def upload(dataset_name: str, samples: list[dict]) -> UploadResult:
    """Create-or-get MLflow Evaluation Dataset `dataset_name` (dùng experiment đang active,
    đã set qua mlflow.set_experiment trước đó) rồi merge_records — upsert theo nội dung
    `inputs` (T06 spike), re-run không nhân đôi record."""
    from mlflow.exceptions import MlflowException
    from mlflow.genai.datasets import create_dataset, get_dataset

    records = build_records(samples)
    try:
        dataset = get_dataset(name=dataset_name)
    except MlflowException:
        dataset = create_dataset(name=dataset_name)
    dataset.merge_records(records)
    return UploadResult(dataset_name=dataset_name, records=records, jsonl=records_to_jsonl(records))
