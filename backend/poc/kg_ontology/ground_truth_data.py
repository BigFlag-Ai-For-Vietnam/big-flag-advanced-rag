"""Transcribe tay `sample_compliance_corpus/GROUND_TRUTH.md` (§1-§5) thành Python data
có cấu trúc — nguồn CHÍNH cho ontology entities/relations (build_ontology_yaml.py) và cho
bộ competency questions (validator tầng sau, chưa dùng ở PoC này).

`code` là khoá ngắn dùng nội bộ file này để nối các bảng với nhau; `pdf_stem` khớp đúng
`Document.title` mà `ingest_corpus.py` đặt (title = tên file PDF bỏ đuôi .pdf).
"""
from __future__ import annotations

# ------------------------------------------------------------------ §1 Danh mục văn bản

DOCUMENTS: list[dict] = [
    {
        "code": "ND88", "pdf_stem": "01_ND_88_2024_NDCP_bao_ve_du_lieu_ca_nhan",
        "so_hieu": "88/2024/NĐ-CP", "loai": "Nghị định", "cap": "Nhà nước (Chính phủ)",
        "ngay_bh": "15/10/2024", "hieu_luc_tu": "01/01/2025", "trang_thai": "Còn hiệu lực",
    },
    {
        "code": "TT09", "pdf_stem": "02_TT_09_2024_TT-NHNN_an_toan_he_thong_thong_tin",
        "so_hieu": "09/2024/TT-NHNN", "loai": "Thông tư", "cap": "Nhà nước (NHNN)",
        "ngay_bh": "20/05/2024", "hieu_luc_tu": "01/07/2024", "trang_thai": "Còn hiệu lực",
    },
    {
        "code": "TT04", "pdf_stem": "03_TT_04_2025_TT-NHNN_quan_ly_rui_ro_AI",
        "so_hieu": "04/2025/TT-NHNN", "loai": "Thông tư", "cap": "Nhà nước (NHNN)",
        "ngay_bh": "28/03/2025", "hieu_luc_tu": "01/06/2025", "trang_thai": "Còn hiệu lực",
    },
    {
        "code": "QD215", "pdf_stem": "04_QD_215_2022_QD-DDB_ATTT_v1_BI_THAY_THE",
        "so_hieu": "215/2022/QĐ-DDB", "loai": "Quyết định", "cap": "Nội bộ DDB",
        "ngay_bh": "10/03/2022", "hieu_luc_tu": "10/03/2022",
        "trang_thai": "BỊ THAY THẾ (một phần)",
    },
    {
        "code": "QD342", "pdf_stem": "05_QD_342_2024_QD-DDB_ATTT_v2",
        "so_hieu": "342/2024/QĐ-DDB", "loai": "Quyết định", "cap": "Nội bộ DDB",
        "ngay_bh": "15/08/2024", "hieu_luc_tu": "01/09/2024",
        "trang_thai": "Còn hiệu lực (bản hiện hành ATTT)",
    },
    {
        "code": "QD401", "pdf_stem": "06_QD_401_2024_QD-DDB_lam_viec_tu_xa",
        "so_hieu": "401/2024/QĐ-DDB", "loai": "Quyết định", "cap": "Nội bộ DDB",
        "ngay_bh": "12/11/2024", "hieu_luc_tu": "01/12/2024", "trang_thai": "Còn hiệu lực",
    },
    {
        "code": "QD455", "pdf_stem": "07_QD_455_2025_QD-DDB_bao_ve_du_lieu_khach_hang",
        "so_hieu": "455/2025/QĐ-DDB", "loai": "Quyết định", "cap": "Nội bộ DDB",
        "ngay_bh": "20/02/2025", "hieu_luc_tu": "01/03/2025", "trang_thai": "Còn hiệu lực",
    },
    {
        "code": "QD502", "pdf_stem": "08_QD_502_2025_QD-DDB_su_dung_AI_noi_bo",
        "so_hieu": "502/2025/QĐ-DDB", "loai": "Quyết định", "cap": "Nội bộ DDB",
        "ngay_bh": "15/05/2025", "hieu_luc_tu": "01/06/2025", "trang_thai": "Còn hiệu lực",
    },
    {
        "code": "TT20", "pdf_stem": "09_TT_20_2024_TT-NHNN_phong_chong_rua_tien",
        "so_hieu": "20/2024/TT-NHNN", "loai": "Thông tư", "cap": "Nhà nước (NHNN)",
        "ngay_bh": "30/07/2024", "hieu_luc_tu": "01/09/2024", "trang_thai": "Còn hiệu lực",
    },
    {
        "code": "QD480", "pdf_stem": "10_QD_480_2025_QD-DDB_KYC_phong_chong_rua_tien",
        "so_hieu": "480/2025/QĐ-DDB", "loai": "Quyết định", "cap": "Nội bộ DDB",
        "ngay_bh": "10/04/2025", "hieu_luc_tu": "01/05/2025", "trang_thai": "Còn hiệu lực",
    },
]

