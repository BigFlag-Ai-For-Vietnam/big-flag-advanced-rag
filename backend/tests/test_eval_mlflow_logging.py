"""Test judge-run logging: technique tag + tier/persona breakdowns (FR-12, rev 3) —
offline, fake mlflow module qua sys.modules."""
import math
import sys

from eval.judge_logging import breakdowns, log_run_metadata

ROWS = [
    {"synthesizer_name": "single_hop_specific_query_synthesizer", "persona_name": "P1", "faithfulness": 0.8},
    {"synthesizer_name": "single_hop_specific_query_synthesizer", "persona_name": "P2", "faithfulness": 0.6},
    {"synthesizer_name": "multi_hop_abstract_query_synthesizer", "persona_name": "P1", "faithfulness": math.nan},
    {"synthesizer_name": "multi_hop_abstract_query_synthesizer", "persona_name": "P2", "faithfulness": 0.4},
]


def test_breakdowns_nan_mean_per_synthesizer_and_persona():
    result = breakdowns(ROWS)

    assert result["faithfulness/single_hop_specific_query_synthesizer"] == 0.7  # (0.8+0.6)/2
    assert result["faithfulness/multi_hop_abstract_query_synthesizer"] == 0.4   # NaN bỏ qua
    assert result["faithfulness/persona/P1"] == 0.8   # NaN bỏ qua, chỉ còn 0.8
    assert result["faithfulness/persona/P2"] == 0.5   # (0.6+0.4)/2


def test_all_nan_slice_omitted():
    rows = [
        {"synthesizer_name": "s1", "persona_name": "p1", "faithfulness": math.nan},
        {"synthesizer_name": "s1", "persona_name": "p1", "faithfulness": math.nan},
    ]
    result = breakdowns(rows)
    assert "faithfulness/s1" not in result
    assert "faithfulness/persona/p1" not in result


class _FakeMlflow:
    def __init__(self):
        self.params = None
        self.tags = {}
        self.metrics = None

    def log_params(self, params):
        self.params = params

    def set_tag(self, key, value):
        self.tags[key] = value

    def log_metrics(self, metrics):
        self.metrics = metrics


def test_params_breakdowns_and_technique_tag(monkeypatch):
    fake = _FakeMlflow()
    monkeypatch.setitem(sys.modules, "mlflow", fake)

    breakdown_metrics = breakdowns(ROWS)
    params = {
        "eval_judge_model": "glm-model",
        "eval_top_k": 5,
        "eval_dataset": "d1",
    }
    log_run_metadata("trivial", params, breakdown_metrics)

    assert fake.params == params
    assert fake.tags["technique"] == "trivial"
    assert fake.metrics == breakdown_metrics
    assert fake.metrics["faithfulness/persona/P1"] == 0.8
