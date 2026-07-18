"""Sinh CATALOG dạng "cây entities" (lean) cho tài liệu — gần tinh thần Property Graph.

Catalog = cây phân cấp các entity thuộc từng facet user chỉ định:
  {
    "tree": [
      {"name": "Các loại phí", "children": [
        {"name": "Phí gói Sung Túc", "children": [
          {"name": "Phí gói Sung Túc hằng năm", "children": []},
          {"name": "Phí gói Sung Túc trọn đời", "children": []}]},
        {"name": "Phí rút tiền mặt tại ATM", "children": []}]},
    ]
  }

QUAN TRỌNG: catalog CHỈ chứa TÊN mục (lean) — KHÔNG chứa giá trị cụ thể (số tiền, %,
điều kiện chi tiết). Giá trị cụ thể do chunk-based retrieval cung cấp; cây entities cho
ReAct agent biết "tổng thể tài liệu có những mục nào / phân cấp ra sao" để đánh giá độ đầy đủ.

Cách sinh: extract 1 partial-tree cho TỪNG ĐƠN VỊ (mặc định là chunk đã contextual —
mỗi mảnh self-contained nhờ câu định vị nên gán facet đúng kể cả khi section kéo dài qua
nhiều trang / trang không có header; hoặc parsed_text từng page), rồi MERGE + PRUNE thành
cây document-level. Nguồn cấu hình qua settings.catalog_source ("chunks" | "pages").
"""
from __future__ import annotations

import json
import logging
import re

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.services import llm_client

logger = logging.getLogger("catalog_service")

# Giới hạn độ dài cho nhánh fallback (sinh 1 lần trên full_text khi extract theo page rỗng).
MAX_DOC_CHARS = 60_000
# Tên node hợp lệ: ngắn gọn (tên mục), không phải cả câu văn.
MAX_NAME_LEN = 120

_SCHEMA_HINT = '{"tree": [{"name": "<tên facet>", "children": [{"name": "<tên mục con>", "children": []}]}]}'


def _rules(focus_entities: list[str]) -> str:
    facets_bullets = "\n".join(f"- {e}" for e in focus_entities)
    return (
        "Xây dựng một CÂY ENTITIES (mục lục phân cấp) cho nội dung dưới đây.\n\n"
        "Các FACET ở tầng gốc (chỉ dùng khi tài liệu có đề cập):\n"
        f"{facets_bullets}\n\n"
        "QUY TẮC BẮT BUỘC:\n"
        "1. Node tầng gốc PHẢI là một facet trong danh sách trên. Chỉ khi một mục quan trọng "
        "không thuộc facet nào mới đặt dưới facet tên \"Khác\".\n"
        "2. Mỗi heading/khoản/mục thật trong tài liệu là 1 node đặt dưới đúng facet; nếu mục có "
        "các mục con thì lồng chúng vào \"children\" (đệ quy, nhiều tầng).\n"
        "3. Với văn bản tuân thủ/quy định, ưu tiên tên KHÁI NIỆM NGHIỆP VỤ được điều khoản "
        "điều chỉnh (ví dụ: mật khẩu, MFA, khóa phiên, thời hạn lưu trữ), không chỉ chép tên "
        "heading chung chung như \"Quy định cụ thể\". Có thể giữ số Điều/Khoản/Phụ lục trong "
        "tên node để truy vết nguồn.\n"
        "4. Với căn cứ/tham chiếu/thay thế, giữ TÊN và SỐ HIỆU văn bản được nhắc tới; với "
        "ngoại lệ/ưu tiên/xung đột, đặt tên ngắn gọn theo CHỦ ĐỀ chịu tác động. Không suy diễn "
        "quan hệ không được nêu trong nội dung đầu vào.\n"
        "5. LEAN — CHỈ lấy TÊN mục ngắn gọn. TUYỆT ĐỐI KHÔNG kèm giá trị cụ thể "
        "(số tiền, %, số ngày, điều kiện chi tiết).\n"
        "6. KHÔNG lấy làm entity: tên cột của bảng (vd \"Khách hàng đăng ký/không đăng ký gói...\"), "
        "tiêu đề/chân trang, tên công ty/địa chỉ/hotline, số trang, ghi chú đánh dấu (*), "
        "hay cả câu văn dài.\n"
        "7. Bỏ qua facet không xuất hiện. Nếu không có gì để trích, trả về {\"tree\": []}.\n\n"
        "CHỈ trả về JSON hợp lệ đúng schema sau, không giải thích, không markdown:\n"
        f"{_SCHEMA_HINT}"
    )


