"""Registry kỹ thuật RAG cho eval (FR-17, rev 3): mọi biến thể RAG (trivial hiện tại; agentic,
agentic-kg-vector sau này) đứng sau MỘT interface `(question, top_k) -> (response,
retrieved_contexts)` để `judge`/runner không cần biết chi tiết implementation — thêm biến thể
mới chỉ là thêm 1 entry vào `TECHNIQUES`, không đổi dataset/judge.

Import nhẹ — module này KHÔNG được kéo ragas/mlflow (NFR-1/2); `qa_service` là dep backend
bình thường nên import thẳng là an toàn.
"""
from __future__ import annotations

from typing import Callable

from app.services import qa_service

TechniqueFn = Callable[[str, int], tuple[str, list[str]]]


def _trivial(question: str, top_k: int) -> tuple[str, list[str]]:
    """Kỹ thuật RAG mặc định v1: bọc `qa_service.answer` (đúng flow playground, FR-11)."""
    response, citations = qa_service.answer(question, top_k)
    return response, [c.final_content for c in citations]


TECHNIQUES: dict[str, TechniqueFn] = {
    "trivial": _trivial,
}


def resolve(name: str) -> TechniqueFn:
    """Tra registry theo tên; tên không tồn tại -> ValueError liệt kê tên đã đăng ký."""
    try:
        return TECHNIQUES[name]
    except KeyError:
        registered = ", ".join(sorted(TECHNIQUES))
        raise ValueError(
            f"Kỹ thuật RAG không xác định: '{name}'. Đã đăng ký: {registered}"
        ) from None
