# -*- coding: utf-8 -*-
"""Nội dung 10 văn bản mô phỏng (bản enrich: dài hơn, có bảng biểu + liệt kê). Chạy: python docs_content.py"""
from reportlab.lib.units import cm
from reportlab.platypus import Spacer, KeepTogether
from gen_corpus import (
    esc, P, S, Paragraph, build_pdf, state_header, internal_header,
    sign_block, noinhan, value_table,
)


def sp(h=6):
    return Spacer(1, h)


def H(t):   # chương / tiêu đề khối
    return Paragraph(esc(t), S["chuong"])


def D(t):   # tên điều
    return Paragraph(esc(t), S["dieu"])


def B(t):   # đoạn body
    return P(t, "body")


def K(t):   # khoản (thụt lề)
    return P(t, "khoan")


def CC(t):  # căn cứ
    return P(t, "cancu")


def bullets(items):
    return [P("– " + it, "khoan") for it in items]


def tbl_block(title, rows, widths):
    """Bảng + tên bảng, giữ tiêu đề bảng đi cùng ít nhất phần đầu."""
    return [D(title), value_table(rows, widths), sp(4)]


# =====================================================================
# 01 — NGHỊ ĐỊNH 88/2024/NĐ-CP — Bảo vệ dữ liệu cá nhân trong TCTD  (STATE, nền)
# =====================================================================
def doc_nd88():
    s = []
    s += state_header(
        "88/2024/NĐ-CP", "CHÍNH PHỦ", "NGHỊ ĐỊNH",
        "Quy định về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng",
        "Hà Nội, ngày 15 tháng 10 năm 2024",
    )
    s += [
        CC("Căn cứ Luật Tổ chức Chính phủ ngày 19 tháng 6 năm 2015;"),
        CC("Căn cứ Luật Các tổ chức tín dụng ngày 18 tháng 01 năm 2024;"),
        CC("Căn cứ Luật An toàn thông tin mạng ngày 19 tháng 11 năm 2015;"),
        CC("Theo đề nghị của Thống đốc Ngân hàng Nhà nước Việt Nam;"),
        B("Chính phủ ban hành Nghị định quy định về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng."),
        sp(),
        H("Chương I. QUY ĐỊNH CHUNG"),
        D("Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng"),
        B("Nghị định này quy định về việc thu thập, xử lý, lưu trữ và bảo vệ dữ liệu cá nhân của khách hàng tại các tổ chức tín dụng, chi nhánh ngân hàng nước ngoài hoạt động tại Việt Nam."),
        D("Điều 2. Giải thích từ ngữ"),
        K("1. **Dữ liệu cá nhân** là thông tin dưới dạng ký hiệu, chữ viết, chữ số, hình ảnh, âm thanh gắn liền với một con người cụ thể hoặc giúp xác định một con người cụ thể."),
        K("2. **Dữ liệu cá nhân nhạy cảm** bao gồm thông tin về tình trạng sức khỏe, dữ liệu sinh trắc học, dữ liệu về tài khoản và lịch sử giao dịch tài chính của khách hàng."),
        K("3. **Chủ thể dữ liệu** là cá nhân được phản ánh thông tin qua dữ liệu cá nhân."),
        K("4. **Sự đồng ý** của chủ thể dữ liệu là việc thể hiện rõ ràng, tự nguyện sự chấp thuận đối với việc xử lý dữ liệu cá nhân của mình."),
        K("5. **Bên xử lý dữ liệu** là tổ chức, cá nhân thực hiện việc xử lý dữ liệu thay mặt cho tổ chức tín dụng theo hợp đồng."),
    ]
    s += tbl_block("Điều 3. Phân loại dữ liệu cá nhân và mức độ bảo vệ", [
        ["Nhóm dữ liệu", "Ví dụ", "Mức độ bảo vệ"],
        ["Cơ bản", "Họ tên, số điện thoại, địa chỉ liên hệ", "Tiêu chuẩn"],
        ["Định danh", "Số CCCD, số tài khoản, chữ ký", "Nâng cao"],
        ["Nhạy cảm", "Sinh trắc học, sức khỏe, lịch sử giao dịch", "Đặc biệt (bắt buộc mã hóa)"],
    ], [4 * cm, 8 * cm, 4.5 * cm])
    s += [
        H("Chương II. NGUYÊN TẮC VÀ THỜI HẠN XỬ LÝ"),
        D("Điều 5. Nguyên tắc bảo vệ dữ liệu cá nhân"),
        K("1. Dữ liệu cá nhân được xử lý theo đúng mục đích đã được tổ chức tín dụng thông báo cho khách hàng và được sự đồng ý của khách hàng."),
        K("2. Việc **sử dụng dữ liệu cá nhân cho mục đích khác** với mục đích đã thu thập ban đầu phải được sự đồng ý mới của chủ thể dữ liệu, trừ trường hợp pháp luật có quy định khác."),
        K("3. Dữ liệu cá nhân phải được áp dụng các biện pháp kỹ thuật bảo mật, bao gồm mã hóa khi lưu trữ và khi truyền trên môi trường mạng."),
        D("Điều 8. Thời hạn lưu trữ dữ liệu cá nhân"),
        B("Tổ chức tín dụng chỉ được lưu trữ dữ liệu cá nhân trong thời gian cần thiết để đạt được mục đích xử lý và **không quá 05 (năm) năm** kể từ thời điểm khách hàng chấm dứt quan hệ, **trừ trường hợp pháp luật chuyên ngành có quy định thời hạn khác** (ví dụ pháp luật về phòng, chống rửa tiền)."),
    ]
    s += tbl_block("Bảng thời hạn lưu trữ theo loại hồ sơ", [
        ["Loại hồ sơ / dữ liệu", "Thời hạn lưu trữ tối đa"],
        ["Hồ sơ mở và sử dụng tài khoản", "05 năm sau khi đóng tài khoản"],
        ["Dữ liệu phục vụ tiếp thị (đã đồng ý)", "Đến khi khách hàng rút lại sự đồng ý"],
        ["Nhật ký truy cập dữ liệu cá nhân", "02 năm"],
        ["Hồ sơ chuyên ngành (phòng chống rửa tiền)", "Theo pháp luật chuyên ngành"],
    ], [10.5 * cm, 6 * cm])
    s += [
        D("Điều 9. Xử lý dữ liệu cho mục đích phân tích, mô hình hóa"),
        B("Việc sử dụng dữ liệu cá nhân của khách hàng để **phân tích hành vi, xây dựng hoặc huấn luyện các mô hình dự báo, mô hình tự động** được coi là mục đích khác với mục đích thu thập ban đầu và phải tuân thủ khoản 2 Điều 5 Nghị định này."),
        H("Chương III. QUYỀN CỦA CHỦ THỂ DỮ LIỆU"),
        D("Điều 12. Quyền của khách hàng"),
        B("Khách hàng là chủ thể dữ liệu có các quyền sau đây:"),
    ]
    s += bullets([
        "Quyền được biết về việc xử lý dữ liệu cá nhân của mình;",
        "Quyền đồng ý hoặc không đồng ý cho phép xử lý dữ liệu cá nhân;",
        "Quyền truy cập để xem, chỉnh sửa dữ liệu cá nhân;",
        "Quyền yêu cầu xóa dữ liệu cá nhân;",
        "Quyền rút lại sự đồng ý đã cung cấp;",
        "Quyền phản đối việc xử lý dữ liệu cho mục đích tiếp thị;",
        "Quyền khiếu nại, tố cáo và yêu cầu bồi thường thiệt hại theo quy định.",
    ])
    s += [
        D("Điều 13. Thông báo vi phạm dữ liệu cá nhân"),
        B("Khi xảy ra vi phạm dữ liệu cá nhân, tổ chức tín dụng phải thông báo cho Ngân hàng Nhà nước và chủ thể dữ liệu bị ảnh hưởng **trong thời hạn 72 (bảy mươi hai) giờ** kể từ khi phát hiện."),
        H("Chương IV. XỬ LÝ VI PHẠM"),
    ]
    s += tbl_block("Điều 14. Mức xử phạt vi phạm hành chính", [
        ["Hành vi vi phạm", "Mức phạt (triệu đồng)"],
        ["Xử lý dữ liệu cá nhân khi chưa có sự đồng ý", "80 – 100"],
        ["Không áp dụng mã hóa với dữ liệu nhạy cảm", "100 – 150"],
        ["Không thông báo vi phạm trong 72 giờ", "150 – 200"],
        ["Chuyển dữ liệu cá nhân ra nước ngoài trái phép", "200 – 300"],
    ], [11 * cm, 5.5 * cm])
    s += [
        D("Điều 15. Hiệu lực thi hành"),
        B("Nghị định này có hiệu lực thi hành kể từ ngày **01 tháng 01 năm 2025**."),
    ]
    s += sign_block("TM. CHÍNH PHỦ\nKT. THỦ TƯỚNG\n(mô phỏng)", "Nguyễn Văn A",
                    extra_left=noinhan(["Các tổ chức tín dụng", "Ngân hàng Nhà nước Việt Nam", "Lưu: VT"]))
    build_pdf("01_ND_88_2024_NDCP_bao_ve_du_lieu_ca_nhan.pdf", s)


