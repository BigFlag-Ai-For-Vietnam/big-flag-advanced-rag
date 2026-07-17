"""Preset facet-entities theo category tài liệu.

Ý tưởng: mỗi category (Thẻ tín dụng / Bảo hiểm / Quy trình…) có sẵn danh sách
"facet-entities" — các trục thông tin mà LLM cần focus khi sinh CATALOG cho tài liệu.
User chọn category lúc upload để prefill, và được phép customize (thêm/bớt) danh sách này.

Danh sách dưới đây rút ra từ chính các tài liệu mẫu trong `backend/docs`
(Thẻ tín dụng Sung Túc / SHBFinance, Bảo hiểm Family, Bảo hiểm Bảo Tâm An + TASCO).
"""
from __future__ import annotations

# key ổn định (dùng trong API/DB) -> {label hiển thị, entities preset}
CATALOG_PRESETS: dict[str, dict] = {
    "the_tin_dung": {
        "label": "Thẻ tín dụng",
        "entities": [
            "Định nghĩa & thuật ngữ",
            "Các loại phí",
            "Hạn mức (tín dụng, giao dịch, rút tiền)",
            "Lãi suất, kỳ sao kê & thanh toán",
            "Quyền lợi & ưu đãi",
            "Quyền & nghĩa vụ của chủ thẻ",
            "Điều kiện phát hành & sử dụng",
            "An toàn, bảo mật & xử lý tranh chấp",
        ],
    },
    "bao_hiem": {
        "label": "Bảo hiểm",
        "entities": [
            "Đối tượng & điều kiện tham gia",
            "Phạm vi bảo hiểm",
            "Quyền lợi bảo hiểm (chính & bổ sung)",
            "Điều kiện loại trừ",
            "Số tiền bảo hiểm & phí bảo hiểm",
            "Hồ sơ & thủ tục bồi thường",
            "Thời hạn & hiệu lực hợp đồng",
            "Định nghĩa & thuật ngữ",
        ],
    },
    "quy_trinh": {
        "label": "Quy trình / Hướng dẫn",
        "entities": [
            "Mục đích & phạm vi áp dụng",
            "Đối tượng áp dụng",
            "Các bước thực hiện",
            "Trách nhiệm các bên",
            "Biểu mẫu & hồ sơ liên quan",
            "Định nghĩa & thuật ngữ",
        ],
    },
    "khac": {
        "label": "Khác (tổng quát)",
        "entities": [
            "Chủ thể / sản phẩm chính",
            "Các mục / phần chính",
            "Số liệu & điều kiện quan trọng",
            "Định nghĩa & thuật ngữ",
        ],
    },
}

DEFAULT_CATEGORY = "khac"


def list_presets() -> list[dict]:
    """Trả về danh sách preset cho UI: [{key, label, entities}]."""
    return [
        {"key": key, "label": val["label"], "entities": val["entities"]}
        for key, val in CATALOG_PRESETS.items()
    ]


def resolve_focus_entities(
    category: str | None, custom_entities: list[str] | None
) -> list[str]:
    """Chốt danh sách focus-entities dùng để sinh catalog.

    Ưu tiên: custom_entities (nếu user nhập) > preset theo category > preset mặc định.
    """
    if custom_entities:
        cleaned = [e.strip() for e in custom_entities if e and e.strip()]
        if cleaned:
            return cleaned
    preset = CATALOG_PRESETS.get(category or "", CATALOG_PRESETS[DEFAULT_CATEGORY])
    return list(preset["entities"])
