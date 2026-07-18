"""Router API eval chỉ-đọc: /api/eval/datasets, /api/eval/runs (FR-13)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.eval import DatasetInfo, RunInfo
from app.services import eval_mlflow_client

router = APIRouter(prefix="/api/eval", tags=["eval"])
_MLFLOW_503 = "Không kết nối được tới MLflow. Kiểm tra MLFLOW_TRACKING_URI và trạng thái server MLflow."


@router.get("/datasets", response_model=list[DatasetInfo])
def list_datasets():
    try:
        rows = eval_mlflow_client.list_datasets()
    except eval_mlflow_client.MLflowUnreachable as exc:
        raise HTTPException(status_code=503, detail=_MLFLOW_503) from exc
    return [DatasetInfo(**r) for r in rows]


@router.get("/runs", response_model=list[RunInfo])
def list_runs():
    try:
        rows = eval_mlflow_client.list_runs()
    except eval_mlflow_client.MLflowUnreachable as exc:
        raise HTTPException(status_code=503, detail=_MLFLOW_503) from exc
    return [RunInfo(**r) for r in rows]