DOC_BY_CODE = {d["code"]: d for d in DOCUMENTS}

# ------------------------------------------------------------------ §2 Đồ thị quan hệ (edges)
# target=None + external_name=... nghĩa là văn bản đích KHÔNG nằm trong corpus 10 file
# (dangling ref cố ý cài — P1: TT18/2018 văn bản đời cũ; Luật PCRT 2022 luật gốc).

RELATIONS: list[dict] = [
    # 2.1 CĂN_CỨ / COMPLIES_WITH (nội bộ -> Nhà nước) — P3
    {"source": "QD342", "target": "TT09", "type": "CAN_CU",
     "evidence": "Căn cứ + Điều 3 \"phù hợp Điều 6 TT 09\", Điều 8 dẫn Điều 12 TT 09"},
    {"source": "QD401", "target": "TT09", "type": "CAN_CU", "evidence": "Phần Căn cứ"},
    {"source": "QD455", "target": "ND88", "type": "CAN_CU",
     "evidence": "Căn cứ + Điều 7 dẫn \"Điều 8 NĐ 88\", Điều 9 dẫn \"Điều 13 NĐ 88\""},
    {"source": "QD502", "target": "TT04", "type": "CAN_CU",
     "evidence": "Căn cứ + Điều 4 dẫn \"Điều 7 TT 04\", Điều 9 dẫn \"Điều 3 TT 04\""},
    {"source": "QD480", "target": "TT20", "type": "CAN_CU", "evidence": "Căn cứ + Điều 2/4/8 dẫn TT 20"},
    # 2.2 CĂN_CỨ (Nhà nước -> Nhà nước / Luật)
    {"source": "TT09", "target": "ND88", "type": "CAN_CU", "evidence": None},
    {"source": "TT04", "target": "ND88", "type": "CAN_CU", "evidence": None},
    {"source": "TT04", "target": "TT09", "type": "CAN_CU", "evidence": None},
    {"source": "TT20", "target": None, "external_name": "Luật Phòng chống rửa tiền 2022",
     "type": "CAN_CU", "evidence": None},
    # 2.3 THAM_CHIẾU (nội bộ -> nội bộ)
    {"source": "QD401", "target": "QD342", "type": "THAM_CHIEU",
     "evidence": "Điều 4.2 (tuyên bố ưu tiên), Điều 5"},
    {"source": "QD502", "target": "QD342", "type": "THAM_CHIEU", "evidence": "Điều 8 (ATTT cho hệ thống AI)"},
    {"source": "QD480", "target": "QD455", "type": "THAM_CHIEU",
     "evidence": "Điều 8 — thời hạn 10 năm áp dụng thay cho 5 năm của QĐ 455"},
    # 2.4 THAY_THẾ (supersession) — P1
    {"source": "QD342", "target": "QD215", "type": "THAY_THE", "partial": True,
     "giu_hieu_luc": ["Phụ lục 02 — Danh mục hệ thống thông tin trọng yếu"],
     "evidence": "Điều 1.2 thay thế toàn bộ; Điều 1.3 GIỮ hiệu lực Phụ lục 02"},
    {"source": "QD215", "target": None, "external_name": "TT 18/2018/TT-NHNN", "type": "CAN_CU",
     "evidence": "Phần Căn cứ (luật đời cũ — dangling ref cố ý)"},
]

# ------------------------------------------------------------------ §3 Entity dùng chung (KhaiNiem)

