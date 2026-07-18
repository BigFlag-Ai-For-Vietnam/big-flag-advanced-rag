"""Test offline cho catalog (cây entities): parse JSON, merge, prune, format text, preset."""
from types import SimpleNamespace

from app.catalog_presets import (
    CATALOG_PRESETS,
    list_presets,
    resolve_focus_entities,
)
from app.services.catalog_service import (
    _build_chunk_messages,
    _build_page_messages,
    _merge_trees,
    _parse_catalog_json,
    _prune,
    format_catalog_text,
)
from scripts import recatalog


def _names(nodes):
    return [n["name"] for n in nodes]


def test_parse_plain_tree_json():
    raw = (
        '{"tree": [{"name": "Các loại phí", "children": ['
        '{"name": "Phí thường niên", "children": []},'
        '{"name": "Phí mở thẻ", "children": []}]}]}'
    )
    out = _parse_catalog_json(raw)
    assert out["tree"][0]["name"] == "Các loại phí"
    assert _names(out["tree"][0]["children"]) == ["Phí thường niên", "Phí mở thẻ"]


def test_parse_json_in_code_fence():
    raw = '```json\n{"tree": [{"name": "Phạm vi", "children": [{"name": "A", "children": []}]}]}\n```'
    out = _parse_catalog_json(raw)
    assert out["tree"][0]["name"] == "Phạm vi"


def test_parse_accepts_headings_key_and_strings():
    # Chấp nhận LLM trả "headings" (list string) thay cho "children".
    raw = '{"tree": [{"name": "X", "headings": ["a", "b"]}]}'
    out = _parse_catalog_json(raw)
    assert _names(out["tree"][0]["children"]) == ["a", "b"]


def test_parse_drops_empty_name_nodes():
    raw = '{"tree": [{"name": "", "children": [{"name": "x", "children": []}]}, {"name": "Y", "children": [{"name": "z", "children": []}]}]}'
    out = _parse_catalog_json(raw)
    assert _names(out["tree"]) == ["Y"]


def test_merge_trees_dedup_case_insensitive():
    t1 = {"tree": [{"name": "Các loại phí", "children": [{"name": "Phí A", "children": []}]}]}
    t2 = {"tree": [{"name": "các loại phí", "children": [{"name": "Phí B", "children": []}]}]}
    merged = _merge_trees([t1, t2])
    assert _names(merged["tree"]) == ["Các loại phí"]  # gộp theo tên chuẩn hóa
    assert _names(merged["tree"][0]["children"]) == ["Phí A", "Phí B"]


def test_prune_drops_empty_top_facet_and_noise():
    tree = {"tree": [
        {"name": "Các loại phí", "children": [{"name": "Phí A", "children": []}]},
        {"name": "Hạn mức", "children": []},          # facet rỗng -> bỏ
        {"name": "123", "children": [{"name": "x", "children": []}]},  # tên rác (số) -> bỏ
    ]}
    out = _prune(tree)
    assert _names(out["tree"]) == ["Các loại phí"]


def test_prune_collapses_child_same_name_as_parent():
    # Header nhóm lặp lại: "Phí gói Sung Túc" chứa con trùng tên mang các cháu.
    tree = {"tree": [{"name": "Các loại phí", "children": [
        {"name": "Phí gói Sung Túc", "children": [
            {"name": "Phí gói Sung Túc", "children": [
                {"name": "hằng năm", "children": []},
                {"name": "trọn đời", "children": []}]}]}]}]}
    out = _prune(tree)
    sung_tuc = out["tree"][0]["children"][0]
    assert sung_tuc["name"] == "Phí gói Sung Túc"
    assert _names(sung_tuc["children"]) == ["hằng năm", "trọn đời"]


def test_format_catalog_text_indented():
    catalog = {"tree": [{"name": "Các loại phí", "children": [
        {"name": "Phí gói Sung Túc", "children": [
            {"name": "hằng năm", "children": []}]}]}]}
    text = format_catalog_text("Biểu phí thẻ", catalog)
    assert "Biểu phí thẻ" in text
    assert "- Các loại phí" in text
    assert "  - Phí gói Sung Túc" in text
    assert "    - hằng năm" in text