# =====================================================================
# 02 — THÔNG TƯ 09/2024/TT-NHNN — An toàn hệ thống CNTT  (STATE)
# =====================================================================
def doc_tt09():
    s = []
    s += state_header(
        "09/2024/TT-NHNN", "NGÂN HÀNG NHÀ NƯỚC\nVIỆT NAM", "THÔNG TƯ",
        "Quy định về bảo đảm an toàn, bảo mật hệ thống công nghệ thông tin trong hoạt động ngân hàng",
        "Hà Nội, ngày 20 tháng 5 năm 2024",
    )
    s += [
        CC("Căn cứ Luật Ngân hàng Nhà nước Việt Nam ngày 16 tháng 6 năm 2010;"),
        CC("Căn cứ Luật An toàn thông tin mạng ngày 19 tháng 11 năm 2015;"),
        CC("Căn cứ Nghị định số 88/2024/NĐ-CP ngày 15 tháng 10 năm 2024 của Chính phủ quy định về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng;"),
        B("Thống đốc Ngân hàng Nhà nước Việt Nam ban hành Thông tư quy định về bảo đảm an toàn, bảo mật hệ thống công nghệ thông tin trong hoạt động ngân hàng."),
        sp(),
        H("Chương I. PHÂN LOẠI HỆ THỐNG"),
        D("Điều 3. Phân loại hệ thống thông tin theo cấp độ"),
        B("Hệ thống thông tin của tổ chức tín dụng được phân loại từ Cấp độ 1 đến Cấp độ 5. **Hệ thống thông tin trọng yếu là hệ thống từ Cấp độ 3 trở lên.**"),
    ]
    s += tbl_block("Bảng phân loại cấp độ hệ thống thông tin", [
        ["Cấp độ", "Tiêu chí", "Ví dụ hệ thống"],
        ["Cấp độ 1", "Thông tin công khai", "Website giới thiệu"],
        ["Cấp độ 2", "Nội bộ, ít nhạy cảm", "Thư điện tử nội bộ"],
        ["Cấp độ 3", "Ảnh hưởng nhiều khách hàng", "eKYC, hệ thống thẻ và ATM"],
        ["Cấp độ 4", "Trọng yếu", "Core banking, thanh toán liên ngân hàng"],
        ["Cấp độ 5", "Đặc biệt quan trọng", "Trung tâm dữ liệu dự phòng thảm họa"],
    ], [2.5 * cm, 6.5 * cm, 7.5 * cm])
    s += [
        H("Chương II. KIỂM SOÁT TRUY CẬP"),
        D("Điều 6. Xác thực đa yếu tố"),
        K("1. Tổ chức tín dụng phải áp dụng **xác thực đa yếu tố (MFA)** đối với mọi truy cập từ xa vào hệ thống thông tin nội bộ và đối với mọi truy cập của người dùng có đặc quyền quản trị."),
        K("2. Xác thực đa yếu tố phải bao gồm tối thiểu hai trong ba yếu tố: yếu tố người dùng biết (mật khẩu), yếu tố người dùng có (thiết bị, mã OTP) và yếu tố sinh trắc học."),
        D("Điều 7. Chính sách mật khẩu"),
        B("Tổ chức tín dụng ban hành chính sách mật khẩu bảo đảm độ phức tạp tối thiểu và định kỳ rà soát. Độ dài và chu kỳ thay đổi mật khẩu do tổ chức tín dụng quy định nhưng không thấp hơn mức bảo đảm an toàn thông thường của ngành."),
        D("Điều 8. Yêu cầu kiểm soát truy cập tối thiểu"),
        B("Tổ chức tín dụng phải bảo đảm các yêu cầu sau:"),
    ]
    s += bullets([
        "Áp dụng nguyên tắc đặc quyền tối thiểu (least privilege) cho mọi tài khoản;",
        "Thu hồi quyền truy cập trong vòng 24 giờ khi nhân sự nghỉ việc hoặc chuyển vị trí;",
        "Rà soát, đối chiếu danh sách tài khoản và quyền định kỳ tối thiểu 06 tháng một lần;",
        "Nghiêm cấm sử dụng tài khoản dùng chung cho hệ thống trọng yếu;",
        "Ghi nhật ký toàn bộ hành vi của tài khoản quản trị.",
    ])
    s += [
        H("Chương III. GIÁM SÁT VÀ ỨNG CỨU SỰ CỐ"),
        D("Điều 10. Nhật ký hệ thống"),
        B("Tổ chức tín dụng phải ghi và lưu trữ **nhật ký (log)** truy cập, thao tác trên các hệ thống thông tin trọng yếu trong thời gian **tối thiểu 12 (mười hai) tháng** để phục vụ điều tra, truy vết sự cố."),
        D("Điều 11. Mã hóa dữ liệu"),
        B("Dữ liệu cá nhân của khách hàng và dữ liệu xác thực phải được mã hóa khi lưu trữ và khi truyền trên môi trường mạng, phù hợp với quy định tại Nghị định số 88/2024/NĐ-CP."),
    ]
    s += tbl_block("Điều 12. Thời hạn báo cáo sự cố an toàn thông tin", [
        ["Mức độ sự cố", "Mô tả", "Thời hạn báo cáo NHNN"],
        ["Nghiêm trọng", "Rò rỉ dữ liệu cá nhân; gián đoạn core banking", "Trong 04 giờ"],
        ["Trung bình", "Xâm nhập trái phép chưa gây thiệt hại lớn", "Trong 24 giờ"],
        ["Thấp", "Sự cố đơn lẻ, đã kiểm soát", "Báo cáo định kỳ hàng tháng"],
    ], [3 * cm, 8.5 * cm, 5 * cm])
    s += [
        D("Điều 14. Hiệu lực thi hành"),
        B("Thông tư này có hiệu lực thi hành kể từ ngày **01 tháng 7 năm 2024**."),
    ]
    s += sign_block("KT. THỐNG ĐỐC\nPHÓ THỐNG ĐỐC\n(mô phỏng)", "Trần Thị B",
                    extra_left=noinhan(["Các tổ chức tín dụng, chi nhánh NHNNg", "Văn phòng Chính phủ", "Lưu: VT, CNTT"]))
    build_pdf("02_TT_09_2024_TT-NHNN_an_toan_he_thong_thong_tin.pdf", s)


