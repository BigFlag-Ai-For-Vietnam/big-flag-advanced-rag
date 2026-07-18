"""Breakdown metric theo synthesizer_name (tier) và persona_name + log metadata run cho
`judge` (FR-12, rev 3) — khôi phục khả năng breakdown đã mất khi module logging thủ công
(T15) bị xóa trong lần pivot sang `mlflow.genai.evaluate()` native. Native path đã tự log
điểm tổng hợp + trace; module này chỉ log thêm phần nó KHÔNG log: tag `technique` + slice
theo tier/persona.

`breakdowns()` là hàm thuần (không import mlflow/ragas) — dễ test offline; chỉ
`log_run_metadata()` import mlflow (lazy, trong hàm).
"""
from __future__ import annotations

import math

_ROW_KEYS = {"synthesizer_name", "persona_name"}


def _mean_ignore_nan(values: list) -> float | None:
    """Mean bỏ qua None/NaN; toàn None/NaN -> None (không log 0.0 giả)."""
    clean = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    if not clean:
        return None
    return sum(clean) / len(clean)


def breakdowns(rows: list[dict]) -> dict[str, float]:
    """rows: mỗi dict có `synthesizer_name`, `persona_name`, + cột điểm số (tên metric -> float).
    Trả về `{"<metric>/<synthesizer_name>": mean, "<metric>/persona/<persona_name>": mean, ...}`
    — NaN-mean (bỏ qua NaN khi tính trung bình); slice toàn NaN không xuất hiện trong kết quả."""
    metric_names = sorted({k for row in rows for k in row if k not in _ROW_KEYS})

    by_synth: dict[str, list[dict]] = {}
    by_persona: dict[str, list[dict]] = {}
    for row in rows:
        by_synth.setdefault(row.get("synthesizer_name"), []).append(row)
        by_persona.setdefault(row.get("persona_name"), []).append(row)

    result: dict[str, float] = {}
    for metric in metric_names:
        for synth_name, synth_rows in by_synth.items():
            if synth_name is None:
                continue
            mean = _mean_ignore_nan([r.get(metric) for r in synth_rows])
            if mean is not None:
                result[f"{metric}/{synth_name}"] = mean
        for persona_name, persona_rows in by_persona.items():
            if persona_name is None:
                continue
            mean = _mean_ignore_nan([r.get(metric) for r in persona_rows])
            if mean is not None:
                result[f"{metric}/persona/{persona_name}"] = mean

    return result


def log_run_metadata(
    technique: str, params: dict, breakdown_metrics: dict[str, float], *, run_id: str | None = None,
) -> None:
    """Log params + tag `technique` + breakdown metrics. `run_id` (mặc định None): run của
    chính `mlflow.genai.evaluate()` — cần resume qua `start_run(run_id=...)` để log đúng chỗ
    (evaluate() tự đóng run của nó, không còn active khi hàm này chạy). Không truyền -> log
    vào run đang active (dùng trong test/offline)."""
    import mlflow

    if run_id is not None:
        with mlflow.start_run(run_id=run_id):
            _log(mlflow, technique, params, breakdown_metrics)
        return
    _log(mlflow, technique, params, breakdown_metrics)


def _log(mlflow_mod, technique: str, params: dict, breakdown_metrics: dict[str, float]) -> None:
    mlflow_mod.log_params(params)
    mlflow_mod.set_tag("technique", technique)
    if breakdown_metrics:
        mlflow_mod.log_metrics(breakdown_metrics)
