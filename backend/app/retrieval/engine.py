"""Outer graph của Retrieval Engine — AGENTIC PLANNING (plan → gather → assess → loop).

Thay vì phó mặc cho một free ReAct loop tự quyết khi nào dừng (rủi ro với domain nghiệp vụ
ngân hàng/bảo hiểm cần độ đầy đủ), engine dùng planner–executor–verifier có kiểm soát:

  normalize → rewrite → plan → gather → assess → (assess: gather nếu còn thiếu & còn budget
                                                  | finalize nếu đủ/hết budget) → finalize → END

- plan   : tách câu hỏi thành các SUB-GOAL (mỗi thực thể × mỗi khía cạnh), có tham chiếu catalog.
- gather : với mỗi sub-goal còn thiếu, retrieve chunk (broaden truy vấn ở vòng sau) — provenance
           gắn theo từng sub-goal.
- assess : LLM chấm coverage từng sub-goal (đủ bằng chứng chưa) — bước verify bắt buộc.
- loop   : còn sub-goal thiếu và hops < RETRIEVAL_MAX_HOPS -> gather lại; ngược lại finalize.
- finalize: gom bằng chứng GIỮ COVERAGE từng sub-goal (không cắt top_k toàn cục làm đói facet).

Trả về citations (có provenance) + trace + coverage từng sub-goal (để nêu rõ còn thiếu gì).
"""
from __future__ import annotations

import logging
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import settings
from app.retrieval import nodes
from app.retrieval.tools import query_catalog, query_vector_store
from app.schemas.playground import Citation

logger = logging.getLogger("retrieval.engine")


class EngineState(TypedDict):
    question: str
    top_k: int
    normalized_question: str
    rewritten_question: str
    subgoals: list[dict]   # {id, description, query, satisfied, note, evidence: list[chunk-dict]}
    hops: int
    tool_calls: list[dict]
    citations: list[Citation]


# ------------------------------------------------------------------ helpers

def _search(query: str, k: int) -> list[dict]:
    """Retrieval 1 truy vấn. Hybrid (dense + BM25 fuse) nếu bật; ngược lại dense-only.

    Lấy dư (fetch) từ mỗi nguồn rồi fuse xuống k để tăng recall (đặc biệt ca keyword/số).
    """
    fetch = max(2 * k, 10)
    dense = query_vector_store.invoke({"query": query, "top_k": fetch})
    if not settings.retrieval_enable_hybrid:
        return dense[:k]
    from app.retrieval import hybrid

    bm25 = hybrid.bm25_search(query, fetch)
    return hybrid.fuse(dense, bm25, k, settings.retrieval_hybrid_alpha)


def _catalog_outline(query: str, k: int) -> str:
    try:
        cats = query_catalog.invoke({"query": query, "top_k": k})
    except Exception as exc:  # noqa: BLE001 — catalog optional, không chặn plan
        logger.warning("[plan] lấy catalog lỗi: %s", exc)
        return ""
    return "\n\n".join(c.get("outline", "") for c in cats if c.get("outline"))


def _merge_evidence(existing: list[dict], hits: list[dict]) -> list[dict]:
    seen = {e.get("chunk_id") for e in existing}
    out = list(existing)
    for h in hits:
        cid = h.get("chunk_id")
        if cid and cid not in seen:
            out.append(h)
            seen.add(cid)
    return out


# ------------------------------------------------------------------ nodes

def _normalize_step(state: EngineState) -> dict:
    return {"normalized_question": nodes.normalize(state["question"])}


def _rewrite_step(state: EngineState) -> dict:
    return {"rewritten_question": nodes.rewrite(state["normalized_question"])}


def _plan_step(state: EngineState) -> dict:
    q = state["rewritten_question"]
    outline = _catalog_outline(q, state["top_k"])
    subgoals = nodes.plan(q, outline)
    for sg in subgoals:
        sg.setdefault("evidence", [])
        sg.setdefault("satisfied", False)
        sg.setdefault("note", "")
    return {"subgoals": subgoals, "hops": 0, "tool_calls": []}


