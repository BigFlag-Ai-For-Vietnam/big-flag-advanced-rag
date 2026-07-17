"""Test build_final_content: định dạng title + câu định vị + raw_text."""
from app.services.chunking_service import build_final_content


def test_final_content_format():
    result = build_final_content(
        title="Điều khoản Thẻ tín dụng Sung Túc",
        contextual_prefix="Đoạn này nói về phí thường niên của Thẻ tín dụng Sung Túc, mục 3.",
        raw_text="Phí thường niên là 500.000đ.",
    )
    lines = result.split("\n")
    assert lines[0] == "Điều khoản Thẻ tín dụng Sung Túc"
    assert "phí thường niên" in result.lower()
    assert result.endswith("Phí thường niên là 500.000đ.")
    # có dòng trống ngăn cách prefix và raw_text
    assert "\n\n" in result


def test_final_content_empty_prefix():
    result = build_final_content("Tiêu đề", "", "Nội dung.")
    assert result.startswith("Tiêu đề")
    assert result.endswith("Nội dung.")