# =====================================================================
# 03 — THÔNG TƯ 04/2025/TT-NHNN — Quản lý rủi ro ứng dụng AI  (STATE)
# =====================================================================
def doc_tt04():
    s = []
    s += state_header(
        "04/2025/TT-NHNN", "NGÂN HÀNG NHÀ NƯỚC\nVIỆT NAM", "THÔNG TƯ",
        "Quy định về quản lý rủi ro trong ứng dụng trí tuệ nhân tạo (AI) tại tổ chức tín dụng",
        "Hà Nội, ngày 28 tháng 3 năm 2025",
    )
    s += [
        CC("Căn cứ Luật Ngân hàng Nhà nước Việt Nam ngày 16 tháng 6 năm 2010;"),
        CC("Căn cứ Nghị định số 88/2024/NĐ-CP ngày 15 tháng 10 năm 2024 của Chính phủ về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng;"),
        CC("Căn cứ Thông tư số 09/2024/TT-NHNN ngày 20 tháng 5 năm 2024 của Thống đốc Ngân hàng Nhà nước về bảo đảm an toàn, bảo mật hệ thống công nghệ thông tin trong hoạt động ngân hàng;"),
        B("Thống đốc Ngân hàng Nhà nước Việt Nam ban hành Thông tư quy định về quản lý rủi ro trong ứng dụng trí tuệ nhân tạo tại tổ chức tín dụng."),
        sp(),
        D("Điều 2. Giải thích từ ngữ"),
        K("1. **Hệ thống trí tuệ nhân tạo (hệ thống AI)** là hệ thống dựa trên máy học hoặc mô hình thống kê có khả năng đưa ra dự báo, khuyến nghị hoặc quyết định ảnh hưởng đến khách hàng."),
        K("2. **Con người ra quyết định cuối cùng (human-in-the-loop)** là cơ chế trong đó cán bộ có thẩm quyền xem xét, phê duyệt lại kết quả do hệ thống AI đề xuất trước khi áp dụng."),
        K("3. **Mô hình rủi ro cao** là mô hình AI ảnh hưởng trực tiếp đến quyền lợi tài chính hoặc khả năng tiếp cận dịch vụ của khách hàng."),
    ]
    s += tbl_block("Điều 3. Phân loại mức độ rủi ro của hệ thống AI", [
        ["Mức rủi ro", "Ví dụ ứng dụng", "Yêu cầu kiểm soát"],
        ["Không chấp nhận", "Chấm điểm công dân, thao túng hành vi", "Nghiêm cấm sử dụng"],
        ["Cao", "Chấm điểm tín dụng, phê duyệt khoản vay", "Human-in-the-loop + hồ sơ mô hình"],
        ["Trung bình", "Chatbot CSKH, gợi ý sản phẩm", "Giám sát, cảnh báo cho khách hàng"],
        ["Thấp", "Lọc thư rác, phân loại tài liệu nội bộ", "Kiểm soát tối thiểu"],
    ], [3.5 * cm, 6.5 * cm, 6.5 * cm])
    s += [
        D("Điều 4. Các ứng dụng AI bị nghiêm cấm"),
        B("Tổ chức tín dụng không được triển khai các ứng dụng AI sau đây:"),
    ]
    s += bullets([
        "Hệ thống chấm điểm, xếp hạng công dân dựa trên hành vi xã hội;",
        "Ra quyết định cấp hoặc từ chối tín dụng hoàn toàn tự động, không có con người xem xét;",
        "Nhận diện cảm xúc để làm căn cứ tuyển dụng hoặc quyết định tín dụng;",
        "Khai thác điểm yếu của nhóm khách hàng dễ tổn thương;",
        "Sử dụng dữ liệu sinh trắc học của khách hàng cho mục đích ngoài xác thực khi chưa có đồng ý.",
    ])
    s += [
        D("Điều 5. Nguyên tắc minh bạch và giải trình"),
        B("Tổ chức tín dụng phải bảo đảm khả năng giải thích được đối với kết quả của hệ thống AI ảnh hưởng trực tiếp đến quyền lợi của khách hàng, và lưu vết đầy đủ dữ liệu đầu vào, phiên bản mô hình đã sử dụng."),
        D("Điều 6. Trách nhiệm quản trị AI"),
        B("Tổ chức tín dụng thành lập bộ phận hoặc phân công đầu mối chịu trách nhiệm quản trị rủi ro AI, độc lập với bộ phận phát triển mô hình."),
        D("Điều 7. Kiểm soát đối với quyết định tín dụng"),
        B("Mọi **quyết định từ chối hoặc hạn chế cấp tín dụng** do hệ thống AI đề xuất phải được **cán bộ có thẩm quyền phê duyệt lại** theo cơ chế human-in-the-loop trước khi thông báo cho khách hàng."),
        D("Điều 9. Sử dụng dữ liệu để huấn luyện mô hình"),
        K("1. Tổ chức tín dụng **không được sử dụng dữ liệu cá nhân của khách hàng để huấn luyện mô hình AI khi chưa được sự đồng ý** của chủ thể dữ liệu theo quy định tại Nghị định số 88/2024/NĐ-CP."),
        K("2. Trường hợp sử dụng dữ liệu đã được ẩn danh hoặc phi định danh để huấn luyện mô hình, tổ chức tín dụng phải đánh giá và **lưu hồ sơ chứng minh dữ liệu không còn khả năng xác định lại chủ thể dữ liệu**."),
        D("Điều 10. Hồ sơ mô hình AI"),
        B("Đối với mỗi mô hình AI rủi ro cao, tổ chức tín dụng phải lập và lưu hồ sơ gồm:"),
    ]
    s += bullets([
        "Mục đích và phạm vi sử dụng của mô hình;",
        "Nguồn gốc, phạm vi dữ liệu huấn luyện và cơ sở pháp lý sử dụng dữ liệu;",
        "Chỉ số hiệu năng và ngưỡng chấp nhận;",
        "Kết quả đánh giá thiên lệch (bias) đối với các nhóm khách hàng;",
        "Phiên bản mô hình, ngày phê duyệt và người phê duyệt.",
    ])
    s += [
        D("Điều 12. Hiệu lực thi hành"),
        B("Thông tư này có hiệu lực thi hành kể từ ngày **01 tháng 6 năm 2025**."),
    ]
    s += sign_block("KT. THỐNG ĐỐC\nPHÓ THỐNG ĐỐC\n(mô phỏng)", "Trần Thị B",
                    extra_left=noinhan(["Các tổ chức tín dụng, chi nhánh NHNNg", "Bộ Thông tin và Truyền thông", "Lưu: VT, CNTT"]))
    build_pdf("03_TT_04_2025_TT-NHNN_quan_ly_rui_ro_AI.pdf", s)


