"""Điểm chặn DUY NHẤT cho MLflow tracing — span an toàn, no-op khi tắt/không sẵn sàng.

Ranh giới: mọi span đi qua đây; service khác chỉ gọi `tracing.span(...)`, không import
mlflow trực tiếp. Tracing là best-effort — MLflow down / init lỗi / tạo span lỗi đều
KHÔNG được làm hỏng request hay pipeline (yield span no-op thay vì raise).

Quyết định (memory observability-mlflow-otel): MLflow là backbone cho trace + experiment.
Trace ghi vào experiment RIÊNG (mlflow_trace_experiment), tách khỏi experiment eval.
"""
from __future__ import annotations

import contextlib
import logging
import os
import socket
import threading
import urllib.parse
from typing import Any, Iterator

from app.config import settings

logger = logging.getLogger("tracing")

# Span type (khớp mlflow.entities.SpanType) — dùng chuỗi để service khác khỏi import mlflow.
PARSER = "PARSER"
EMBEDDING = "EMBEDDING"
RETRIEVER = "RETRIEVER"
LLM = "LLM"
CHAIN = "CHAIN"
TASK = "TASK"

_init_lock = threading.Lock()
_initialized = False
_enabled = False


class _NoopSpan:
    """Span giả khi tracing tắt — nuốt mọi setter để call-site không cần rẽ nhánh."""

    def set_inputs(self, *a, **k) -> None: ...
    def set_outputs(self, *a, **k) -> None: ...
    def set_attribute(self, *a, **k) -> None: ...
    def set_attributes(self, *a, **k) -> None: ...


_NOOP = _NoopSpan()


def configure() -> bool:
    """Khởi tạo MLflow tracking URI + experiment MỘT LẦN (idempotent, thread-safe).

    Gọi ở startup để dời network I/O khỏi request đầu tiên; cũng được span() gọi lười.
    Trả về True nếu tracing bật & sẵn sàng. Lỗi (MLflow down/URI sai) -> tắt lặng, log warning.
    """
    global _initialized, _enabled
    if _initialized:
        return _enabled
    with _init_lock:
        if _initialized:
            return _enabled
        _initialized = True
        if not settings.tracing_enabled:
            logger.info("MLflow tracing tắt (TRACING_ENABLED=false).")
            return False
        # Probe nhanh: nếu MLflow không mở cổng, tắt tracing NGAY thay vì để set_experiment
        # dính retry/timeout dài của mlflow (có thể treo startup cả phút khi server down).
        if not _reachable(settings.mlflow_tracking_uri):
            logger.warning(
                "MLflow tracing tắt (không kết nối được %s).", settings.mlflow_tracking_uri
            )
            return False
        try:
            import mlflow

            # Giới hạn timeout HTTP để không treo lâu khi MLflow không phản hồi.
            os.environ.setdefault("MLFLOW_HTTP_REQUEST_TIMEOUT", str(int(settings.llm_timeout)))
            mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
            mlflow.set_experiment(settings.mlflow_trace_experiment)
            _enabled = True
            logger.info(
                "MLflow tracing bật -> %s (experiment=%s).",
                settings.mlflow_tracking_uri,
                settings.mlflow_trace_experiment,
            )
        except Exception as exc:  # noqa: BLE001 — init lỗi không được chặn app
            logger.warning("MLflow tracing tắt (init lỗi): %s", exc)
            _enabled = False
        return _enabled


def _reachable(uri: str, timeout: float = 3.0) -> bool:
    """TCP probe nhanh host:port của tracking URI (http/https). URI local (file://, db) -> True."""
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme not in ("http", "https"):
        return True
    host = parsed.hostname
    if not host:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@contextlib.contextmanager
def span(
    name: str,
    *,
    span_type: str | None = None,
    inputs: dict | None = None,
    attributes: dict | None = None,
) -> Iterator[Any]:
    """Mở 1 span MLflow (tự nest dưới span đang active). No-op nếu tracing tắt/lỗi.

    Body raise -> span được đánh dấu ERROR rồi exception propagate như thường (không nuốt lỗi
    nghiệp vụ). Chỉ lỗi CỦA tracing mới bị nuốt.
    """
    if not configure():
        yield _NOOP
        return

    import mlflow

    try:
        cm = mlflow.start_span(name=name, span_type=span_type or "UNKNOWN")
    except Exception as exc:  # noqa: BLE001 — tạo span lỗi -> no-op, không chặn request
        logger.debug("Không mở được span %s (bỏ qua): %s", name, exc)
        yield _NOOP
        return

    with cm as s:
        _safe_set(s, inputs, attributes)
        yield s


def _safe_set(s: Any, inputs: dict | None, attributes: dict | None) -> None:
    try:
        if inputs is not None:
            s.set_inputs(inputs)
        if attributes:
            s.set_attributes(attributes)
    except Exception as exc:  # noqa: BLE001 — set metadata lỗi không được chặn request
        logger.debug("set span metadata lỗi (bỏ qua): %s", exc)


def set_outputs(s: Any, outputs: dict) -> None:
    """Gán outputs cho span an toàn (nuốt lỗi tracing)."""
    try:
        s.set_outputs(outputs)
    except Exception as exc:  # noqa: BLE001
        logger.debug("set span outputs lỗi (bỏ qua): %s", exc)
