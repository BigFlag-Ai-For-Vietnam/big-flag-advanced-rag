"""Chạy eval in-process: nạp dataset (silver JSONL hoặc golden MLflow) -> thực thi kỹ thuật
RAG đã chọn (registry `eval.techniques`, FR-17) -> ghi lại thành MLflow trace đúng hình dạng
mà tích hợp native mlflow.genai.scorers.ragas cần (RETRIEVER span, output
[{"page_content": ...}]).

Việc chấm điểm (mlflow.genai.evaluate() + ragas scorer) nằm ở eval/cli.py::cmd_judge —
module này chỉ chịu trách nhiệm tạo trace, không tự chấm điểm (NFR-2: không import ragas
ở đây, chỉ mlflow — lazy trong hàm để suite offline không cần cài mlflow/ragas).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TOP_K = 5  # khớp QueryRequest.top_k mặc định của playground


@dataclass
class EvalSample:  # 1 dòng dataset đầu vào (từ golden MLflow hoặc silver JSONL)
    user_input: str
    reference: str
    reference_contexts: list[str] = field(default_factory=list)
    synthesizer_name: str | None = None
    persona_name: str | None = None


def _load_jsonl(path: Path) -> list[EvalSample]:
    samples = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            samples.append(EvalSample(
                user_input=d["user_input"],
                reference=d.get("reference", ""),
                reference_contexts=d.get("reference_contexts", []),
                synthesizer_name=d.get("synthesizer_name"),
                persona_name=d.get("persona_name"),
            ))
    return samples


def _load_mlflow_dataset(name: str) -> list[EvalSample]:
    from mlflow.genai.datasets import get_dataset

    ds = get_dataset(name=name)
    samples = []
    for record in ds.to_dict()["records"]:
        inputs = record.get("inputs", {})
        expectations = record.get("expectations", {})
        samples.append(EvalSample(
            user_input=inputs.get("question", ""),
            reference=expectations.get("expected_response", ""),
            reference_contexts=expectations.get("reference_contexts", []),
            persona_name=inputs.get("persona_name"),
        ))
    return samples


def load_dataset(source: str) -> list[EvalSample]:
    """source = đường dẫn JSONL silver (local) HOẶC tên golden dataset trong MLflow.
    JSONL nếu Path(source) tồn tại và đuôi .jsonl; ngược lại coi là tên golden dataset."""
    p = Path(source)
    if p.suffix == ".jsonl" and p.exists():
        return _load_jsonl(p)
    return _load_mlflow_dataset(source)


def traced_answer(question: str, top_k: int = DEFAULT_TOP_K, *, technique=None) -> str:
    """Chạy kỹ thuật RAG đã chọn (mặc định 'trivial' qua registry, FR-17), ghi thành 1
    MLflow trace: span gốc (CHAIN) bọc span RETRIEVER — output span RETRIEVER phải là
    list[{"page_content": ...}] để mlflow.genai.scorers.ragas trích được retrieved_contexts
    (xem extract_retrieval_context_from_trace / _parse_chunk trong mlflow, xác nhận sống).
    Trả về trace_id (đã flush) để cli.py gọi mlflow.get_trace()/log_expectation()."""
    import mlflow
    from mlflow.entities import SpanType

    from eval.techniques import resolve

    technique = technique or resolve("trivial")

    with mlflow.start_span(name="answer", span_type=SpanType.CHAIN) as root:
        root.set_inputs({"question": question, "top_k": top_k})
        response, retrieved_contexts = technique(question, top_k)
        with mlflow.start_span(name="retrieve", span_type=SpanType.RETRIEVER) as rspan:
            rspan.set_inputs({"question": question, "top_k": top_k})
            rspan.set_outputs([{"page_content": c} for c in retrieved_contexts])
        root.set_outputs(response)
        trace_id = root.trace_id

    mlflow.flush_trace_async_logging()  # export bất đồng bộ — phải flush trước khi dùng trace_id
    return trace_id


def run(source: str, *, top_k: int = DEFAULT_TOP_K, technique=None) -> list:
    """Nạp dataset -> chạy kỹ thuật RAG đã chọn (có trace) từng sample -> gắn tag
    synthesizer_name/persona_name lên trace (để cli.py breakdown theo tier/persona sau khi
    chấm điểm, FR-12) -> log expectation 'expected_output' nếu sample có reference -> trả về
    list[Trace] cho cli.py chấm điểm."""
    import mlflow
    from mlflow.entities import AssessmentSource
    from mlflow.entities.assessment_source import AssessmentSourceType

    samples = load_dataset(source)
    traces = []
    for sample in samples:
        trace_id = traced_answer(sample.user_input, top_k, technique=technique)
        if sample.synthesizer_name:
            mlflow.set_trace_tag(trace_id=trace_id, key="synthesizer_name", value=sample.synthesizer_name)
        if sample.persona_name:
            mlflow.set_trace_tag(trace_id=trace_id, key="persona_name", value=sample.persona_name)
        if sample.reference:
            mlflow.log_expectation(
                trace_id=trace_id,
                name="expected_output",
                value=sample.reference,
                source=AssessmentSource(source_type=AssessmentSourceType.LLM_JUDGE, source_id="silver-golden"),
            )
        traces.append(mlflow.get_trace(trace_id))
    return traces