def _build_page_messages(title: str, focus_entities: list[str], page_text: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": (
                f"Tài liệu: \"{title}\". Đây là nội dung MỘT TRANG:\n"
                f"<page>\n{page_text}\n</page>"
            ),
        },
        {"role": "user", "content": _rules(focus_entities)},
    ]


def _build_chunk_messages(title: str, focus_entities: list[str], chunk_text: str) -> list[dict]:
    """Message trích cây từ 1 chunk đã contextual (final_content = title + câu định vị + body).

    Nhắc model: các dòng đầu là CÂU ĐỊNH VỊ (nêu chủ thể + mục/phần) — chỉ dùng để biết mảnh
    này thuộc facet nào; TÊN các mục lấy từ phần thân. Không đụng tới prompt của contextual.
    """
    return [
        {
            "role": "user",
            "content": (
                f"Tài liệu: \"{title}\". Đây là MỘT ĐOẠN (chunk) đã tự chứa ngữ cảnh: các dòng đầu "
                "là CÂU ĐỊNH VỊ nêu chủ thể + mục/phần (dùng để xác định facet, KHÔNG trích làm "
                "entity); phần thân chứa nội dung các mục cần trích tên:\n"
                f"<chunk>\n{chunk_text}\n</chunk>"
            ),
        },
        {"role": "user", "content": _rules(focus_entities)},
    ]


def _build_fallback_messages(title: str, focus_entities: list[str], full_text: str) -> list[dict]:
    doc = full_text[:MAX_DOC_CHARS]
    if len(full_text) > MAX_DOC_CHARS:
        logger.warning("Fallback catalog: doc dài %s ký tự, cắt còn %s.", len(full_text), MAX_DOC_CHARS)
    return [
        {"role": "user", "content": f"Tài liệu: \"{title}\". Toàn bộ nội dung:\n<document>\n{doc}\n</document>"},
        {"role": "user", "content": _rules(focus_entities)},
    ]


# ------------------------------------------------------------------ parse/normalize