CONCEPTS: list[dict] = [
    {"name": "Mật khẩu", "xuat_hien_tai": ["QD215", "QD342", "QD401"],
     "ghi_chu": "giá trị mâu thuẫn (xem CONFLICTS)"},
    {"name": "Xác thực đa yếu tố (MFA)", "xuat_hien_tai": ["TT09", "QD215", "QD342", "QD401"],
     "ghi_chu": "QĐ215 \"khuyến khích\" -> QĐ342 \"bắt buộc\" (theo TT09)"},
    {"name": "Nhật ký / Log", "xuat_hien_tai": ["TT09", "QD215", "QD342"],
     "ghi_chu": "6 tháng (215) -> 12 tháng (342, khớp TT09)"},
    {"name": "Khóa phiên (session timeout)", "xuat_hien_tai": ["QD215", "QD342", "QD401"],
     "ghi_chu": "15' nội bộ vs 30' từ xa"},
    {"name": "Hệ thống thông tin trọng yếu", "xuat_hien_tai": ["TT09", "QD215", "QD342"],
     "ghi_chu": "Cấp độ 3+ (TT09), Phụ lục 02 (QĐ215) — link supersession một phần"},
    {"name": "Phân loại cấp độ hệ thống (1-5)", "xuat_hien_tai": ["TT09"],
     "ghi_chu": "Điều 3 (bảng): core banking = Cấp độ 4"},
    {"name": "Dữ liệu cá nhân", "xuat_hien_tai": ["ND88", "TT09", "TT04", "QD401", "QD455", "QD502", "QD480"],
     "ghi_chu": "entity trung tâm liên kết Nhà nước<->nội bộ"},
    {"name": "Sự đồng ý (consent)", "xuat_hien_tai": ["ND88", "TT04", "QD455"],
     "ghi_chu": "mấu chốt xung đột huấn luyện AI"},
    {"name": "Huấn luyện mô hình AI", "xuat_hien_tai": ["ND88", "TT04", "QD455", "QD502"],
     "ghi_chu": "mấu chốt xung đột (ND88 Đ9, TT04 Đ9, QĐ455 Đ5, QĐ502 Đ6)"},
    {"name": "Phân loại rủi ro AI (4 mức)", "xuat_hien_tai": ["TT04", "QD502"],
     "ghi_chu": "TT04 Đ3 (bảng), QĐ502 Đ9: chấm điểm tín dụng = rủi ro Cao"},
    {"name": "Human-in-the-loop / quyết định tín dụng", "xuat_hien_tai": ["TT04", "QD502"],
     "ghi_chu": "overlap ĐỒNG NHẤT (không xung đột), TT04 Đ7 <-> QĐ502 Đ4"},
    {"name": "Mã hóa", "xuat_hien_tai": ["ND88", "TT09", "QD342", "QD401", "QD455"],
     "ghi_chu": "tiêu chuẩn cụ thể: AES-256, TLS 1.2 (QĐ342 Đ7 bảng)"},
    {"name": "Ẩn danh (anonymization)", "xuat_hien_tai": ["TT04", "QD502"],
     "ghi_chu": "TT04 Đ9.2, QĐ502 Đ6 — định nghĩa gây tranh cãi trong xung đột"},
    {"name": "KYC / Nhận biết khách hàng", "xuat_hien_tai": ["TT20", "QD480"],
     "ghi_chu": "cặp Nhà nước<->nội bộ mới"},
    {"name": "Ngưỡng giao dịch báo cáo", "xuat_hien_tai": ["TT20", "QD480"],
     "ghi_chu": "TT20 Đ5 (bảng), QĐ480 Đ4 (bảng): tiền mặt >=400tr (NN) / >=300tr (nội bộ)"},
    {"name": "Dấu hiệu giao dịch đáng ngờ", "xuat_hien_tai": ["TT20", "QD480"],
     "ghi_chu": "TT20 Đ6 (8 mục), QĐ480 Đ6 (5 mục)"},
    {"name": "Thời hạn lưu trữ", "xuat_hien_tai": ["ND88", "QD455", "QD502", "TT20", "QD480"],
     "ghi_chu": "3 mốc khác nhau theo loại dữ liệu: 5 năm (DLCN), 24 tháng (AI), 10 năm (KYC)"},
    {"name": "Xử phạt vi phạm hành chính", "xuat_hien_tai": ["ND88"],
     "ghi_chu": "ND88 Đ14 (bảng): 80-300 triệu theo hành vi"},
]

# ------------------------------------------------------------------ §4 Ma trận OVERLAP / XUNG ĐỘT

