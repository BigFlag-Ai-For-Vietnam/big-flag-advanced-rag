"""Ontology tối giản cho PoC "reduce noise" của knowledge graph LightRAG.

Ý tưởng lấy từ 2 nguồn tham khảo (xem README.md của PoC này):
- "Ontology-Driven GraphRAG: A Framework for Zero-Noise Knowledge Extraction" (A. Goyal, Medium)
  -> đặt tên "Ontology Operating System": entity type + relation type là schema bắt buộc,
     node/edge không khớp schema thì bị loại trước khi materialize vào graph.
- arXiv:2507.06107 (Khan & Bartolini) -> "unified ontology" làm guard-rail: Schema Definition
  -> Extraction -> Validation & Filtering -> Graph Assembly. Noise bị chặn ở bước Validation,
  không phải sửa ở bước Extraction.

LightRAG (bản 1.5.4) hỗ trợ constrain ENTITY TYPE ngay tại lúc extract qua
`addon_params["entity_types_guidance"]` (native). Nhưng RELATION lại là free-text keywords
("relationship_keywords"), KHÔNG có khái niệm relation-type schema nào ở tầng LightRAG.
=> Ontology ở đây có 2 phần tương ứng 2 lever khác nhau:
  1. ENTITY_TYPES: đẩy thẳng vào LightRAG qua entity_types_guidance (constrain lúc extract).
  2. RELATION_TYPES + ALLOWED_TRIPLES: LightRAG không hỗ trợ -> tự làm ở tầng
     post-processing (noise_filter.py) bằng cách map relationship_keywords tự do về 1
     relation-type chuẩn hoá, rồi kiểm tra (src_type, relation_type, tgt_type) có nằm
     trong danh sách hợp lệ không.

Domain: tài liệu tài chính/bảo hiểm tiếng Việt (thẻ tín dụng, bảo hiểm) — entity types dưới
đây bám theo facet đã dùng cho catalog (`app/catalog_presets.py`) nhưng ở mức hạt (entity),
không phải mức mục lục (heading).
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- entity types

# name -> mô tả ngắn (tiếng Việt) dùng để build entity_types_guidance cho LightRAG.
ENTITY_TYPES: dict[str, str] = {
    "SanPham": "Sản phẩm hoặc gói dịch vụ cụ thể (vd: Thẻ tín dụng Sung Túc, Gói Sung Túc hàng năm, Bảo hiểm Family Care)",
    "ToChuc": "Công ty/tổ chức phát hành hoặc cung cấp sản phẩm (vd: SHBFinance)",
    "LoaiPhi": "Tên một loại phí hoặc loại quyền lợi/điều khoản cụ thể (vd: Phí phát hành lần đầu, Phí rút tiền mặt tại ATM, Quyền lợi tử vong)",
    "MucGiaTri": "Một con số/mức cụ thể gắn với loại phí hoặc quyền lợi — số tiền, phần trăm, hạn mức, kỳ hạn (vd: 110.000 VND/lần, 3% Hạn mức tín dụng, 10 giao dịch đầu tiên)",
    "DieuKienApDung": "Điều kiện hoặc nhóm đối tượng mà một mức giá trị/điều khoản áp dụng cho (vd: Khách hàng đăng ký gói Sung Túc, giao dịch rút tiền tại ATM)",
    "DieuKhoan": "Mục/điều khoản/ghi chú trong tài liệu mà loại phí hoặc điều kiện đó thuộc về (vd: Điều 5 - Phí và lãi suất)",
}

# ---------------------------------------------------------------- relation types

# name -> (mô tả, các cụm từ khoá tiếng Việt/Anh dùng để nhận diện từ
# LightRAG relationship_keywords tự do — heuristic, không phải NLP thật).
RELATION_TYPES: dict[str, tuple[str, tuple[str, ...]]] = {
    "co_muc_gia_tri": (
        "SanPham/LoaiPhi có một mức giá trị cụ thể",
        ("phí", "mức", "giá trị", "fee", "amount", "cost", "price", "charge"),
    ),
    "ap_dung_khi": (
        "LoaiPhi/MucGiaTri áp dụng trong một điều kiện cụ thể",
        ("điều kiện", "áp dụng", "condition", "applies", "khi", "eligibility"),
    ),
    "thuoc_ve": (
        "LoaiPhi/DieuKienApDung thuộc về 1 SanPham",
        ("thuộc", "của", "belongs", "part of", "gồm", "bao gồm"),
    ),
    "phat_hanh_boi": (
        "SanPham do 1 ToChuc phát hành/cung cấp",
        ("phát hành", "cung cấp", "issued", "provided", "offered by"),
    ),
    "quy_dinh_boi": (
        "LoaiPhi/DieuKienApDung được quy định trong 1 DieuKhoan",
        ("quy định", "nêu tại", "defined", "specified", "stated in", "mục", "điều"),
    ),
}

# (loại nguồn, relation_type, loại đích) hợp lệ — cả 2 chiều đã liệt kê tường minh vì
# LightRAG coi relationship là vô hướng (undirected) nên source/target có thể hoán đổi.
ALLOWED_TRIPLES: set[tuple[str, str, str]] = {
    ("SanPham", "co_muc_gia_tri", "MucGiaTri"),
    ("LoaiPhi", "co_muc_gia_tri", "MucGiaTri"),
    ("LoaiPhi", "ap_dung_khi", "DieuKienApDung"),
    ("MucGiaTri", "ap_dung_khi", "DieuKienApDung"),
    ("LoaiPhi", "thuoc_ve", "SanPham"),
    ("DieuKienApDung", "thuoc_ve", "SanPham"),
    ("SanPham", "phat_hanh_boi", "ToChuc"),
    ("LoaiPhi", "quy_dinh_boi", "DieuKhoan"),
    ("DieuKienApDung", "quy_dinh_boi", "DieuKhoan"),
    ("SanPham", "quy_dinh_boi", "DieuKhoan"),
}
# bù chiều ngược lại (undirected) để tra cứu 2 chiều không cần sort thủ công mỗi lần.
ALLOWED_TRIPLES |= {(b, r, a) for (a, r, b) in ALLOWED_TRIPLES}


def build_entity_types_guidance() -> str:
    """Format ENTITY_TYPES đúng style LightRAG dùng cho `default_entity_types_guidance`
    (xem lightrag/prompt.py) để feed vào addon_params["entity_types_guidance"]."""
    lines = ["Classify each entity using one of the following types. If no type fits, use `Other`.", ""]
    lines += [f"- {name}: {desc}" for name, desc in ENTITY_TYPES.items()]
    return "\n".join(lines)


def classify_relation_keyword(keywords: str) -> str | None:
    """Map relationship_keywords tự do (LightRAG output) về 1 relation_type chuẩn hoá.

    Heuristic substring-match trên keyword tiếng Việt/Anh — ĐỦ cho PoC để chứng minh ý
    tưởng "validate relation theo ontology", KHÔNG phải NLP chuẩn (production nên dùng
    embedding similarity hoặc 1 lượt LLM classify riêng). Trả None nếu không khớp type nào
    -> caller (noise_filter) sẽ coi cạnh đó là "ngoài ontology" và loại bỏ.
    """
    text = (keywords or "").casefold()
    for rel_type, (_desc, kw_list) in RELATION_TYPES.items():
        if any(kw in text for kw in kw_list):
            return rel_type
    return None


_ENTITY_TYPE_BY_CASEFOLD = {name.casefold(): name for name in ENTITY_TYPES}


def canonical_entity_type(entity_type: str | None) -> str | None:
    """LightRAG tự lowercase/snake_case entity_type khi ghi vào graph (quan sát thực tế
    từ 1 lần chạy PoC: guidance đưa "SanPham" nhưng graph lưu "sanpham") — so khớp phải
    casefold thay vì so chuỗi y hệt, nếu không mọi node đều bị coi là "sai type" dù đúng
    ontology. Trả về tên chuẩn PascalCase (khớp key ENTITY_TYPES/ALLOWED_TRIPLES) hoặc
    None nếu không khớp type nào trong ontology."""
    if not entity_type:
        return None
    return _ENTITY_TYPE_BY_CASEFOLD.get(entity_type.casefold())


def normalize_name(name: str) -> str:
    """Khoá so khớp/dedup entity name: gộp khoảng trắng + casefold.

    Cùng tinh thần với `_norm()` trong app/services/catalog_service.py (đã dùng để
    dedup node theo tên khi merge cây catalog) — áp lại ở đây cho entity resolution
    của knowledge graph.
    """
    return re.sub(r"\s+", " ", name or "").strip().casefold()