# =====================================================================
# 04 — QĐ 215/2022/QĐ-DDB — Quy chế ATTT v1.0  (INTERNAL, BỊ THAY THẾ)
# =====================================================================
def doc_qd215():
    s = []
    s += internal_header(
        "215/2022/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy chế An toàn thông tin của Ngân hàng TMCP Đông Đô (Phiên bản 1.0)",
        "Hà Nội, ngày 10 tháng 3 năm 2022",
    )
    s += [
        P("TỔNG GIÁM ĐỐC NGÂN HÀNG TMCP ĐÔNG ĐÔ", "trichyeu"),
        CC("Căn cứ Điều lệ tổ chức và hoạt động của Ngân hàng TMCP Đông Đô;"),
        CC("Căn cứ Thông tư số 18/2018/TT-NHNN ngày 21 tháng 8 năm 2018 của Ngân hàng Nhà nước quy định về an toàn hệ thống thông tin trong hoạt động ngân hàng;"),
        CC("Theo đề nghị của Giám đốc Khối Công nghệ thông tin,"),
        sp(),
        H("QUYẾT ĐỊNH:"),
        D("Điều 1. Chính sách mật khẩu"),
        K("1. Mật khẩu đăng nhập hệ thống nội bộ phải có độ dài **tối thiểu 08 (tám) ký tự**, bao gồm chữ hoa, chữ thường và chữ số."),
        K("2. Người dùng phải **thay đổi mật khẩu định kỳ 90 (chín mươi) ngày** một lần."),
        D("Điều 2. Xác thực"),
        B("Khuyến khích áp dụng xác thực đa yếu tố (MFA) đối với các tài khoản quản trị. Việc áp dụng MFA do từng đơn vị chủ động triển khai theo điều kiện thực tế."),
        D("Điều 3. Nhật ký hệ thống"),
        B("Nhật ký truy cập hệ thống được lưu trữ **tối thiểu 06 (sáu) tháng**."),
        D("Điều 4. Khóa phiên làm việc"),
        B("Phiên làm việc trên máy trạm tự động khóa sau **15 (mười lăm) phút** không có thao tác."),
        D("Điều 5. Điều khoản thi hành"),
        B("Quyết định này có hiệu lực kể từ ngày ký. Danh mục hệ thống thông tin trọng yếu được ban hành kèm theo tại **Phụ lục 02** của Quyết định này."),
        sp(),
        H("PHỤ LỤC 02 — DANH MỤC HỆ THỐNG THÔNG TIN TRỌNG YẾU"),
        value_table([
            ["STT", "Tên hệ thống", "Cấp độ"],
            ["1", "Hệ thống Core Banking T24", "Cấp độ 4"],
            ["2", "Hệ thống thanh toán liên ngân hàng", "Cấp độ 4"],
            ["3", "Hệ thống xác thực khách hàng số (eKYC)", "Cấp độ 3"],
            ["4", "Hệ thống thẻ và ATM", "Cấp độ 3"],
        ], [1.5 * cm, 11 * cm, 3.5 * cm]),
    ]
    s += sign_block("TỔNG GIÁM ĐỐC\n(mô phỏng)", "Lê Văn C",
                    extra_left=noinhan(["Ban Tổng Giám đốc", "Các Khối, Phòng, Ban", "Lưu: VT, CNTT"]))
    build_pdf("04_QD_215_2022_QD-DDB_ATTT_v1_BI_THAY_THE.pdf", s)