CONFLICTS_DECLARED_PRIORITY: list[dict] = [
    {
        "topic": "Độ dài mật khẩu", "doc_a": "QD342", "gia_tri_a": "12 ký tự, 180 ngày",
        "doc_b": "QD401", "gia_tri_b": "8 ký tự",
        "mau_thuan": "Có (12 vs 8)", "uu_tien_tuyen_bo": True,
        "uu_tien_cho": "QD342", "bang_chung_uu_tien": "QĐ401 Đ4.2 \"ưu tiên QĐ342\"",
        "ket_luan_dung": "Áp dụng 12 ký tự (QĐ342)",
    },
    {
        "topic": "Thời hạn lưu KYC vs DLCN", "doc_a": "QD480", "gia_tri_a": "10 năm (KYC)",
        "doc_b": "QD455", "gia_tri_b": "5 năm (DLCN)",
        "mau_thuan": "Bề ngoài mâu thuẫn", "uu_tien_tuyen_bo": True,
        "uu_tien_cho": "QD480",
        "bang_chung_uu_tien": (
            "QĐ480 Đ8 nói rõ \"áp dụng thay cho 5 năm do là pháp luật chuyên ngành\"; "
            "NĐ88 Đ8 có carve-out \"trừ pháp luật chuyên ngành\""
        ),
        "ket_luan_dung": (
            "KHÔNG phải xung đột thật: hồ sơ KYC lưu 10 năm (chuyên ngành thắng). "
            "Hệ thống KHÔNG được báo động giả (bẫy ngược)."
        ),
    },
]

CONFLICTS_SILENT: list[dict] = [
    {
        "topic": "Khóa phiên", "doc_a": "QD342", "gia_tri_a": "15 phút (nội bộ)",
        "doc_b": "QD401", "gia_tri_b": "30 phút (từ xa)",
        "mau_thuan": "Mập mờ — cùng chủ đề, khác phạm vi", "uu_tien_tuyen_bo": False,
        "ly_do_khong_uu_tien": "câu ưu tiên QĐ401 chỉ phủ \"mật khẩu và xác thực\", không phủ timeout",
        "ky_vong_he_thong": "Cảnh báo 2 giá trị theo phạm vi; không tự chọn 1",
    },
    {
        "topic": "Dữ liệu huấn luyện AI",
        "doc_a": "QD455", "gia_tri_a": "dùng DLCN huấn luyện phải có đồng ý riêng (Đ5)",
        "doc_b": "QD502", "gia_tri_b": "dữ liệu đã ẩn danh dùng huấn luyện, lưu 24 tháng, không nhắc đồng ý (Đ6)",
        "mau_thuan": "Có — QĐ502 mở \"cửa\" ẩn danh mà QĐ455 không đề cập", "uu_tien_tuyen_bo": False,
        "ly_do_khong_uu_tien": "hai văn bản không dẫn chiếu nhau ở điểm này",
        "ky_vong_he_thong": (
            "Cảnh báo xung đột + nêu mấu chốt: dữ liệu ẩn danh có còn là \"dữ liệu cá nhân\" "
            "không? (định nghĩa NĐ88 Đ2). Showcase mạnh nhất: chạm cả P1/P2/P3."
        ),
    },
]

OVERLAPS_CONSISTENT: list[dict] = [
    {"topic": "MFA bắt buộc cho truy cập từ xa", "docs": ["TT09", "QD342"], "trang_thai": "Khớp (nội bộ tuân thủ Nhà nước)"},
    {"topic": "Log >= 12 tháng", "docs": ["TT09", "QD342"], "trang_thai": "Khớp"},
    {"topic": "Human-in-the-loop cho từ chối tín dụng", "docs": ["TT04", "QD502"], "trang_thai": "Khớp"},
    {"topic": "Thời hạn lưu DLCN <= 5 năm", "docs": ["ND88", "QD455"], "trang_thai": "Khớp"},
    {"topic": "Ngưỡng báo cáo giao dịch", "docs": ["TT20", "QD480"],
     "trang_thai": "Nội bộ nghiêm ngặt hơn (300tr < 400tr) — hợp lệ, KHÔNG xung đột"},
]

# ------------------------------------------------------------------ §5 Bộ câu hỏi kiểm thử
# Dùng cho validator tầng sau (competency questions, chưa triển khai ở PoC này) —
# transcribe sẵn để khỏi phải quay lại đọc GROUND_TRUTH.md lần nữa.

