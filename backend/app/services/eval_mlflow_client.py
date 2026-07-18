"""Client CHỈ-ĐỌC tới MLflow cho API eval (FR-13).

Ranh giới: router chỉ gọi list_datasets()/list_runs(). Lỗi kết nối/timeout
-> MLflowUnreachable -> router trả 503.

Quyết định T07 (spike mlflow-skinny): mlflow-skinny==3.14.0 đủ dùng — pip check sạch với
pin backend, không kéo pandas/langchain, round-trip sống xác nhận cả hai API dưới đây.
KHÔNG dùng EvaluationDataset.to_df() (cần pandas, skinny không có) — dùng to_dict()["records"].
KHÔNG dùng mlflow.search_runs() cấp module (trả DataFrame) — chỉ dùng MlflowClient.search_runs.
"""
from __future__ import annotations

import os

from app.config import settings


class MLflowUnreachable(RuntimeError):
    """MLflow không truy cập được (mạng/timeout/URI sai)."""


def _bound_request_timeout() -> None:
    """Giới hạn timeout HTTP request của mlflow-skinny theo llm_timeout — tránh treo
    lâu khi MLflow không phản hồi (mặc định mlflow tự retry nhiều lần)."""
    os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", str(int(settings.llm_timeout)))


def list_datasets() -> list[dict]:
    """[{name, num_records, last_updated}] — MLflow genai evaluation datasets."""
    import mlflow
    from mlflow.exceptions import MlflowException
    from mlflow.genai.datasets import search_datasets
    from mlflow.tracking import MlflowClient

    _bound_request_timeout()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    try:
        client = MlflowClient()
        exp = client.get_experiment_by_name(settings.mlflow_experiment)
        if exp is None:
            return []
        datasets = search_datasets(experiment_ids=[exp.experiment_id])
    except MlflowException as exc:
        raise MLflowUnreachable(str(exc)) from exc

    out = []
    for ds in datasets:
        d = ds.to_dict()
        out.append({
            "name": d["name"],
            "num_records": len(d.get("records", [])),
            "last_updated": d.get("last_update_time"),
        })
    return out


def list_runs() -> list[dict]:
    """[{run_id, run_name, status, start_time, dataset, metrics}] cho experiment eval."""
    import mlflow
    from mlflow.exceptions import MlflowException
    from mlflow.tracking import MlflowClient

    _bound_request_timeout()
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    try:
        client = MlflowClient()
        exp = client.get_experiment_by_name(settings.mlflow_experiment)
        if exp is None:
            return []
        runs = client.search_runs(experiment_ids=[exp.experiment_id], max_results=100)
    except MlflowException as exc:
        raise MLflowUnreachable(str(exc)) from exc

    out = []
    for run in runs:
        out.append({
            "run_id": run.info.run_id,
            "run_name": run.info.run_name,
            "status": run.info.status,
            "start_time": run.info.start_time,
            "dataset": run.data.params.get("dataset_name") or run.data.params.get("dataset"),
            "metrics": dict(run.data.metrics),
        })
    return out