def _parse_catalog_json(raw: str) -> dict:
    """Parse JSON cây từ output LLM một cách chịu lỗi (strip code fence, tìm object)."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))
    return _normalize_tree(data)


def _norm(name: str) -> str:
    """Khóa so khớp/dedup: gộp khoảng trắng + casefold."""
    return re.sub(r"\s+", " ", name).strip().casefold()


def _clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name)).strip()


def _normalize_nodes(nodes) -> list[dict]:
    """Chuẩn hóa list node bất kỳ về [{"name": str, "children": [...]}]. Chấp nhận cả
    trường hợp LLM trả "children" hoặc "headings" (list tên), hoặc list string thuần."""
    out: list[dict] = []
    if not isinstance(nodes, list):
        return out
    for n in nodes:
        if isinstance(n, str):
            name, children_raw = n, []
        elif isinstance(n, dict):
            name = n.get("name") or n.get("entity") or ""
            children_raw = n.get("children")
            if children_raw is None:
                children_raw = n.get("headings", [])
        else:
            continue
        name = _clean_name(name)
        if not name:
            continue
        out.append({"name": name, "children": _normalize_nodes(children_raw)})
    return out


def _normalize_tree(data) -> dict:
    """Chuẩn hóa về {"tree": [node, ...]}. Chấp nhận data là dict có key tree/facets hoặc list."""
    if isinstance(data, list):
        nodes = data
    elif isinstance(data, dict):
        nodes = data.get("tree", data.get("facets", []))
    else:
        nodes = []
    return {"tree": _normalize_nodes(nodes)}


# ------------------------------------------------------------------ merge/prune

def _merge_into(target: list[dict], node: dict) -> None:
    """Merge 1 node vào list target theo tên chuẩn hóa; đệ quy children."""
    key = _norm(node["name"])
    for existing in target:
        if _norm(existing["name"]) == key:
            for ch in node["children"]:
                _merge_into(existing["children"], ch)
            return
    target.append({"name": node["name"], "children": list(node["children"])})


def _merge_trees(trees: list[dict]) -> dict:
    """Hợp nhất nhiều cây (mỗi page 1 cây) thành 1, dedup theo tên ở từng cấp."""
    merged: list[dict] = []
    for t in trees:
        for node in (t or {}).get("tree", []):
            _merge_into(merged, node)
    return {"tree": merged}


def _is_noise(name: str) -> bool:
    """Loại tên rõ ràng là rác: rỗng, quá dài (cả câu), toàn số/ký hiệu, marker."""
    if not name or len(name) > MAX_NAME_LEN:
        return True
    if not re.search(r"[A-Za-zÀ-ỹ]", name):  # không có chữ cái -> số trang/ký hiệu
        return True
    return False


def _prune_nodes(nodes: list[dict]) -> list[dict]:
    """Dọn cây: bỏ tên rác, dedup anh em, gộp con trùng tên cha."""
    out: list[dict] = []
    for n in nodes:
        name = n["name"]
        if _is_noise(name):
            continue
        children = _prune_nodes(n["children"])
        # gộp con trùng tên cha (header nhóm lặp lại): thay bằng cháu
        collapsed: list[dict] = []
        for ch in children:
            if _norm(ch["name"]) == _norm(name):
                collapsed.extend(ch["children"])
            else:
                collapsed.append(ch)
        _merge_into(out, {"name": name, "children": collapsed})
    return out


def _prune(tree: dict, drop_empty_top: bool = True) -> dict:
    """Prune toàn cây; drop_empty_top=True bỏ facet gốc không có mục con (facet không xuất hiện)."""
    nodes = _prune_nodes(tree.get("tree", []))
    if drop_empty_top:
        nodes = [n for n in nodes if n["children"]]
    return {"tree": nodes}


# ------------------------------------------------------------------ LLM + orchestration

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
def _call_llm(messages: list[dict]) -> str:
    return llm_client.chat(
        messages,
        cacheable_prefix_index=0,
        disable_thinking=True,
        temperature=0.0,
        max_tokens=settings.catalog_max_tokens,
        tag="catalog",
    )


def _extract_tree(messages: list[dict]) -> dict:
    raw = _call_llm(messages)
    return _parse_catalog_json(raw)


def generate_catalog(
    title: str,
    unit_texts: list[str],
    focus_entities: list[str],
    *,
    unit_kind: str = "chunk",
    full_text_fallback: str = "",
) -> dict:
    """Sinh cây entities cho document. Trả về {"tree": [...]}; lỗi trả về {"tree": []}.

    unit_kind: "chunk" (final_content đã contextual — mặc định) hoặc "page" (parsed_text).
    Chiến lược: extract partial-tree theo từng đơn vị rồi merge + prune. Nếu tất cả đơn vị rỗng
    (hoặc không có) thì fallback sinh 1 lần trên full_text_fallback.
    """
    builder = _build_page_messages if unit_kind == "page" else _build_chunk_messages
    units = [u for u in (unit_texts or []) if u and u.strip()]
    trees: list[dict] = []
    for idx, unit_text in enumerate(units):
        try:
            trees.append(_extract_tree(builder(title, focus_entities, unit_text)))
        except Exception as exc:  # noqa: BLE001 — 1 đơn vị lỗi không nên chặn cả tài liệu
            logger.warning("Sinh catalog lỗi ở %s %s của '%s': %s", unit_kind, idx, title, exc)

    merged = _merge_trees(trees)
    if not merged["tree"] and full_text_fallback.strip():
        logger.info("Catalog theo %s rỗng cho '%s' -> fallback full_text.", unit_kind, title)
        try:
            merged = _extract_tree(_build_fallback_messages(title, focus_entities, full_text_fallback))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fallback sinh catalog lỗi cho '%s': %s", title, exc)
            return {"tree": []}

    catalog = _prune(merged)
    logger.info(
        "Sinh catalog: %s facet gốc cho '%s' (nguồn=%s, %s đơn vị)",
        len(catalog["tree"]), title, unit_kind, len(units),
    )
    return catalog


# ------------------------------------------------------------------ format cho agent

def _format_nodes(nodes: list[dict], depth: int, lines: list[str]) -> None:
    for n in nodes:
        lines.append(f"{'  ' * depth}- {n['name']}")
        _format_nodes(n.get("children", []), depth + 1, lines)


def format_catalog_text(title: str, catalog: dict | None) -> str:
    """Định dạng cây entities thành text thụt lề để nhét vào context cho agent."""
    if not catalog or not catalog.get("tree"):
        return ""
    lines = [f"# Catalog tài liệu: {title}"]
    _format_nodes(catalog["tree"], 0, lines)
    return "\n".join(lines)
