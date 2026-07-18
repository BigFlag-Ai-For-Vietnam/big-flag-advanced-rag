"""Test API chỉ-đọc /api/eval (FR-13) — offline, stub eval_mlflow_client."""
from fastapi.testclient import TestClient

from app.main import app
from app.services import eval_mlflow_client


def test_list_datasets_and_runs(monkeypatch):
    monkeypatch.setattr(
        eval_mlflow_client, "list_datasets",
        lambda: [{"name": "golden-d1", "num_records": 12, "last_updated": 1700000000000}],
    )
    monkeypatch.setattr(
        eval_mlflow_client, "list_runs",
        lambda: [{"run_id": "r1", "run_name": "run-a", "status": "FINISHED",
                  "start_time": 1700000000000, "dataset": "golden-d1",
                  "metrics": {"faithfulness": 0.9}}],
    )
    client = TestClient(app)
    ds = client.get("/api/eval/datasets")
    assert ds.status_code == 200 and ds.json()[0]["name"] == "golden-d1"
    runs = client.get("/api/eval/runs")
    assert runs.status_code == 200 and runs.json()[0]["metrics"]["faithfulness"] == 0.9


def test_mlflow_unreachable_503(monkeypatch):
    def _boom():
        raise eval_mlflow_client.MLflowUnreachable("connection refused")

    monkeypatch.setattr(eval_mlflow_client, "list_datasets", _boom)
    monkeypatch.setattr(eval_mlflow_client, "list_runs", _boom)
    client = TestClient(app)
    assert client.get("/api/eval/datasets").status_code == 503
    r = client.get("/api/eval/runs")
    assert r.status_code == 503 and "MLflow" in r.json()["detail"]