# =====================================================================
# 05 — QĐ 342/2024/QĐ-DDB — Quy chế ATTT v2.0 (INTERNAL, THAY THẾ 215 một phần)
# =====================================================================
def doc_qd342():
    s = []
    s += internal_header(
        "342/2024/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy chế An toàn thông tin của Ngân hàng TMCP Đông Đô (Phiên bản 2.0)",
        "Hà Nội, ngày 15 tháng 8 năm 2024",
    )
    s += [
        P("TỔNG GIÁM ĐỐC NGÂN HÀNG TMCP ĐÔNG ĐÔ", "trichyeu"),
        CC("Căn cứ Điều lệ tổ chức và hoạt động của Ngân hàng TMCP Đông Đô;"),
        CC("Căn cứ Thông tư số 09/2024/TT-NHNN ngày 20 tháng 5 năm 2024 của Ngân hàng Nhà nước quy định về bảo đảm an toàn, bảo mật hệ thống công nghệ thông tin trong hoạt động ngân hàng;"),
        CC("Theo đề nghị của Giám đốc Khối Công nghệ thông tin,"),
        sp(),
        H("QUYẾT ĐỊNH:"),
        D("Điều 1. Phạm vi và quy định chuyển tiếp"),
        K("1. Ban hành Quy chế An toàn thông tin phiên bản 2.0 áp dụng thống nhất trong toàn hệ thống Ngân hàng TMCP Đông Đô."),
        K("2. Quyết định này **thay thế Quyết định số 215/2022/QĐ-DDB** ngày 10 tháng 3 năm 2022. Các quy định trước đây trái với Quy chế này đều hết hiệu lực thi hành."),
        K("3. Riêng **Phụ lục 02 (Danh mục hệ thống thông tin trọng yếu) ban hành kèm theo Quyết định số 215/2022/QĐ-DDB tiếp tục có hiệu lực** cho đến khi Danh mục thay thế được ban hành."),
        D("Điều 2. Chính sách mật khẩu"),
        K("1. Mật khẩu đăng nhập hệ thống nội bộ phải có độ dài **tối thiểu 12 (mười hai) ký tự**, bao gồm chữ hoa, chữ thường, chữ số và ký tự đặc biệt."),
        K("2. Người dùng phải **thay đổi mật khẩu định kỳ 180 (một trăm tám mươi) ngày** một lần; không được sử dụng lại 05 mật khẩu gần nhất."),
    ]
    s += tbl_block("Bảng tóm tắt chính sách mật khẩu (áp dụng thống nhất)", [
        ["Thuộc tính", "Yêu cầu"],
        ["Độ dài tối thiểu", "12 ký tự"],
        ["Thành phần", "Chữ hoa, chữ thường, chữ số, ký tự đặc biệt"],
        ["Chu kỳ thay đổi", "180 ngày"],
        ["Không lặp lại", "05 mật khẩu gần nhất"],
        ["Khóa tài khoản", "Sau 05 lần đăng nhập sai liên tiếp"],
    ], [5 * cm, 11.5 * cm])
    s += [
        D("Điều 3. Xác thực đa yếu tố"),
        B("Áp dụng **bắt buộc xác thực đa yếu tố (MFA)** đối với mọi truy cập từ xa vào hệ thống nội bộ và mọi tài khoản có đặc quyền quản trị, phù hợp với Điều 6 Thông tư số 09/2024/TT-NHNN."),
        D("Điều 4. Nhật ký hệ thống"),
        B("Nhật ký truy cập, thao tác trên hệ thống thông tin trọng yếu được lưu trữ **tối thiểu 12 (mười hai) tháng**."),
        D("Điều 5. Khóa phiên làm việc"),
        B("Phiên làm việc trên máy trạm trong mạng nội bộ tự động khóa sau **15 (mười lăm) phút** không có thao tác."),
    ]
    s += tbl_block("Điều 6. Ma trận phân quyền truy cập", [
        ["Vai trò", "Quyền tối đa", "Yêu cầu bổ sung"],
        ["Nhân viên nghiệp vụ", "Truy vấn, nhập liệu", "—"],
        ["Kiểm soát viên", "Phê duyệt giao dịch", "Ghi nhật ký"],
        ["Quản trị hệ thống", "Cấu hình hệ thống", "Bắt buộc MFA + ghi nhật ký đầy đủ"],
        ["Đối tác bên thứ ba", "Theo phạm vi hợp đồng", "Có thời hạn, thu hồi khi hết hạn"],
    ], [4.5 * cm, 6 * cm, 6 * cm])
    s += tbl_block("Điều 7. Tiêu chuẩn mã hóa tối thiểu", [
        ["Trường hợp áp dụng", "Tiêu chuẩn tối thiểu"],
        ["Dữ liệu lưu trữ (at rest)", "AES-256"],
        ["Dữ liệu truyền (in transit)", "TLS 1.2 trở lên"],
        ["Lưu mật khẩu người dùng", "Băm bằng bcrypt hoặc argon2"],
    ], [8.5 * cm, 8 * cm])
    s += [
        D("Điều 8. Xử lý sự cố an toàn thông tin"),
        B("Mọi sự cố an toàn thông tin phải được báo cáo cho Trung tâm Điều hành an ninh (SOC) **trong vòng 02 giờ** kể từ khi phát hiện; sự cố nghiêm trọng liên quan hệ thống trọng yếu phải báo cáo Ngân hàng Nhà nước theo Điều 12 Thông tư số 09/2024/TT-NHNN."),
        D("Điều 10. Điều khoản thi hành"),
        B("Quyết định này có hiệu lực thi hành kể từ ngày **01 tháng 9 năm 2024**."),
    ]
    s += sign_block("TỔNG GIÁM ĐỐC\n(mô phỏng)", "Lê Văn C",
                    extra_left=noinhan(["Ban Tổng Giám đốc", "Các Khối, Phòng, Ban", "Lưu: VT, CNTT"]))
    build_pdf("05_QD_342_2024_QD-DDB_ATTT_v2.pdf", s)


# =====================================================================
# 06 — QĐ 401/2024/QĐ-DDB — Làm việc từ xa (INTERNAL; overlap 342: ưu tiên + im lặng)
# =====================================================================
def doc_qd401():
    s = []
    s += internal_header(
        "401/2024/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định làm việc từ xa và an toàn thiết bị đầu cuối",
        "Hà Nội, ngày 12 tháng 11 năm 2024",
    )
    s += [
        P("TỔNG GIÁM ĐỐC NGÂN HÀNG TMCP ĐÔNG ĐÔ", "trichyeu"),
        CC("Căn cứ Điều lệ tổ chức và hoạt động của Ngân hàng TMCP Đông Đô;"),
        CC("Căn cứ Thông tư số 09/2024/TT-NHNN ngày 20 tháng 5 năm 2024 của Ngân hàng Nhà nước;"),
        CC("Theo đề nghị của Giám đốc Khối Quản trị nguồn nhân lực và Giám đốc Khối Công nghệ thông tin,"),
        sp(),
        H("QUYẾT ĐỊNH:"),
        D("Điều 1. Đối tượng và điều kiện làm việc từ xa"),
        B("Quy định áp dụng cho cán bộ, nhân viên được phê duyệt làm việc từ xa. Thiết bị làm việc từ xa phải được cài đặt phần mềm bảo mật do Ngân hàng cung cấp và kết nối qua kênh VPN."),
    ]
    s += tbl_block("Điều 2. Yêu cầu đối với thiết bị đầu cuối", [
        ["Loại thiết bị", "Yêu cầu bắt buộc"],
        ["Laptop do Ngân hàng cấp", "Mã hóa ổ đĩa, cài EDR, kết nối VPN"],
        ["Thiết bị cá nhân (BYOD)", "Chỉ truy cập qua hạ tầng ảo hóa (VDI); cấm lưu dữ liệu cục bộ"],
    ], [5.5 * cm, 11 * cm])
    s += [
        D("Điều 3. Kết nối mạng"),
        B("Mọi kết nối tới hệ thống nội bộ phải thực hiện qua VPN có mã hóa. Nghiêm cấm truy cập hệ thống nội bộ qua mạng Wi-Fi công cộng khi không có VPN."),
        D("Điều 4. Yêu cầu mật khẩu và xác thực"),
        K("1. Tài khoản truy cập từ xa phải sử dụng mật khẩu có độ dài **tối thiểu 08 (tám) ký tự** và áp dụng xác thực đa yếu tố khi kết nối VPN."),
        K("2. **Về yêu cầu độ phức tạp mật khẩu và xác thực, trường hợp có khác biệt với Quy chế An toàn thông tin hiện hành (Quyết định số 342/2024/QĐ-DDB) thì ưu tiên áp dụng Quy chế An toàn thông tin.**"),
        D("Điều 5. Khóa phiên đối với thiết bị từ xa"),
        B("Đối với thiết bị làm việc từ xa, phiên làm việc tự động khóa sau **30 (ba mươi) phút** không có thao tác nhằm phù hợp với đặc thù kết nối từ xa."),
        D("Điều 6. Dữ liệu trên thiết bị đầu cuối"),
        B("Không lưu trữ dữ liệu cá nhân của khách hàng trên thiết bị đầu cuối cá nhân. Dữ liệu tạm thời phải được mã hóa và xóa sau khi kết thúc công việc."),
        D("Điều 7. Các hành vi bị nghiêm cấm khi làm việc từ xa"),
        B("Nghiêm cấm cán bộ, nhân viên thực hiện các hành vi sau:"),
    ]
    s += bullets([
        "Truy cập hệ thống nội bộ qua Wi-Fi công cộng khi không dùng VPN;",
        "Chụp ảnh, quay màn hình chứa dữ liệu khách hàng;",
        "Cho người khác sử dụng thiết bị đã đăng nhập hệ thống ngân hàng;",
        "In tài liệu mật tại nhà hoặc địa điểm không được kiểm soát;",
        "Lưu mật khẩu hệ thống trên trình duyệt hoặc ghi chú không mã hóa;",
        "Sử dụng công cụ AI công cộng để xử lý dữ liệu công việc.",
    ])
    s += [
        D("Điều 9. Điều khoản thi hành"),
        B("Quyết định này có hiệu lực thi hành kể từ ngày **01 tháng 12 năm 2024**."),
    ]
    s += sign_block("TỔNG GIÁM ĐỐC\n(mô phỏng)", "Lê Văn C",
                    extra_left=noinhan(["Ban Tổng Giám đốc", "Các Khối, Phòng, Ban", "Lưu: VT, HR, CNTT"]))
    build_pdf("06_QD_401_2024_QD-DDB_lam_viec_tu_xa.pdf", s)


