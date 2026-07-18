"""Test eval runner (FR-9) — offline, stub qa_service + mlflow giả qua sys.modules."""
import sys
import types

from app.schemas.playground import Citation
from app.services import qa_service
from eval.runner import EvalSample, load_dataset, run, traced_answer


class _FakeSpan:
    def __init__(self, trace_id):
        self.trace_id = trace_id
        self.inputs = None
        self.outputs = None

    def set_inputs(self, inputs):
        self.inputs = inputs

    def set_outputs(self, outputs):
        self.outputs = outputs

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeMlflow:
    def __init__(self):
        self._counter = 0
        self.entities = types.SimpleNamespace(
            SpanType=types.SimpleNamespace(CHAIN="CHAIN", RETRIEVER="RETRIEVER"),
        )
        self.expectations = []  # (trace_id, name, value, source)
        self.traces = {}
        self.trace_tags = []  # (trace_id, key, value)

    def set_trace_tag(self, *, trace_id, key, value):
        self.trace_tags.append((trace_id, key, value))

    def start_span(self, name=None, span_type=None):
        self._counter += 1
        span = _FakeSpan(f"tr-{self._counter}")
        self.traces[span.trace_id] = span
        return span

    def flush_trace_async_logging(self):
        pass

    def log_expectation(self, *, trace_id, name, value, source=None):
        self.expectations.append((trace_id, name, value, source))

    def get_trace(self, trace_id):
        return self.traces[trace_id]


def test_sample_execution_captures_contexts_and_response(monkeypatch):
    c1 = Citation(document_id="d1", title="T", chunk_index=0, score=0.9, final_content="ND1")
    c2 = Citation(document_id="d1", title="T", chunk_index=1, score=0.8, final_content="ND2")
    recorded = {}

    def fake_retrieve(question, top_k):
        recorded["question"] = question
        recorded["top_k"] = top_k
        return [c1, c2]

    monkeypatch.setattr(qa_service, "retrieve", fake_retrieve)
    monkeypatch.setattr(qa_service, "build_messages", lambda q, citations: [{"role": "user", "content": q}])

    from app.services import llm_client
    monkeypatch.setattr(llm_client, "chat", lambda messages, **kw: "câu trả lời")

    fake = _FakeMlflow()
    monkeypatch.setitem(sys.modules, "mlflow", fake)
    monkeypatch.setitem(sys.modules, "mlflow.entities", fake.entities)

    trace_id = traced_answer("Phí?", top_k=5)

    assert recorded["top_k"] == 5
    assert recorded["question"] == "Phí?"
    root_span = fake.traces[trace_id]
    assert root_span.outputs == "câu trả lời"


def test_run_logs_expectation_only_when_reference_present(monkeypatch, tmp_path):
    def fake_retrieve(question, top_k):
        return []

    monkeypatch.setattr(qa_service, "retrieve", fake_retrieve)
    monkeypatch.setattr(qa_service, "build_messages", lambda q, citations: [{"role": "user", "content": q}])

    from app.services import llm_client
    monkeypatch.setattr(llm_client, "chat", lambda messages, **kw: "trả lời")

    fake = _FakeMlflow()
    entities_mod = types.ModuleType("mlflow.entities")
    entities_mod.SpanType = fake.entities.SpanType

    class _FakeAssessmentSource:
        def __init__(self, source_type, source_id="default"):
            self.source_type = source_type
            self.source_id = source_id

    entities_mod.AssessmentSource = _FakeAssessmentSource
    assessment_source_mod = types.ModuleType("mlflow.entities.assessment_source")
    assessment_source_mod.AssessmentSourceType = types.SimpleNamespace(LLM_JUDGE="LLM_JUDGE")

    monkeypatch.setitem(sys.modules, "mlflow", fake)
    monkeypatch.setitem(sys.modules, "mlflow.entities", entities_mod)
    monkeypatch.setitem(sys.modules, "mlflow.entities.assessment_source", assessment_source_mod)

    jsonl_path = tmp_path / "silver.jsonl"
    jsonl_path.write_text(
        '{"user_input": "Có reference?", "reference": "Đáp án chuẩn", "reference_contexts": []}\n'
        '{"user_input": "Không reference?", "reference": "", "reference_contexts": []}\n',
        encoding="utf-8",
    )

    traces = run(str(jsonl_path), top_k=5)

    assert len(traces) == 2
    assert len(fake.expectations) == 1
    trace_id, name, value, _source = fake.expectations[0]
    assert name == "expected_output"
    assert value == "Đáp án chuẩn"


def test_load_dataset_jsonl(tmp_path):
    jsonl_path = tmp_path / "silver.jsonl"
    jsonl_path.write_text(
        '{"user_input": "Q1", "reference": "R1", "reference_contexts": ["c1"], '
        '"synthesizer_name": "single_hop_specific_query_synthesizer", "persona_name": "p1"}\n',
        encoding="utf-8",
    )
    samples = load_dataset(str(jsonl_path))
    assert samples == [EvalSample(
        user_input="Q1", reference="R1", reference_contexts=["c1"],
        synthesizer_name="single_hop_specific_query_synthesizer", persona_name="p1",
    )]


def test_run_tags_sample_id_on_trace(monkeypatch, tmp_path):
    from eval.dataset_upload import sample_id

    monkeypatch.setattr(qa_service, "retrieve", lambda q, top_k: [])
    monkeypatch.setattr(qa_service, "build_messages", lambda q, citations: [{"role": "user", "content": q}])
    from app.services import llm_client
    monkeypatch.setattr(llm_client, "chat", lambda messages, **kw: "trả lời")

    fake = _FakeMlflow()
    entities_mod = types.ModuleType("mlflow.entities")
    entities_mod.SpanType = fake.entities.SpanType
    entities_mod.AssessmentSource = lambda source_type, source_id="default": None
    assessment_source_mod = types.ModuleType("mlflow.entities.assessment_source")
    assessment_source_mod.AssessmentSourceType = types.SimpleNamespace(LLM_JUDGE="LLM_JUDGE")
    monkeypatch.setitem(sys.modules, "mlflow", fake)
    monkeypatch.setitem(sys.modules, "mlflow.entities", entities_mod)
    monkeypatch.setitem(sys.modules, "mlflow.entities.assessment_source", assessment_source_mod)

    jsonl_path = tmp_path / "silver.jsonl"
    jsonl_path.write_text(
        '{"user_input": "Có id sẵn?", "sample_id": "id-tu-dataset", "persona_name": "p1"}\n'
        '{"user_input": "Thiếu id?", "persona_name": "p2"}\n',
        encoding="utf-8",
    )

    run(str(jsonl_path), top_k=5)

    tags = {(k, v) for _tid, k, v in fake.trace_tags if k == "sample_id"}
    # Dòng 1: giữ nguyên id từ dataset; dòng 2: dẫn xuất deterministic từ identity.
    assert ("sample_id", "id-tu-dataset") in tags
    assert ("sample_id", sample_id("Thiếu id?", "p2")) in tags
