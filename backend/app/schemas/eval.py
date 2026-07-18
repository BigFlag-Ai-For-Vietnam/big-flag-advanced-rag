"""Schema response cho API eval chỉ-đọc (FR-13)."""
from pydantic import BaseModel


class DatasetInfo(BaseModel):
    name: str
    num_records: int
    last_updated: int | None = None   # epoch ms từ MLflow


class RunInfo(BaseModel):
    run_id: str
    run_name: str | None = None
    status: str
    start_time: int | None = None
    dataset: str | None = None
    metrics: dict[str, float] = {}