def _gather_step(state: EngineState) -> dict:
    subgoals = state["subgoals"]
    hops = state["hops"]
    trace = list(state["tool_calls"])
    k = settings.retrieval_per_subgoal_k

    for sg in subgoals:
        if sg.get("satisfied"):
            continue
        # vòng sau: broaden bằng chính "note" của assess (nói còn thiếu gì) để nhắm đúng chỗ hổng
        query = sg["query"] if hops == 0 else f"{sg['query']} {sg.get('note') or 'chi tiết cụ thể'}".strip()
        hits = _search(query, k)
        sg["evidence"] = _merge_evidence(sg.get("evidence", []), hits)
        trace.append({"tool": "query_vector_store", "args": {"query": query, "subgoal": sg["id"]}, "hit_count": len(hits)})

    return {"subgoals": subgoals, "hops": hops + 1, "tool_calls": trace}


def _assess_step(state: EngineState) -> dict:
    return {"subgoals": nodes.assess(state["subgoals"])}


def _route_after_assess(state: EngineState) -> str:
    all_satisfied = all(sg.get("satisfied") for sg in state["subgoals"])
    if all_satisfied or state["hops"] >= settings.retrieval_max_hops:
        return "finalize"
    return "gather"


def _finalize_step(state: EngineState) -> dict:
    """Gom bằng chứng giữ coverage: mỗi sub-goal góp top-N theo score, union dedup, sort."""
    subgoals = state["subgoals"]
    per = max(2, state["top_k"])  # tối thiểu mỗi sub-goal đóng góp tới `per` đoạn tốt nhất
    picked: dict[str, dict] = {}
    for sg in subgoals:
        ev = sorted(sg.get("evidence", []), key=lambda e: e.get("score", 0.0), reverse=True)[:per]
        for e in ev:
            cid = e.get("chunk_id") or f"{e.get('document_id')}:{e.get('chunk_index')}"
            if cid not in picked:
                picked[cid] = e
    ordered = sorted(picked.values(), key=lambda e: e.get("score", 0.0), reverse=True)
    citations = [
        Citation(
            document_id=e.get("document_id", ""),
            title=e.get("title", ""),
            chunk_index=e.get("chunk_index", -1),
            score=e.get("score", 0.0),
            final_content=e.get("final_content", ""),
        )
        for e in ordered
    ]
    logger.info(
        "[finalize] sub-goals=%s satisfied=%s citations=%s",
        len(subgoals), sum(1 for s in subgoals if s.get("satisfied")), len(citations),
    )
    return {"citations": citations}


# ------------------------------------------------------------------ graph

def build_graph():
    graph = StateGraph(EngineState)
    graph.add_node("normalize", _normalize_step)
    graph.add_node("rewrite", _rewrite_step)
    graph.add_node("plan", _plan_step)
    graph.add_node("gather", _gather_step)
    graph.add_node("assess", _assess_step)
    graph.add_node("finalize", _finalize_step)
    graph.add_edge(START, "normalize")
    graph.add_edge("normalize", "rewrite")
    graph.add_edge("rewrite", "plan")
    graph.add_edge("plan", "gather")
    graph.add_edge("gather", "assess")
    graph.add_conditional_edges("assess", _route_after_assess, {"gather": "gather", "finalize": "finalize"})
    graph.add_edge("finalize", END)
    return graph.compile()


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = build_graph()
    return _engine


def _subgoal_coverage(subgoals: list[dict]) -> list[dict]:
    return [
        {
            "description": sg.get("description", ""),
            "query": sg.get("query", ""),
            "satisfied": bool(sg.get("satisfied")),
            "note": sg.get("note", ""),
            "evidence_count": len(sg.get("evidence", [])),
        }
        for sg in subgoals
    ]


def retrieve(question: str, top_k: int = 5) -> dict:
    """Chạy planner–executor–verifier. Trả citations + trace + coverage từng sub-goal."""
    result = _get_engine().invoke(
        {"question": question, "top_k": top_k, "subgoals": [], "hops": 0, "tool_calls": [], "citations": []},
        config={"recursion_limit": 2 * settings.retrieval_max_hops + 6},
    )
    return {
        "citations": result["citations"],
        "normalized_question": result["normalized_question"],
        "rewritten_question": result["rewritten_question"],
        "tool_calls": result["tool_calls"],
        "subgoals": _subgoal_coverage(result["subgoals"]),
    }
