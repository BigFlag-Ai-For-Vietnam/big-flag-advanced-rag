"""Tạo MLflow Review Queue (experimental, 3.14) cho SME duyệt silver traces của 1 dataset.

APIs mlflow.genai.label_schemas / review_queues còn experimental (FR-7 là "should") —
KHÔNG import mlflow ở top-level (NFR-2): test offline dùng ReviewQueueDeps giả.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# Tên question khớp tên expectation do silver-ingest (FR-6) ghi, để SME sửa đúng
# expectation mà promote (FR-8) sẽ ưu tiên lấy giá trị human-sourced.
APPROVE_Q = "approve"                 # feedback pass/fail: mẫu có đạt để lên golden không
ANSWER_Q = "expected_response"        # expectation text: sửa câu trả lời chuẩn
CONTEXTS_Q = "reference_contexts"     # expectation text: sửa ngữ cảnh tham chiếu


@dataclass(frozen=True)
class ReviewQuestion:
    name: str
    kind: str            # "feedback" | "expectation"
    input: str            # "pass_fail" | "text"
    instruction: str
    positive_label: str | None = None
    negative_label: str | None = None


REVIEW_QUESTIONS: list[ReviewQuestion] = [
    ReviewQuestion(APPROVE_Q, "feedback", "pass_fail",
                   "Mẫu này (câu hỏi + đáp án + ngữ cảnh) có đạt để đưa vào golden không?",
                   positive_label="Đạt", negative_label="Không đạt"),
    ReviewQuestion(ANSWER_Q, "expectation", "text",
                   "Sửa lại câu trả lời chuẩn nếu chưa đúng."),
    ReviewQuestion(CONTEXTS_Q, "expectation", "text",
                   "Sửa lại danh sách ngữ cảnh tham chiếu nếu chưa đúng."),
]


@dataclass
class ReviewQueueDeps:
    """Điểm nối tới MLflow genai — cho phép fake trong test offline."""
    create_label_schema: Callable
    create_review_queue: Callable
    add_items_to_review_queue: Callable
    search_traces: Callable
    input_pass_fail: type
    input_text: type


def _default_deps() -> ReviewQueueDeps:
    import mlflow  # lazy: không import ở top-level
    from mlflow.genai.label_schemas import InputPassFail, InputText, create_label_schema
    from mlflow.genai.review_queues import add_items_to_review_queue, create_review_queue

    return ReviewQueueDeps(create_label_schema, create_review_queue,
                            add_items_to_review_queue, mlflow.search_traces,
                            InputPassFail, InputText)


def _tag_filter(dataset_name: str) -> str:
    return f"tags.dataset_name = '{dataset_name}'"


def create_dataset_review_queue(dataset_name: str, *, deps: ReviewQueueDeps | None = None) -> str:
    """Tạo review queue cho toàn bộ trace silver của dataset_name; trả về queue_id."""
    deps = deps or _default_deps()
    schema_ids = []
    for q in REVIEW_QUESTIONS:
        inp = (deps.input_pass_fail(positive_label=q.positive_label, negative_label=q.negative_label)
               if q.input == "pass_fail" else deps.input_text())
        s = deps.create_label_schema(name=q.name, type=q.kind, input=inp,
                                      instruction=q.instruction, enable_comment=True)
        schema_ids.append(getattr(s, "schema_id", q.name))
    traces = deps.search_traces(filter_string=_tag_filter(dataset_name), return_type="list")
    queue = deps.create_review_queue(name=f"review-{dataset_name}", queue_type="custom",
                                      schema_ids=schema_ids)
    deps.add_items_to_review_queue(queue.queue_id, item_ids=[t.trace_id for t in traces])
    return queue.queue_id
