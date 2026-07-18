# sample_compliance_corpus — bộ văn bản tuân thủ MÔ PHỎNG

Bộ **10 PDF giả lập** (fictional) mô phỏng văn bản tuân thủ ngân hàng, dùng để kiểm thử
pipeline RAG + **relationship/entity extraction (Graph)** và làm showcase hackathon.

> ⚠️ Ngân hàng "TMCP Đông Đô (DongDoBank)" là **hư cấu**; mọi số hiệu, nội dung, người ký đều
> **giả lập** — không phải văn bản pháp luật / quy định thật. Mỗi trang có dòng disclaimer đặt ở
> **lề trên + lề dưới** (ngoài vùng body text → không làm nhiễu VLM parsing).

## Có gì
- 4 văn bản **Nhà nước**: NĐ 88/2024 (DLCN), TT 09/2024 (ATTT), TT 04/2025 (AI), TT 20/2024 (PCRT).
- 6 văn bản **nội bộ** ngân hàng DDB (Quyết định 215, 342, 401, 455, 502, 480).
- Nội dung đã enrich: có **bảng biểu giá trị** (phân loại cấp độ, ngưỡng giao dịch, mức phạt, thời
  hạn lưu, biểu mật khẩu) và **danh sách liệt kê** (quyền, dấu hiệu đáng ngờ, hành vi bị cấm) để
  test các archetype RAG: liệt kê / tra bảng / hỏi specific.
- **[`GROUND_TRUTH.md`](GROUND_TRUTH.md)** — **đáp án**: toàn bộ entity, cạnh quan hệ, chuỗi thay thế,
  ma trận xung đột, và bộ câu hỏi test kèm đáp án đúng. Đọc file này trước.
- `_generator/` — script reproducible (reportlab) để sinh lại/chỉnh sửa bộ văn bản.

## Ba pain point được cài cắm sẵn
- **P1 — hết hiệu lực & thay thế**: `QĐ 342/2024` thay thế `QĐ 215/2022` **một phần**
  (giữ lại Phụ lục 02 danh mục hệ thống trọng yếu).
- **P2 — overlap/xung đột điều khoản**: có ca **tuyên bố ưu tiên** (mật khẩu 12 vs 8 ký tự) và ca
  **im lặng không nói ưu tiên** (timeout 15' vs 30'; dữ liệu huấn luyện AI ẩn danh vs cần đồng ý);
  thêm **ca bẫy ngược** (lưu trữ KYC 10 năm vs DLCN 5 năm — KHÔNG phải xung đột mà là carve-out
  pháp luật chuyên ngành; hệ thống không được báo động giả).
- **P3 — liên kết Nhà nước ↔ nội bộ**: mỗi Quyết định nội bộ `căn cứ` một Thông tư/Nghị định,
  các văn bản Nhà nước lại `căn cứ` lẫn nhau → chuỗi tuân thủ nhiều tầng.

## Regenerate
```bash
python3 -m venv venv && ./venv/bin/pip install reportlab
./venv/bin/python _generator/docs_content.py   # cần font Times New Roman của macOS
```
Font mặc định trỏ tới `/System/Library/Fonts/Supplemental/Times New Roman*.ttf` (macOS).
Trên OS khác, đổi `FONT_DIR` trong `_generator/gen_corpus.py` sang một TTF hỗ trợ tiếng Việt
(vd DejaVuSans, Noto Sans).