# =====================================================================
# 07 — QĐ 455/2025/QĐ-DDB — Bảo vệ dữ liệu KH (INTERNAL; căn cứ NĐ88)
# =====================================================================
def doc_qd455():
    s = []
    s += internal_header(
        "455/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định bảo vệ dữ liệu cá nhân của khách hàng",
        "Hà Nội, ngày 20 tháng 02 năm 2025",
    )
    s += [
        P("TỔNG GIÁM ĐỐC NGÂN HÀNG TMCP ĐÔNG ĐÔ", "trichyeu"),
        CC("Căn cứ Điều lệ tổ chức và hoạt động của Ngân hàng TMCP Đông Đô;"),
        CC("Căn cứ Nghị định số 88/2024/NĐ-CP ngày 15 tháng 10 năm 2024 của Chính phủ về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng;"),
        CC("Theo đề nghị của Giám đốc Khối Pháp chế và Tuân thủ,"),
        sp(),
        H("QUYẾT ĐỊNH:"),
        D("Điều 3. Nguyên tắc xử lý dữ liệu cá nhân"),
        B("Dữ liệu cá nhân của khách hàng chỉ được thu thập và xử lý theo đúng mục đích đã thông báo và được khách hàng đồng ý; được mã hóa khi lưu trữ và khi truyền trên môi trường mạng."),
    ]
    s += tbl_block("Điều 4. Phân loại dữ liệu khách hàng và thời hạn lưu trữ", [
        ["Nhóm dữ liệu", "Thời hạn lưu trữ"],
        ["Hồ sơ định danh (eKYC)", "05 năm sau khi đóng tài khoản"],
        ["Lịch sử giao dịch", "05 năm sau khi đóng tài khoản"],
        ["Dữ liệu phục vụ tiếp thị", "Đến khi khách hàng rút lại đồng ý"],
        ["Ghi âm cuộc gọi chăm sóc khách hàng", "01 năm"],
    ], [9 * cm, 7.5 * cm])
    s += [
        D("Điều 5. Sử dụng dữ liệu cho mục đích thứ cấp"),
        B("Việc sử dụng dữ liệu cá nhân của khách hàng cho **mục đích ngoài mục đích thu thập ban đầu**, bao gồm phân tích hành vi và **huấn luyện mô hình**, chỉ được thực hiện khi **có sự đồng ý riêng bằng văn bản hoặc phương tiện điện tử** của khách hàng."),
        D("Điều 7. Thời hạn lưu trữ chung"),
        B("Dữ liệu cá nhân của khách hàng được lưu trữ trong thời gian cần thiết và **không quá 05 (năm) năm** kể từ khi khách hàng đóng tài khoản hoặc chấm dứt quan hệ, phù hợp với Điều 8 Nghị định số 88/2024/NĐ-CP, **trừ trường hợp pháp luật chuyên ngành quy định thời hạn dài hơn**."),
        D("Điều 8. Quyền của khách hàng"),
        B("Khách hàng có các quyền sau đây và Ngân hàng phải bố trí kênh tiếp nhận, xử lý yêu cầu:"),
    ]
    s += bullets([
        "Quyền yêu cầu truy cập và bản sao dữ liệu cá nhân;",
        "Quyền yêu cầu chỉnh sửa dữ liệu không chính xác;",
        "Quyền yêu cầu xóa dữ liệu khi không còn mục đích xử lý;",
        "Quyền rút lại sự đồng ý đã cung cấp;",
        "Quyền phản đối xử lý dữ liệu cho mục đích tiếp thị.",
    ])
    s += [
        D("Điều 9. Thông báo vi phạm dữ liệu"),
        B("Khi phát hiện vi phạm dữ liệu cá nhân, Khối Pháp chế và Tuân thủ phối hợp Khối CNTT thông báo cho Ngân hàng Nhà nước và khách hàng bị ảnh hưởng **trong vòng 72 giờ**, phù hợp Điều 13 Nghị định số 88/2024/NĐ-CP."),
        D("Điều 11. Điều khoản thi hành"),
        B("Quyết định này có hiệu lực thi hành kể từ ngày **01 tháng 3 năm 2025**."),
    ]
    s += sign_block("TỔNG GIÁM ĐỐC\n(mô phỏng)", "Lê Văn C",
                    extra_left=noinhan(["Ban Tổng Giám đốc", "Khối Pháp chế và Tuân thủ", "Các Khối, Phòng, Ban", "Lưu: VT, PC"]))
    build_pdf("07_QD_455_2025_QD-DDB_bao_ve_du_lieu_khach_hang.pdf", s)


