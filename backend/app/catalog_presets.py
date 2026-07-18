"""Preset facet-entities theo category tài liệu.

Ý tưởng: mỗi category (Tuân thủ / Pháp lý / Quy trình…) có sẵn danh sách
"facet-entities" — các trục thông tin mà LLM cần focus khi sinh CATALOG cho tài liệu.
User chọn category lúc upload để prefill, và được phép customize (thêm/bớt) danh sách này.

Tập trung vào domain văn bản tuân thủ/pháp lý (xem `sample_compliance_corpus/` +
`GROUND_TRUTH.md`) — đã bỏ hẳn 2 preset thẻ tín dụng/bảo hiểm của bản PoC biểu phí trước đó
(không còn phù hợp hướng đi hiện tại).
"""
from __future__ import annotations

# key ổn định (dùng trong API/DB) -> {label hiển thị, entities preset}
CATALOG_PRESETS: dict[str, dict] = {
    "van_ban_tuan_thu": {
        "label": "Văn bản tuân thủ / Quy định",
        "entities": [
            "Thông tin văn bản, phạm vi & đối tượng áp dụng",
            "Căn cứ pháp lý & văn bản tham chiếu",
            "Hiệu lực, sửa đổi & thay thế",
            "Mật khẩu & xác thực đa yếu tố (MFA)",
            "Nhật ký, giám sát & ứng phó sự cố",
            "Khóa phiên, truy cập & làm việc từ xa",
            "Hệ thống thông tin & phân loại cấp độ",
            "Dữ liệu cá nhân, sự đồng ý & quyền chủ thể",
            "AI, dữ liệu huấn luyện & quyết định tự động",
            "Mã hóa, ẩn danh & bảo mật dữ liệu",
            "KYC & phòng chống rửa tiền",
            "Ngưỡng giao dịch & dấu hiệu đáng ngờ",
            "Thời hạn lưu trữ",
            "Ngoại lệ, quy tắc ưu tiên & xung đột",
            "Chế tài & xử phạt",
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
