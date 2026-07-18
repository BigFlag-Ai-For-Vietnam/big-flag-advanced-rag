"""Test ingest silver vào MLflow (FR-6) — offline, tiêm mlflow giả qua sys.modules."""
import json
import sys
import types

from eval.silver import SilverSample, ingest_silver


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


class _FakeRun:
    def __init__(self, run_id):
        self.info = types.SimpleNamespace(run_id=run_id)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeMlflow:
    def __init__(self):
        self._trace_counter = 0
        self.traces = []          # list of tag dicts
        self.expectations = []    # list of (trace_id, name, value, source)
        self.texts = []           # list of (text, artifact_file)

    def set_tracking_uri(self, uri):
        pass

    def set_experiment(self, name):
        pass

    def start_run(self):
        return _FakeRun("run-silver-1")

    def start_span(self, name=None):
        self._trace_counter += 1
        return _FakeSpan(f"tr-{self._trace_counter}")

    def update_current_trace(self, tags=None):
        self.traces.append(tags or {})

    def log_expectation(self, *, trace_id, name, value, source=None):
        self.expectations.append((trace_id, name, value, source))

    def log_text(self, text, artifact_file):
        self.texts.append((text, artifact_file))

    def flush_trace_async_logging(self):
        pass


class _FakeAssessmentSource:
    def __init__(self, source_type, source_id="default"):
        self.source_type = source_type
        self.source_id = source_id


class _FakeAssessmentSourceType:
    LLM_JUDGE = "LLM_JUDGE"
    HUMAN = "HUMAN"


def test_traces_expectations_and_jsonl_logged(monkeypatch):
    fake = _FakeMlflow()
    entities_mod = types.ModuleType("mlflow.entities")
    entities_mod.AssessmentSource = _FakeAssessmentSource
    assessment_source_mod = types.ModuleType("mlflow.entities.assessment_source")
    assessment_source_mod.AssessmentSourceType = _FakeAssessmentSourceType

    monkeypatch.setitem(sys.modules, "mlflow", fake)
    monkeypatch.setitem(sys.modules, "mlflow.entities", entities_mod)
    monkeypatch.setitem(sys.modules, "mlflow.entities.assessment_source", assessment_source_mod)

    samples = [
        SilverSample(
            user_input="Phí thường niên là bao nhiêu?",
            reference="500.000đ",
            reference_contexts=["ctx1"],
            synthesizer_name="single_hop_specific_query_synthesizer",
            persona_name="kh_ca_nhan",
            source_document_ids=["d1"],
        ),
        SilverSample(
            user_input="Điều kiện mở thẻ?",
            reference="Đủ 18 tuổi",
            reference_contexts=["ctx2"],
            synthesizer_name="multi_hop_abstract_query_synthesizer",
            persona_name="chuyen_vien",
            source_document_ids=["d1", "d2"],
        ),
    ]

    run_id = ingest_silver(samples, dataset_name="d1")

    assert run_id == "run-silver-1"
    assert len(fake.traces) == 2
    for tags in fake.traces:
        assert tags["dataset_name"] == "d1"
        assert "synthesizer_name" in tags
        assert "persona_name" in tags
        assert "source_document_ids" in tags

    expectation_names = [e[1] for e in fake.expectations]
    assert expectation_names.count("expected_response") == 2
    assert expectation_names.count("reference_contexts") == 2

    assert len(fake.texts) == 1
    text, artifact_file = fake.texts[0]
    lines = [json.loads(line) for line in text.strip().split("\n")]
    assert len(lines) == 2
    assert {line["user_input"] for line in lines} == {"Phí thường niên là bao nhiêu?", "Điều kiện mở thẻ?"}