# =====================================================================
# 08 — QĐ 502/2025/QĐ-DDB — Sử dụng AI nội bộ (INTERNAL; căn cứ TT04; XUNG ĐỘT im lặng với 455)
# =====================================================================
def doc_qd502():
    s = []
    s += internal_header(
        "502/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định sử dụng công cụ Trí tuệ nhân tạo trong hoạt động nội bộ",
        "Hà Nội, ngày 15 tháng 5 năm 2025",
    )
    s += [
        P("TỔNG GIÁM ĐỐC NGÂN HÀNG TMCP ĐÔNG ĐÔ", "trichyeu"),
        CC("Căn cứ Điều lệ tổ chức và hoạt động của Ngân hàng TMCP Đông Đô;"),
        CC("Căn cứ Thông tư số 04/2025/TT-NHNN ngày 28 tháng 3 năm 2025 của Ngân hàng Nhà nước về quản lý rủi ro trong ứng dụng trí tuệ nhân tạo tại tổ chức tín dụng;"),
        CC("Theo đề nghị của Giám đốc Khối Công nghệ thông tin và Giám đốc Khối Dữ liệu,"),
        sp(),
        H("QUYẾT ĐỊNH:"),
        D("Điều 2. Danh mục công cụ AI được phê duyệt"),
        B("Chỉ được sử dụng các công cụ AI có trong Danh mục được Ngân hàng phê duyệt dưới đây. **Nghiêm cấm nhập dữ liệu cá nhân hoặc dữ liệu nhạy cảm của khách hàng vào các công cụ AI công cộng** (ví dụ chatbot trên Internet) chưa được phê duyệt."),
    ]
    s += tbl_block("Danh mục công cụ AI nội bộ được phê duyệt", [
        ["Công cụ", "Mục đích", "Mức rủi ro", "Điều kiện sử dụng"],
        ["Trợ lý tra cứu quy định (RAG)", "Tra cứu văn bản nội bộ", "Trung bình", "Không nhập dữ liệu cá nhân KH"],
        ["Mô hình chấm điểm tín dụng", "Hỗ trợ thẩm định khoản vay", "Cao", "Bắt buộc human-in-the-loop"],
        ["Hệ thống phát hiện gian lận", "Giám sát giao dịch bất thường", "Cao", "Cán bộ rà soát cảnh báo"],
        ["Chatbot chăm sóc khách hàng", "Hỗ trợ khách hàng", "Trung bình", "Hiển thị cảnh báo đang dùng AI"],
    ], [4.5 * cm, 4.5 * cm, 2.5 * cm, 5 * cm])
    s += [
        D("Điều 4. Kiểm soát quyết định tín dụng"),
        B("Kết quả do hệ thống AI đề xuất liên quan đến **từ chối hoặc hạn chế cấp tín dụng phải được cán bộ có thẩm quyền phê duyệt lại** (human-in-the-loop) trước khi áp dụng, phù hợp với Điều 7 Thông tư số 04/2025/TT-NHNN."),
        D("Điều 5. Các hành vi bị nghiêm cấm khi sử dụng AI"),
        B("Nghiêm cấm cán bộ, nhân viên:"),
    ]
    s += bullets([
        "Nhập dữ liệu cá nhân, dữ liệu nhạy cảm của khách hàng vào công cụ AI công cộng;",
        "Sử dụng công cụ AI ngoài Danh mục được phê duyệt cho công việc;",
        "Để hệ thống AI tự động ra quyết định tín dụng mà không có người phê duyệt;",
        "Sử dụng kết quả AI chưa kiểm chứng làm nội dung văn bản chính thức gửi khách hàng;",
        "Huấn luyện mô hình trên dữ liệu khách hàng chưa được ẩn danh đúng quy trình.",
    ])
    s += [
        D("Điều 6. Dữ liệu phục vụ huấn luyện mô hình nội bộ"),
        K("1. **Dữ liệu giao dịch đã được ẩn danh (anonymized)** có thể được lưu trữ và sử dụng để huấn luyện, đánh giá và cải thiện các mô hình AI nội bộ trong thời hạn **tối đa 24 (hai mươi bốn) tháng**."),
        K("2. Việc ẩn danh dữ liệu do Khối Dữ liệu thực hiện và chịu trách nhiệm bảo đảm không truy ngược được chủ thể dữ liệu."),
        D("Điều 8. An toàn thông tin đối với hệ thống AI"),
        B("Hệ thống AI nội bộ được quản lý về truy cập, nhật ký và mã hóa theo Quy chế An toàn thông tin hiện hành (Quyết định số 342/2024/QĐ-DDB)."),
        D("Điều 9. Phân loại rủi ro ứng dụng AI nội bộ"),
        B("Mỗi ứng dụng AI được phân loại rủi ro (thấp, trung bình, cao, không chấp nhận) theo Điều 3 Thông tư số 04/2025/TT-NHNN; ứng dụng mức rủi ro cao phải lập hồ sơ mô hình đầy đủ trước khi đưa vào vận hành."),
        D("Điều 10. Điều khoản thi hành"),
        B("Quyết định này có hiệu lực thi hành kể từ ngày **01 tháng 6 năm 2025**."),
    ]
    s += sign_block("TỔNG GIÁM ĐỐC\n(mô phỏng)", "Lê Văn C",
                    extra_left=noinhan(["Ban Tổng Giám đốc", "Khối Dữ liệu, Khối CNTT", "Khối Pháp chế và Tuân thủ", "Lưu: VT, DATA"]))
    build_pdf("08_QD_502_2025_QD-DDB_su_dung_AI_noi_bo.pdf", s)


