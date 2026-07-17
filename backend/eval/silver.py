"""Ingest silver vào MLflow: 1 trace/sample (câu hỏi + persona vào, tham chiếu ra) +
2 expectation LLM-sourced (expected_response, reference_contexts) + JSONL artifact.

Không gọi LLM/embedding thật ở đây (LLM boundary thỏa mãn theo kiểu vacuous — mọi giá trị
đã được sinh bởi generation, module này chỉ ghi lại metadata nguồn LLM_JUDGE).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.config import settings


@dataclass
class SilverSample:
    user_input: str                          # câu hỏi
    reference: str                           # câu trả lời tham chiếu (LLM sinh)
    reference_contexts: list[str]            # ngữ cảnh tham chiếu (final_content của chunk nguồn)
    synthesizer_name: str                    # single_hop_specific_query_synthesizer | multi_hop_*
    persona_name: str
    source_document_ids: list[str] = field(default_factory=list)  # id tài liệu nguồn


def ingest_silver(
    samples: list[SilverSample],
    *,
    dataset_name: str,
    experiment: str | None = None,
) -> str:
    """Ghi các sample silver vào MLflow: 1 trace/sample + expectations + JSONL artifact.

    - Mỗi sample -> 1 trace: inputs {question, persona}, outputs {reference, reference_contexts}.
    - Tag trace: dataset_name, synthesizer_name, persona_name, source_document_ids (CSV).
    - log_expectation("expected_response", reference) + log_expectation("reference_contexts",
      reference_contexts) với source LLM_JUDGE (giá trị do LLM sinh khi generate).
    - Toàn bộ silver ghi 1 file JSONL làm artifact của run.
    Trả về run_id.
    """
    import mlflow
    from mlflow.entities import AssessmentSource
    from mlflow.entities.assessment_source import AssessmentSourceType

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(experiment or settings.mlflow_experiment)

    llm_source = AssessmentSource(
        source_type=AssessmentSourceType.LLM_JUDGE,
        source_id=settings.eval_judge_model or settings.fpt_chat_model,
    )

    with mlflow.start_run() as run:
        run_id = run.info.run_id
        for s in samples:
            with mlflow.start_span(name="silver_sample") as span:
                span.set_inputs({"question": s.user_input, "persona": s.persona_name})
                span.set_outputs({
                    "reference": s.reference,
                    "reference_contexts": s.reference_contexts,
                })
                mlflow.update_current_trace(tags={
                    "dataset_name": dataset_name,
                    "synthesizer_name": s.synthesizer_name,
                    "persona_name": s.persona_name,
                    "source_document_ids": ",".join(s.source_document_ids),
                })
                trace_id = span.trace_id
            # Trace được export bất đồng bộ (async queue) — phải flush trước khi
            # log_expectation, nếu không server có thể chưa thấy trace_id vừa tạo
            # (race condition phát hiện khi chạy live: RESOURCE_DOES_NOT_EXIST).
            mlflow.flush_trace_async_logging()
            mlflow.log_expectation(
                trace_id=trace_id, name="expected_response",
                value=s.reference, source=llm_source,
            )
            mlflow.log_expectation(
                trace_id=trace_id, name="reference_contexts",
                value=s.reference_contexts, source=llm_source,
            )
        jsonl = "\n".join(
            json.dumps(_to_record(s), ensure_ascii=False) for s in samples
        )
        mlflow.log_text(jsonl, artifact_file=f"silver/{dataset_name}.jsonl")
    return run_id


def _to_record(s: SilverSample) -> dict:
    return {
        "user_input": s.user_input,
        "reference": s.reference,
        "reference_contexts": s.reference_contexts,
        "synthesizer_name": s.synthesizer_name,
        "persona_name": s.persona_name,
        "source_document_ids": s.source_document_ids,
    }