def test_format_empty_catalog():
    assert format_catalog_text("t", {"tree": []}) == ""
    assert format_catalog_text("t", None) == ""


def test_chunk_and_page_builders_carry_text_and_rules():
    focus = ["Các loại phí"]
    chunk_msgs = _build_chunk_messages("Doc", focus, "Biểu phí thẻ\nĐịnh vị...\n\nPhí thường niên: ...")
    page_msgs = _build_page_messages("Doc", focus, "## Biểu phí\nPhí thường niên ...")
    for msgs, needle in [(chunk_msgs, "chunk"), (page_msgs, "page")]:
        joined = "\n".join(m["content"] for m in msgs)
        assert "Phí thường niên" in joined          # nội dung đơn vị được đưa vào
        assert f"<{needle}>" in joined               # đúng loại wrapper
        assert "CÂY ENTITIES" in joined              # kèm rule trích cây
        assert "Các loại phí" in joined              # facet focus xuất hiện


def test_resolve_custom_overrides_preset():
    out = resolve_focus_entities("van_ban_tuan_thu", ["Chỉ facet này"])
    assert out == ["Chỉ facet này"]


def test_resolve_preset_by_category():
    out = resolve_focus_entities("van_ban_tuan_thu", None)
    assert out == CATALOG_PRESETS["van_ban_tuan_thu"]["entities"]


def test_compliance_preset_covers_ground_truth_entities():
    entities = CATALOG_PRESETS["van_ban_tuan_thu"]["entities"]
    joined = "\n".join(entities)

    # Các nhóm này bao phủ entity dùng chung và ba pain point P1/P2/P3 trong GROUND_TRUTH.md.
    for expected in [
        "Căn cứ pháp lý",
        "Hiệu lực, sửa đổi & thay thế",
        "Mật khẩu",
        "xác thực đa yếu tố",
        "Khóa phiên",
        "Dữ liệu cá nhân",
        "dữ liệu huấn luyện",
        "KYC",
        "Thời hạn lưu trữ",
        "xung đột",
    ]:
        assert expected in joined


def test_compliance_catalog_prompt_preserves_traceable_names_without_values():
    messages = _build_chunk_messages(
        "Quyết định 342/2024/QĐ-DDB",
        CATALOG_PRESETS["van_ban_tuan_thu"]["entities"],
        "Điều 2. Mật khẩu phải có tối thiểu 12 ký tự.",
    )
    rules = messages[-1]["content"]

    assert "KHÁI NIỆM NGHIỆP VỤ" in rules
    assert "số Điều/Khoản/Phụ lục" in rules
    assert "TÊN và SỐ HIỆU văn bản" in rules
    assert "KHÔNG kèm giá trị cụ thể" in rules
    assert "Không suy diễn" in rules


def test_resolve_default_when_unknown_category():
    out = resolve_focus_entities("khong_ton_tai", None)
    assert out == CATALOG_PRESETS["khac"]["entities"]


def test_list_presets_shape():
    presets = list_presets()
    keys = {p["key"] for p in presets}
    assert {"van_ban_tuan_thu", "quy_trinh", "khac"} <= keys
    for p in presets:
        assert p["label"] and isinstance(p["entities"], list)


def test_recatalog_uses_contextual_chunks_by_default(monkeypatch):
    doc = SimpleNamespace(
        pages=[SimpleNamespace(parsed_text="Nội dung trang")],
        chunks=[SimpleNamespace(final_content="Chunk đã contextual")],
    )
    monkeypatch.setattr(recatalog.settings, "catalog_source", "chunks")

    units, unit_kind, full_text = recatalog._catalog_input(doc)

    assert units == ["Chunk đã contextual"]
    assert unit_kind == "chunk"
    assert full_text == "Nội dung trang"


def test_recatalog_can_use_pages(monkeypatch):
    doc = SimpleNamespace(
        pages=[SimpleNamespace(parsed_text="Trang 1"), SimpleNamespace(parsed_text=None)],
        chunks=[SimpleNamespace(final_content="Chunk")],
    )
    monkeypatch.setattr(recatalog.settings, "catalog_source", "pages")

    units, unit_kind, full_text = recatalog._catalog_input(doc)

    assert units == ["Trang 1", ""]
    assert unit_kind == "page"
    assert full_text == "Trang 1"
