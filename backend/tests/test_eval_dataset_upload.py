"""Test direct dataset upload (FR-16, rev 3) — offline, fake mlflow.genai.datasets qua sys.modules."""
import sys
import types

from eval.dataset_upload import UploadResult, build_records, upload


class _FakeMlflowException(Exception):
    pass


class _FakeDataset:
    def __init__(self, name):
        self.name = name
        self.merge_calls: list[list[dict]] = []

    def merge_records(self, records):
        self.merge_calls.append(records)


class _FakeDatasetStore:
    """Giả lập backend MLflow datasets: create-or-get + merge_records, ghi lại mọi call."""

    def __init__(self):
        self.datasets: dict[str, _FakeDataset] = {}
        self.get_calls: list[str] = []
        self.create_calls: list[str] = []

    def get_dataset(self, *, name):
        self.get_calls.append(name)
        if name not in self.datasets:
            raise _FakeMlflowException(f"dataset không tồn tại: {name}")
        return self.datasets[name]

    def create_dataset(self, *, name):
        self.create_calls.append(name)
        ds = _FakeDataset(name)
        self.datasets[name] = ds
        return ds


def _install_fake_mlflow(monkeypatch, store):
    exceptions_mod = types.ModuleType("mlflow.exceptions")
    exceptions_mod.MlflowException = _FakeMlflowException
    datasets_mod = types.ModuleType("mlflow.genai.datasets")
    datasets_mod.get_dataset = store.get_dataset
    datasets_mod.create_dataset = store.create_dataset
    monkeypatch.setitem(sys.modules, "mlflow.exceptions", exceptions_mod)
    monkeypatch.setitem(sys.modules, "mlflow.genai.datasets", datasets_mod)


SAMPLES = [
    {
        "user_input": "Phí thường niên bao nhiêu?",
        "reference": "Phí thường niên là 500.000đ",
        "reference_contexts": ["Điều 3: phí thường niên 500.000đ"],
        "synthesizer_name": "single_hop_specific_query_synthesizer",
        "persona_name": "Khách hàng cá nhân",
    },
    {
        "user_input": "Lãi suất trả chậm là bao nhiêu?",
        "reference": "Lãi suất trả chậm là 20%/năm",
        "reference_contexts": ["Điều 5: lãi suất trả chậm 20%/năm"],
        "synthesizer_name": "multi_hop_abstract_query_synthesizer",
        "persona_name": "Khách hàng doanh nghiệp",
    },
]


def test_build_records_shape():
    records = build_records(SAMPLES)
    assert records == [
        {
            "inputs": {"question": "Phí thường niên bao nhiêu?", "persona_name": "Khách hàng cá nhân"},
            "expectations": {
                "expected_response": "Phí thường niên là 500.000đ",
                "reference_contexts": ["Điều 3: phí thường niên 500.000đ"],
            },
        },
        {
            "inputs": {"question": "Lãi suất trả chậm là bao nhiêu?", "persona_name": "Khách hàng doanh nghiệp"},
            "expectations": {
                "expected_response": "Lãi suất trả chậm là 20%/năm",
                "reference_contexts": ["Điều 5: lãi suất trả chậm 20%/năm"],
            },
        },
    ]


def test_generate_uploads_dataset_and_jsonl(monkeypatch):
    store = _FakeDatasetStore()
    _install_fake_mlflow(monkeypatch, store)

    result = upload("d1", SAMPLES)

    assert isinstance(result, UploadResult)
    assert result.dataset_name == "d1"
    assert store.create_calls == ["d1"]
    assert len(store.datasets["d1"].merge_calls) == 1
    assert store.datasets["d1"].merge_calls[0] == build_records(SAMPLES)
    assert result.jsonl.count("\n") == 1  # 2 record -> 1 dấu xuống dòng nối


def test_rerun_merges_identical_records(monkeypatch):
    store = _FakeDatasetStore()
    _install_fake_mlflow(monkeypatch, store)

    upload("d1", SAMPLES)
    upload("d1", SAMPLES)

    # Lần 2: dataset đã tồn tại -> get_dataset trả về, không create_dataset lại.
    assert store.create_calls == ["d1"]
    assert store.get_calls == ["d1", "d1"]
    merge_calls = store.datasets["d1"].merge_calls
    assert len(merge_calls) == 2
    assert merge_calls[0] == merge_calls[1]