COMPETENCY_QUESTIONS: list[dict] = [
    {"id": "Q1", "question": "Mật khẩu đăng nhập hệ thống nội bộ tối thiểu bao nhiêu ký tự?",
     "pain_point": "P1+P2",
     "expected": "12 ký tự (QĐ342 Đ2). QĐ215 (8) đã bị thay thế; QĐ401 (8) tự nhường ưu tiên QĐ342."},
    {"id": "Q2", "question": "Danh mục hệ thống thông tin trọng yếu của DDB gồm những gì?",
     "pain_point": "P1 (partial)",
     "expected": "4 hệ thống ở Phụ lục 02 QĐ215 — vẫn hiệu lực dù QĐ215 bị thay thế (QĐ342 Đ1.3)."},
    {"id": "Q3", "question": "Nhật ký hệ thống phải lưu tối thiểu bao lâu?", "pain_point": "P1",
     "expected": "12 tháng (QĐ342 Đ4, khớp TT09 Đ10). Không dùng \"6 tháng\" của QĐ215."},
    {"id": "Q4", "question": "Phiên làm việc tự động khóa sau bao nhiêu phút?", "pain_point": "P2 (im lặng)",
     "expected": "Cảnh báo 2 giá trị theo phạm vi: 15' nội bộ (QĐ342), 30' từ xa (QĐ401)."},
    {"id": "Q5", "question": "DDB có được dùng dữ liệu khách hàng để huấn luyện AI không?", "pain_point": "P2+P3",
     "expected": (
         "Nêu xung đột: QĐ455 đòi đồng ý; QĐ502 cho phép nếu ẩn danh (<=24 tháng); "
         "dẫn NĐ88 Đ5/Đ9 + TT04 Đ9; nêu mấu chốt định nghĩa \"ẩn danh\"."
     )},
    {"id": "Q6", "question": "Quy định ATTT của DDB dựa trên văn bản pháp luật nào?", "pain_point": "P3",
     "expected": "QĐ342 & QĐ401 căn cứ TT09/2024/TT-NHNN; TT09 lại căn cứ NĐ88/2024/NĐ-CP."},
    {"id": "Q7", "question": "Hồ sơ nhận biết khách hàng (KYC) phải lưu trữ bao lâu?", "pain_point": "P2 (carve-out)",
     "expected": "10 năm (QĐ480 Đ8 / TT20 Đ10) — KHÔNG phải 5 năm; chuyên ngành PCRT override quy định DLCN."},
    {"id": "Q8", "question": "Quy chế An toàn thông tin nào đang có hiệu lực?", "pain_point": "P1",
     "expected": "QĐ342/2024 (v2.0); QĐ215/2022 đã bị thay thế (trừ Phụ lục 02)."},
    {"id": "Q9", "question": "Liệt kê các dấu hiệu giao dịch đáng ngờ.", "pain_point": "Liệt kê",
     "expected": "8 dấu hiệu ở TT20 Đ6 (hoặc 5 mục nội bộ QĐ480 Đ6)."},
    {"id": "Q10", "question": "Giao dịch tiền mặt bao nhiêu thì phải báo cáo?", "pain_point": "Tra bảng",
     "expected": ">= 400.000.000 VND (TT20 Đ5); nội bộ DDB đặt chặt hơn >= 300.000.000 VND (QĐ480 Đ4)."},
    {"id": "Q11", "question": "Các ứng dụng AI nào bị nghiêm cấm?", "pain_point": "Liệt kê",
     "expected": "5 mục ở TT04 Đ4."},
    {"id": "Q12", "question": "Mức phạt khi chuyển dữ liệu cá nhân ra nước ngoài trái phép là bao nhiêu?",
     "pain_point": "Tra bảng giá trị", "expected": "200-300 triệu đồng (NĐ88 Đ14)."},
    {"id": "Q13", "question": "Hệ thống Core Banking thuộc cấp độ mấy?", "pain_point": "Tra bảng",
     "expected": "Cấp độ 4 (TT09 Đ3, và Phụ lục 02 QĐ215)."},
    {"id": "Q14", "question": "Quyền của khách hàng đối với dữ liệu cá nhân gồm những gì?", "pain_point": "Liệt kê",
     "expected": "7 quyền ở NĐ88 Đ12."},
    {"id": "Q15", "question": "Sự cố nghiêm trọng (rò rỉ DLCN) phải báo cáo NHNN trong bao lâu?",
     "pain_point": "Tra bảng / specific", "expected": "Trong 04 giờ (TT09 Đ12)."},
    {"id": "Q16", "question": "Tiêu chuẩn mã hóa dữ liệu khi lưu trữ của DDB là gì?",
     "pain_point": "Specific / tra bảng", "expected": "AES-256 (QĐ342 Đ7); dữ liệu truyền TLS 1.2 trở lên."},
]
