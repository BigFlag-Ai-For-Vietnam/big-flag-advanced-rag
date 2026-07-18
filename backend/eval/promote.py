"""Golden promotion: gom trace silver đã được SME duyệt (approve=pass), ưu tiên expectation
nguồn HUMAN hơn LLM_JUDGE, merge vào MLflow Evaluation Dataset golden-<name> + JSONL snapshot.

Không import mlflow ở module này — mọi entry point (search_traces, get_or_create_dataset,
log_text) được tiêm từ ngoài (__main__ nối với mlflow thật) để giữ suite offline sạch.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from eval.dataset_upload import EXP_CONTEXTS, EXP_RESPONSE, records_to_jsonl

APPROVE_FEEDBACK = "approve"          # feedback question name (T17 review-queue spec)
PASS_VALUE = "pass"
HUMAN = "HUMAN"


def _source_type(assessment) -> str:
    src = getattr(assessment, "source", None)
    return (getattr(src, "source_type", "") or "").upper()


def _assessments(trace) -> list:
    return list(getattr(getattr(trace, "info", trace), "assessments", []) or [])


def is_approved(trace) -> bool:
    """True nếu trace có feedback 'approve' == 'pass' (SME duyệt)."""
    return any(
        a.name == APPROVE_FEEDBACK and a.value == PASS_VALUE
        for a in _assessments(trace)
    )


def pick_expectation(trace, name: str):
    """Chọn giá trị expectation theo tên; ưu tiên nguồn HUMAN (SME sửa) hơn LLM."""
    matches = [a for a in _assessments(trace) if a.name == name]
    if not matches:
        return None
    human = [a for a in matches if _source_type(a) == HUMAN]
    return (human[0] if human else matches[0]).value


def _trace_inputs(trace) -> dict:
    req = getattr(getattr(trace, "data", None), "request", None) or {}
    return req if isinstance(req, dict) else json.loads(req)


def build_records(traces) -> list[dict]:
    records = []
    for t in traces:
        src = _trace_inputs(t)
        records.append({
            "inputs": {
                "question": src.get("question"),
                # T16 silver-ingest ghi span input với key "persona" (không phải
                # "persona_name") — đọc đúng key thật, chuẩn hoá lại tên field trong
                # record output để khớp quy ước persona_name dùng ở các module khác.
                "persona_name": src.get("persona"),
            },
            "expectations": {
                EXP_RESPONSE: pick_expectation(t, EXP_RESPONSE),
                EXP_CONTEXTS: pick_expectation(t, EXP_CONTEXTS),
            },
        })
    return records


def select_approved_traces(traces) -> list:
    return [t for t in traces if is_approved(t)]


@dataclass
class PromoteResult:
    dataset_name: str
    records: list[dict]
    jsonl: str


def promote(
    dataset_name: str,
    *,
    search_traces,          # callable(...) -> list[trace]  (mlflow.search_traces)
    get_or_create_dataset,  # callable(name) -> dataset obj with .merge_records(records)
    log_text=None,          # callable(text, artifact_file) -> None (mlflow.log_text); optional
) -> PromoteResult:
    """Gom trace đã duyệt -> build record ưu tiên HUMAN -> merge vào golden-<dataset_name>."""
    golden_name = f"golden-{dataset_name}"
    # Cú pháp filter MLflow 3.14 dùng entity type số ít "feedback" (không phải "feedbacks");
    # xác nhận trực tiếp trên server live — "feedbacks." trả lỗi INVALID_PARAMETER_VALUE.
    traces = search_traces(
        filter_string=f"feedback.{APPROVE_FEEDBACK} = '{PASS_VALUE}'",
    )
    approved = select_approved_traces(traces)
    records = build_records(approved)
    dataset = get_or_create_dataset(golden_name)
    dataset.merge_records(records)  # upsert; re-run với inputs giống hệt => không nhân đôi (T06)
    jsonl = records_to_jsonl(records)
    if log_text is not None:
        log_text(jsonl, f"{golden_name}.jsonl")
    return PromoteResult(dataset_name=golden_name, records=records, jsonl=jsonl)
