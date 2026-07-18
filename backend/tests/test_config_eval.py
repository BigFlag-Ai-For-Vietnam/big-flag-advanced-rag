"""Test cấu hình eval/MLflow (FR-15) — offline, không đọc .env thật."""
from app.config import Settings

EVAL_VARS = ["MLFLOW_TRACKING_URI", "MLFLOW_EXPERIMENT", "EVAL_JUDGE_MODEL", "EVAL_MAX_WORKERS"]


def test_eval_settings_env_and_defaults(monkeypatch):
    # env override
    for var in EVAL_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("MLFLOW_TRACKING_URI", "http://x:5")
    monkeypatch.setenv("EVAL_MAX_WORKERS", "2")
    s = Settings(_env_file=None)
    assert s.mlflow_tracking_uri == "http://x:5"
    assert s.eval_max_workers == 2
    # defaults giữ nguyên cho field không set
    assert s.mlflow_experiment == "advanced-rag-eval"
    assert s.eval_judge_model == ""

    # pure defaults
    for var in EVAL_VARS:
        monkeypatch.delenv(var, raising=False)
    d = Settings(_env_file=None)
    assert d.mlflow_tracking_uri == "http://localhost:5000"
    assert d.mlflow_experiment == "advanced-rag-eval"
    assert d.eval_judge_model == ""
    assert d.eval_max_workers == 4
