"""Test citation_extractor (offline, thuần regex — không đụng Neo4j/SQLite/LLM).

extract_citations_from_text() là pure function — rẻ nhất trong toàn bộ phần kg promote,
test trực tiếp với fixture text tiếng Việt."""
from app.services.kg.citation_extractor import extract_citations_from_text


def test_thay_the_verb_before_citation():
    text = (
        "Thông tư này áp dụng thay cho thời hạn 05 năm quy định tại Quyết định 455/2019/QĐ-DDB "
        "về lưu trữ hồ sơ khách hàng."
    )
    results = extract_citations_from_text(text)
    assert len(results) == 1
    assert results[0]["target_so_hieu"] == "455/2019/QĐ-DDB"
    assert results[0]["type"] == "THAM_CHIEU"


def test_thay_the_verb_after_citation_with_partial_exception():
    # verb SAU citation + ngoại lệ "giữ hiệu lực một phần" (Phụ lục 02) — case đã bắt được
    # thật ở PoC mà LightRAG 3 lần chạy đều bỏ lỡ.
    text = (
        "Quyết định 342/2020/QĐ-DDB thay thế toàn bộ văn bản trước đó, tuy nhiên Phụ lục 02 "
        "về danh mục thiết bị vẫn tiếp tục có hiệu lực một phần cho tới hết năm 2025."
    )
    results = extract_citations_from_text(text)
    assert len(results) == 1
    r = results[0]
    assert r["target_so_hieu"] == "342/2020/QĐ-DDB"
    assert r["type"] == "THAY_THE"
    assert r["partial"] is True
    assert r["giu_hieu_luc"] and "Phụ lục 02" in r["giu_hieu_luc"]


def test_uu_tien_hon_verb_after_citation():
    text = "Trường hợp có mâu thuẫn với (Quyết định số 401/2021/QĐ-DDB) thì ưu tiên áp dụng quy định mới nhất."
    results = extract_citations_from_text(text)
    assert len(results) == 1
    assert results[0]["target_so_hieu"] == "401/2021/QĐ-DDB"
    assert results[0]["type"] == "UU_TIEN_HON"


def test_can_cu_pattern():
    text = "Văn bản này được ban hành căn cứ Thông tư 09/2024/TT-NHNN của Ngân hàng Nhà nước."
    results = extract_citations_from_text(text)
    assert len(results) == 1
    assert results[0]["target_so_hieu"] == "09/2024/TT-NHNN"
    assert results[0]["type"] == "CAN_CU"


def test_no_verb_context_yields_no_citation():
    # số hiệu xuất hiện nhưng KHÔNG có verb quan hệ nào quanh nó -> không nên trích thành edge
    text = "Danh sách văn bản liên quan bao gồm 09/2024/TT-NHNN và các phụ lục đính kèm."
    assert extract_citations_from_text(text) == []


def test_multiple_citations_in_one_text():
    text = (
        "Căn cứ Thông tư 09/2024/TT-NHNN, văn bản này thay thế Quyết định 342/2020/QĐ-DDB."
    )
    results = extract_citations_from_text(text)
    so_hieu_types = {r["target_so_hieu"]: r["type"] for r in results}
    assert so_hieu_types.get("09/2024/TT-NHNN") == "CAN_CU"
    assert so_hieu_types.get("342/2020/QĐ-DDB") == "THAY_THE"
