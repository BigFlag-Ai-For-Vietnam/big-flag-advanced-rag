"""Test golden promotion (FR-8) — offline, entry point mlflow được tiêm (fake)."""
from types import SimpleNamespace

from eval.promote import promote


def _assessment(name, value, source_type):
    return SimpleNamespace(name=name, value=value, source=SimpleNamespace(source_type=source_type))


def _trace(request, assessments):
    return SimpleNamespace(
        info=SimpleNamespace(assessments=assessments),
        data=SimpleNamespace(request=request),
    )


class FakeDataset:
    def __init__(self):
        self.merge_calls = []

    def merge_records(self, records):
        self.merge_calls.append(records)


def test_promote_prefers_human_expectations():
    approved_trace = _trace(
        {"question": "Phí thường niên?", "persona": "kh_ca_nhan"},
        [
            _assessment("approve", "pass", "HUMAN"),
            _assessment("expected_response", "500.000đ (LLM)", "LLM_JUDGE"),
            _assessment("expected_response", "500.000đ (SME sửa)", "HUMAN"),
            _assessment("reference_contexts", ["ctx1"], "LLM_JUDGE"),
        ],
    )
    unapproved_trace = _trace(
        {"question": "Điều kiện mở thẻ?", "persona": "kh_ca_nhan"},
        [_assessment("approve", "fail", "HUMAN")],
    )

    fake_ds = FakeDataset()

    def fake_search_traces(*, filter_string):
        return [approved_trace, unapproved_trace]

    result = promote(
        "d1",
        search_traces=fake_search_traces,
        get_or_create_dataset=lambda name: fake_ds,
    )

    assert result.dataset_name == "golden-d1"
    assert len(result.records) == 1
    record = result.records[0]
    assert record["inputs"] == {"question": "Phí thường niên?", "persona_name": "kh_ca_nhan"}
    assert record["expectations"]["expected_response"] == "500.000đ (SME sửa)"
    assert record["expectations"]["reference_contexts"] == ["ctx1"]

    assert len(fake_ds.merge_calls) == 1
    assert fake_ds.merge_calls[0] == result.records


def test_promote_rerun_merges_identical_records():
    approved_trace = _trace(
        {"question": "Phí thường niên?", "persona": "kh_ca_nhan"},
        [
            _assessment("approve", "pass", "HUMAN"),
            _assessment("expected_response", "500.000đ", "HUMAN"),
            _assessment("reference_contexts", ["ctx1"], "HUMAN"),
        ],
    )
    fake_ds = FakeDataset()

    def fake_search_traces(*, filter_string):
        return [approved_trace]

    promote("d1", search_traces=fake_search_traces, get_or_create_dataset=lambda name: fake_ds)
    promote("d1", search_traces=fake_search_traces, get_or_create_dataset=lambda name: fake_ds)

    assert len(fake_ds.merge_calls) == 2
    assert fake_ds.merge_calls[0] == fake_ds.merge_calls[1]
