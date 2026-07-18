"""Node deterministic của outer graph: normalize/rewrite chạy trước react subgraph
(đúng 1 lần, không loop), rerank chạy sau (đúng 1 lần, luôn chạy — không phải tool
cho LLM tự chọn gọi).

Gọi llm_client.chat() trực tiếp, không qua BaseChatModel — các hàm ở đây không cần
interface LangChain vì không phải một phần của react subgraph (không tool-calling).

Mỗi hàm tự check flag bật/tắt của mình (RETRIEVAL_ENABLE_*) và log input/output để
quan sát ảnh hưởng của từng bước.
"""
from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import AIMessage, ToolMessage

from app.config import settings
from app.schemas.playground import Citation
from app.services import llm_client

logger = logging.getLogger("retrieval.nodes")

REWRITE_PROMPT = (
    "Bạn hỗ trợ chuẩn hoá câu hỏi cho hệ thống tìm kiếm tài liệu ngân hàng (điều khoản, "
    "quyền lợi, phí, sản phẩm/dịch vụ). Nếu câu hỏi thiếu tên sản phẩm/dịch vụ cụ thể, "
    "giữ nguyên — KHÔNG bịa tên sản phẩm không có trong câu hỏi gốc. Viết lại câu hỏi rõ "
    "ràng, đầy đủ ý hơn, phù hợp để tìm kiếm ngữ nghĩa. CHỈ trả về câu hỏi đã viết lại, "
    "không giải thích gì thêm."
)


def normalize(question: str) -> str:
    """Dọn dẹp câu hỏi (strip/whitespace) — thuần Python, không gọi LLM."""
    if not settings.retrieval_enable_normalize:
        logger.info("[normalize] tắt (RETRIEVAL_ENABLE_NORMALIZE=false) — passthrough input=%r", question)
        return question
    result = re.sub(r"\s+", " ", question).strip()
    logger.info("[normalize] input=%r output=%r", question, result)
    return result