# =====================================================================
# 09 — THÔNG TƯ 20/2024/TT-NHNN — Phòng, chống rửa tiền  (STATE, mới)
# =====================================================================
def doc_tt20():
    s = []
    s += state_header(
        "20/2024/TT-NHNN", "NGÂN HÀNG NHÀ NƯỚC\nVIỆT NAM", "THÔNG TƯ",
        "Hướng dẫn thực hiện phòng, chống rửa tiền trong hoạt động ngân hàng",
        "Hà Nội, ngày 30 tháng 7 năm 2024",
    )
    s += [
        CC("Căn cứ Luật Phòng, chống rửa tiền ngày 15 tháng 11 năm 2022;"),
        CC("Căn cứ Luật Các tổ chức tín dụng ngày 18 tháng 01 năm 2024;"),
        B("Thống đốc Ngân hàng Nhà nước Việt Nam ban hành Thông tư hướng dẫn thực hiện phòng, chống rửa tiền trong hoạt động ngân hàng."),
        sp(),
        D("Điều 3. Nhận biết khách hàng (KYC)"),
        B("Tổ chức tín dụng phải nhận biết, xác minh và cập nhật thông tin nhận biết khách hàng trước khi thiết lập quan hệ và trong suốt quá trình giao dịch; áp dụng biện pháp nhận biết tăng cường đối với khách hàng có rủi ro cao."),
    ]
    s += tbl_block("Điều 5. Ngưỡng giao dịch phải báo cáo", [
        ["Loại giao dịch", "Ngưỡng", "Loại báo cáo"],
        ["Giao dịch tiền mặt trong ngày", "≥ 400.000.000 VND", "Báo cáo giao dịch giá trị lớn"],
        ["Chuyển tiền điện tử quốc tế", "≥ 1.000 USD", "Báo cáo chuyển tiền điện tử"],
        ["Giao dịch có dấu hiệu đáng ngờ", "Không kể giá trị", "Báo cáo giao dịch đáng ngờ"],
    ], [6 * cm, 5 * cm, 5.5 * cm])
    s += [
        D("Điều 6. Dấu hiệu giao dịch đáng ngờ"),
        B("Tổ chức tín dụng phải giám sát và xem xét báo cáo khi phát hiện các dấu hiệu sau đây:"),
    ]
    s += bullets([
        "Giao dịch được chia nhỏ nhằm tránh ngưỡng phải báo cáo;",
        "Giá trị giao dịch không phù hợp với thu nhập, hoạt động của khách hàng;",
        "Khách hàng từ chối hoặc trì hoãn cung cấp thông tin nhận biết;",
        "Tài khoản nhận tiền từ nhiều nguồn rồi rút hoặc chuyển đi ngay;",
        "Chuyển tiền lòng vòng qua nhiều tài khoản không có lý do kinh tế rõ ràng;",
        "Giao dịch liên quan đến khách hàng, quốc gia trong danh sách rủi ro cao;",
        "Sử dụng nhiều tài khoản của người khác để thực hiện cùng một mục đích;",
        "Đột ngột phát sinh giao dịch giá trị lớn trên tài khoản ít hoạt động.",
    ])
    s += tbl_block("Điều 8. Thời hạn báo cáo", [
        ["Loại báo cáo", "Thời hạn gửi Ngân hàng Nhà nước"],
        ["Báo cáo giao dịch đáng ngờ", "Trong 03 ngày làm việc kể từ khi phát hiện"],
        ["Báo cáo giao dịch giá trị lớn", "Trong 01 ngày làm việc"],
    ], [8 * cm, 8.5 * cm])
    s += [
        D("Điều 10. Lưu trữ hồ sơ, tài liệu"),
        B("Tổ chức tín dụng phải lưu trữ hồ sơ nhận biết khách hàng và hồ sơ báo cáo phòng, chống rửa tiền trong thời gian **tối thiểu 10 (mười) năm** kể từ ngày đóng tài khoản hoặc kể từ ngày hoàn thành giao dịch."),
        D("Điều 12. Hiệu lực thi hành"),
        B("Thông tư này có hiệu lực thi hành kể từ ngày **01 tháng 9 năm 2024**."),
    ]
    s += sign_block("KT. THỐNG ĐỐC\nPHÓ THỐNG ĐỐC\n(mô phỏng)", "Trần Thị B",
                    extra_left=noinhan(["Các tổ chức tín dụng, chi nhánh NHNNg", "Cục Phòng, chống rửa tiền", "Lưu: VT, TTGS"]))
    build_pdf("09_TT_20_2024_TT-NHNN_phong_chong_rua_tien.pdf", s)


# =====================================================================
# 10 — QĐ 480/2025/QĐ-DDB — KYC & PCRT nội bộ (INTERNAL; căn cứ TT20; carve-out lưu trữ)
# =====================================================================
def doc_qd480():
    s = []
    s += internal_header(
        "480/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định nhận biết khách hàng và phòng, chống rửa tiền",
        "Hà Nội, ngày 10 tháng 4 năm 2025",
    )
    s += [
        P("TỔNG GIÁM ĐỐC NGÂN HÀNG TMCP ĐÔNG ĐÔ", "trichyeu"),
        CC("Căn cứ Điều lệ tổ chức và hoạt động của Ngân hàng TMCP Đông Đô;"),
        CC("Căn cứ Thông tư số 20/2024/TT-NHNN ngày 30 tháng 7 năm 2024 của Ngân hàng Nhà nước hướng dẫn thực hiện phòng, chống rửa tiền trong hoạt động ngân hàng;"),
        CC("Theo đề nghị của Giám đốc Khối Pháp chế và Tuân thủ,"),
        sp(),
        H("QUYẾT ĐỊNH:"),
        D("Điều 2. Nhận biết khách hàng"),
        B("Đơn vị kinh doanh thực hiện nhận biết, xác minh khách hàng trước khi mở tài khoản; cập nhật thông tin định kỳ và áp dụng nhận biết tăng cường với khách hàng rủi ro cao, phù hợp Điều 3 Thông tư số 20/2024/TT-NHNN."),
    ]
    s += tbl_block("Điều 4. Ngưỡng giám sát và báo cáo (áp dụng nội bộ)", [
        ["Loại giao dịch", "Ngưỡng nội bộ", "Ghi chú"],
        ["Giao dịch tiền mặt trong ngày", "≥ 300.000.000 VND", "Chặt hơn ngưỡng NHNN để cảnh báo sớm"],
        ["Chuyển tiền quốc tế", "≥ 1.000 USD", "Theo Thông tư 20/2024/TT-NHNN"],
        ["Giao dịch đáng ngờ", "Không kể giá trị", "Báo cáo ngay cho bộ phận AML"],
    ], [5.5 * cm, 4.5 * cm, 6.5 * cm])
    s += [
        D("Điều 6. Dấu hiệu đáng ngờ cần chuyển bộ phận AML"),
        B("Cán bộ phát hiện các dấu hiệu sau phải chuyển ngay bộ phận phòng, chống rửa tiền:"),
    ]
    s += bullets([
        "Khách hàng chia nhỏ giao dịch để tránh ngưỡng báo cáo;",
        "Nguồn tiền không phù hợp với hồ sơ nghề nghiệp, thu nhập;",
        "Khách hàng né tránh cung cấp thông tin nhận biết;",
        "Dòng tiền vào–ra bất thường trên tài khoản mới mở;",
        "Giao dịch liên quan danh sách cảnh báo, cấm vận.",
    ])
    s += [
        D("Điều 8. Lưu trữ hồ sơ nhận biết khách hàng"),
        B("Hồ sơ nhận biết khách hàng và hồ sơ, báo cáo phòng chống rửa tiền được lưu trữ **tối thiểu 10 (mười) năm** kể từ ngày đóng tài khoản hoặc hoàn thành giao dịch, theo Điều 10 Thông tư số 20/2024/TT-NHNN. **Thời hạn này được áp dụng thay cho thời hạn 05 năm tại Quy định bảo vệ dữ liệu cá nhân của khách hàng (Quyết định số 455/2025/QĐ-DDB) do đây là quy định của pháp luật chuyên ngành.**"),
        D("Điều 10. Điều khoản thi hành"),
        B("Quyết định này có hiệu lực thi hành kể từ ngày **01 tháng 5 năm 2025**."),
    ]
    s += sign_block("TỔNG GIÁM ĐỐC\n(mô phỏng)", "Lê Văn C",
                    extra_left=noinhan(["Ban Tổng Giám đốc", "Khối Pháp chế và Tuân thủ", "Bộ phận AML", "Lưu: VT, PC"]))
    build_pdf("10_QD_480_2025_QD-DDB_KYC_phong_chong_rua_tien.pdf", s)


if __name__ == "__main__":
    print("Đang sinh bộ văn bản mô phỏng (bản enrich) ...")
    doc_nd88()
    doc_tt09()
    doc_tt04()
    doc_qd215()
    doc_qd342()
    doc_qd401()
    doc_qd455()
    doc_qd502()
    doc_tt20()
    doc_qd480()
    print("Xong 10 văn bản.")