def rewrite(question: str) -> str:
    """1 lần gọi LLM để làm rõ/chuẩn hoá câu hỏi trước khi vào react subgraph."""
    if not settings.retrieval_enable_rewrite:
        logger.info("[rewrite] tắt (RETRIEVAL_ENABLE_REWRITE=false) — passthrough input=%r", question)
        return question
    result = llm_client.chat(
        [
            {"role": "system", "content": REWRITE_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.0,
        max_tokens=200,
        tag="retrieval_rewrite",
        max_retries=settings.interactive_llm_max_retries,
    ).strip() or question
    logger.info("[rewrite] input=%r output=%r", question, result)
    return result


PLAN_PROMPT = (
    "Bạn là bộ LẬP KẾ HOẠCH truy hồi cho hệ thống hỏi–đáp tài liệu ngân hàng/bảo hiểm. "
    "Tách câu hỏi thành các SUB-GOAL cụ thể — mỗi sub-goal là một mẩu thông tin độc lập cần "
    "tìm để trả lời ĐẦY ĐỦ. Nguyên tắc: mỗi THỰC THỂ/sản phẩm × mỗi KHÍA CẠNH là 1 sub-goal "
    "riêng.\n"
    "Ví dụ:\n"
    "- 'So sánh quyền lợi bảo hiểm A và B' -> 2 sub-goal: 'quyền lợi bảo hiểm A', 'quyền lợi "
    "bảo hiểm B'.\n"
    "- 'Điều kiện loại trừ của bảo hiểm A và mức phí của nó' -> 2 sub-goal: 'điều kiện loại "
    "trừ bảo hiểm A', 'mức phí bảo hiểm A'.\n"
    "Nếu có CATALOG (mục lục tài liệu), dùng nó để tách cho đúng và đủ mục. Câu hỏi đơn (1 "
    "thực thể, 1 khía cạnh) thì chỉ cần 1 sub-goal. Mỗi sub-goal gồm: description (mục tiêu "
    "ngắn) + query (câu truy vấn tiếng Việt rõ ràng để search KB).\n"
    "CHỈ trả về JSON đúng schema, không giải thích: "
    '{"subgoals":[{"description":"...","query":"..."}]}'
)

ASSESS_PROMPT = (
    "Bạn là bộ KIỂM TRA ĐỘ ĐẦY ĐỦ bằng chứng cho retrieval. Với mỗi SUB-GOAL và các đoạn "
    "bằng chứng tìm được, quyết định có nên TÌM THÊM không.\n"
    "Có 2 LOẠI bằng chứng, dùng khác nhau: "
    "(1) BẰNG CHỨNG VĂN BẢN (chunk) — trích y nguyên từ tài liệu, dùng để trả lời trực tiếp; "
    "(2) BẰNG CHỨNG ĐỒ THỊ (graph) — quan hệ/thực thể giữa các văn bản (căn cứ/thay thế/tham "
    "chiếu/ưu tiên hơn) hoặc bundle nhiều giá trị cho cùng 1 khái niệm kèm văn bản nguồn — "
    "KHÔNG phải trích dẫn nguyên văn, chỉ dùng để PHÁT HIỆN quan hệ/xung đột/thay thế giữa "
    "nhiều văn bản (vd 2 văn bản cùng quy định 1 giá trị khác nhau -> có thể xung đột hoặc 1 "
    "văn bản đã thay thế văn bản kia).\n"
    "- satisfied=true nếu ĐÃ CÓ ĐỦ 1 trong 2 loại bằng chứng để trả lời phần lớn sub-goal "
    "(không cần hoàn hảo, không cần mọi chi tiết) — kể cả khi thông tin nằm trong bảng/con số "
    "hoặc chỉ có bằng chứng đồ thị (câu hỏi về quan hệ/so sánh giữa văn bản).\n"
    "- satisfied=false CHỈ khi CẢ 2 loại đều hầu như KHÔNG liên quan hoặc thiếu hẳn thông tin "
    "cốt lõi. Khi false, note nêu ngắn gọn còn thiếu gì để lần tìm sau nhắm đúng.\n"
    "Ưu tiên dừng (true) khi đã đủ dùng — tránh tìm lặp vô ích.\n"
    "NGOẠI LỆ (xét TRƯỚC quy tắc ưu tiên dừng): nếu BẰNG CHỨNG ĐỒ THỊ cho thấy có văn bản "
    "khác được THAY_THE / UU_TIEN_HON / CAN_CU / THAM_CHIEU tới sub-goal này, MÀ nội dung "
    "của văn bản đó KHÔNG xuất hiện trong bằng chứng văn bản, thì đặt satisfied=false — kể "
    "cả khi bằng chứng văn bản hiện có trông đã đủ. Lý do: trả lời bằng điều khoản đã bị "
    "thay thế/chưa xét văn bản căn cứ là SAI, không phải thiếu.\n"
    "Khi rơi vào ngoại lệ này, note PHẢI nêu ĐÍCH DANH tên văn bản còn thiếu, viết dưới dạng "
    "CỤM TỪ TÌM KIẾM ngắn (tên văn bản + khía cạnh cần tra), KHÔNG viết câu giải thích dài — "
    "note sẽ được ghép thẳng vào truy vấn tìm kiếm ở vòng sau.\n"
    'Ví dụ note đúng: "Thông tư 22/2019/TT-NHNN tỷ lệ an toàn vốn"; '
    'note SAI: "cần tìm thêm nội dung của văn bản đã thay thế điều khoản này".\n'
    "CHỈ trả về JSON đúng schema, không giải thích: "
    '{"results":[{"id":"<id>","satisfied":true,"note":"..."}]}'
)


def _parse_json_obj(raw: str) -> dict:
    """Parse JSON object từ output LLM (bỏ code fence, tìm object đầu tiên)."""
    text = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {}
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}


def plan(question: str, catalog_outline: str = "") -> list[dict]:
    """Tách câu hỏi thành sub-goal. Tắt planning -> 1 sub-goal = cả câu hỏi.

    Trả về list [{id, description, query}]. Robust: lỗi/rỗng -> fallback 1 sub-goal.
    """
    single = [{"id": "g1", "description": question, "query": question}]
    if not settings.retrieval_enable_planning:
        logger.info("[plan] tắt (RETRIEVAL_ENABLE_PLANNING=false) — 1 sub-goal = cả câu hỏi")
        return single

    user = f"CÂU HỎI: {question}"
    if catalog_outline.strip():
        user += f"\n\nCATALOG (mục lục tài liệu liên quan):\n{catalog_outline}"
    user += f"\n\nTách tối đa {settings.retrieval_plan_max_subgoals} sub-goal."
    try:
        raw = llm_client.chat(
            [{"role": "system", "content": PLAN_PROMPT}, {"role": "user", "content": user}],
            temperature=0.0, max_tokens=600, tag="retrieval_plan",
            max_retries=settings.interactive_llm_max_retries,
        )
        items = _parse_json_obj(raw).get("subgoals", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("[plan] lỗi, fallback 1 sub-goal: %s", exc)
        return single

    subgoals: list[dict] = []
    for i, it in enumerate(items[: settings.retrieval_plan_max_subgoals]):
        if not isinstance(it, dict):
            continue
        desc = str(it.get("description", "")).strip()
        query = str(it.get("query", "")).strip() or desc
        if not query:
            continue
        subgoals.append({"id": f"g{i + 1}", "description": desc or query, "query": query})
    if not subgoals:
        return single
    logger.info("[plan] %s sub-goal: %s", len(subgoals), [s["query"] for s in subgoals])
    return subgoals


def _evidence_snippet(chunk: dict, limit: int = 500) -> str:
    txt = (chunk.get("final_content") or "").strip().replace("\n", " ")
    return txt[:limit]


def _graph_fact_snippet(fact: dict) -> str:
    props = fact.get("properties") or {}
    prop_txt = f" ({props})" if props else ""
    source_doc = fact.get("source_document_title") or ""
    return (
        f"{fact.get('source_entity', '')} --{fact.get('relation', '')}--> "
        f"{fact.get('target_entity', '')}{prop_txt}"
        + (f" [nguồn: {source_doc}]" if source_doc else "")
    )


def assess(subgoals: list[dict]) -> list[dict]:
    """Đánh giá mỗi sub-goal đã đủ bằng chứng chưa (LLM judge, 1 call).

    Cập nhật tại chỗ 'satisfied' + 'note' cho từng sub-goal. Lỗi -> heuristic theo score.
    """
    def _heuristic():
        for sg in subgoals:
            strong = any(
                (e.get("score", 0.0) >= settings.retrieval_coverage_min_score)
                for e in sg.get("evidence", [])
            )
            sg["satisfied"] = bool(strong)
            sg["note"] = "" if strong else "Chưa có đoạn đủ liên quan."
        return subgoals

    blocks = []
    for sg in subgoals:
        ev = sg.get("evidence", [])[:6]
        ev_txt = "\n".join(f"  - {_evidence_snippet(e)}" for e in ev) or "  (chưa có bằng chứng)"
        graph_ev = sg.get("graph_evidence", [])[:6]
        graph_txt = "\n".join(f"  - {_graph_fact_snippet(f)}" for f in graph_ev) or "  (chưa có bằng chứng đồ thị)"
        blocks.append(
            f"[{sg['id']}] {sg['description']}\n"
            f"Bằng chứng văn bản:\n{ev_txt}\n"
            f"Bằng chứng đồ thị:\n{graph_txt}"
        )
    user = "\n\n".join(blocks)
    try:
        raw = llm_client.chat(
            [{"role": "system", "content": ASSESS_PROMPT}, {"role": "user", "content": user}],
            temperature=0.0, max_tokens=500, tag="retrieval_assess",
            max_retries=settings.interactive_llm_max_retries,
        )
        results = {str(r.get("id")): r for r in _parse_json_obj(raw).get("results", []) if isinstance(r, dict)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[assess] lỗi, fallback heuristic theo score: %s", exc)
        return _heuristic()

    for sg in subgoals:
        r = results.get(sg["id"])
        if r is None:
            sg["satisfied"] = bool(sg.get("evidence"))
            sg["note"] = "" if sg.get("evidence") else "Không có bằng chứng."
        else:
            sg["satisfied"] = bool(r.get("satisfied"))
            sg["note"] = str(r.get("note", "")).strip()
    logger.info("[assess] coverage=%s", {sg["id"]: sg["satisfied"] for sg in subgoals})
    return subgoals


def _parse_tool_message(msg: ToolMessage) -> list[dict]:
    content = msg.content
    if not isinstance(content, str):
        return content if isinstance(content, list) else []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def build_trace(messages: list) -> list[dict]:
    """Trace các lần react subgraph gọi tool: tool name, args, số hit trả về.

    Ghép AIMessage.tool_calls (tool nào, args gì) với ToolMessage tương ứng (theo
    tool_call_id) để biết mỗi lần gọi trả về bao nhiêu hit — phục vụ debug UI (MCP
    Playground) chứ không dùng để tính citations (đó là việc của rerank()).
    """
    tool_call_meta: dict[str, dict] = {}
    for msg in messages:
        if isinstance(msg, AIMessage):
            for tc in msg.tool_calls or []:
                tool_call_meta[tc["id"]] = {"tool": tc["name"], "args": tc["args"]}

    trace: list[dict] = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.tool_call_id in tool_call_meta:
            meta = tool_call_meta[msg.tool_call_id]
            hits = _parse_tool_message(msg)
            trace.append({"tool": meta["tool"], "args": meta["args"], "hit_count": len(hits)})
    return trace


def rerank(messages: list, top_k: int) -> list[Citation]:
    """Gom kết quả mọi lần gọi tool trong react subgraph, dedupe, sort, cắt top_k.

    Luôn chạy đúng 1 lần sau khi react subgraph dừng — không phải tool cho LLM tự
    quyết định có gọi hay không (rerank là bước lọc bắt buộc, không phải tuỳ chọn).
    """
    candidates: list[dict] = []
    for msg in messages:
        if isinstance(msg, ToolMessage):
            for item in _parse_tool_message(msg):
                # chỉ hit dạng chunk (có chunk_id) mới thành citation; kết quả query_catalog
                # (mục lục, không có chunk_id/final_content) chỉ để agent tham khảo, không trích.
                if isinstance(item, dict) and item.get("chunk_id"):
                    candidates.append(item)

    deduped: dict[str, dict] = {}
    for c in candidates:
        key = c.get("chunk_id") or f"{c.get('document_id')}:{c.get('chunk_index')}"
        if key not in deduped:
            deduped[key] = c
    ordered = list(deduped.values())

    if settings.retrieval_enable_rerank:
        ordered.sort(key=lambda c: c.get("score", 0.0), reverse=True)
    else:
        logger.info("[rerank] tắt (RETRIEVAL_ENABLE_RERANK=false) — chỉ dedupe, giữ thứ tự xuất hiện")

    top = ordered[:top_k]
    logger.info(
        "[rerank] candidates=%s deduped=%s output=%s chunk_ids=%s",
        len(candidates),
        len(ordered),
        len(top),
        [c.get("chunk_id") for c in top],
    )
    return [
        Citation(
            document_id=c.get("document_id", ""),
            title=c.get("title", ""),
            chunk_index=c.get("chunk_index", -1),
            score=c.get("score", 0.0),
            final_content=c.get("final_content", ""),
        )
        for c in top
    ]
