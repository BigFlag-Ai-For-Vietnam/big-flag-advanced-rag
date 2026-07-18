# -*- coding: utf-8 -*-
"""Nội dung 40 văn bản mô phỏng BỔ SUNG (tài liệu 11–50) — corpus v2 tăng retrieval pressure.

Thiết kế theo sample_compliance_corpus/GROUND_TRUTH_V2.md (ĐỌC FILE ĐÓ TRƯỚC — đáp án dựng
trước, nội dung ở đây phải khớp từng con số). Chạy: python docs_content_v2.py
"""
from reportlab.lib.units import cm
from reportlab.platypus import Spacer
from gen_corpus import (
    esc, P, S, Paragraph, build_pdf, state_header, internal_header,
    sign_block, noinhan, value_table,
)

DOCS = []


def register(fn):
    DOCS.append(fn)
    return fn


def sp(h=6):
    return Spacer(1, h)


def H(t):
    return Paragraph(esc(t), S["chuong"])


def D(t):
    return Paragraph(esc(t), S["dieu"])


def B(t):
    return P(t, "body")


def K(t):
    return P(t, "khoan")


def CC(t):
    return P(t, "cancu")


def bullets(items):
    return [P("– " + it, "khoan") for it in items]


def tbl_block(title, rows, widths):
    return [D(title), value_table(rows, widths), sp(4)]


# ------------------------------------------------------------------ boilerplate v2
# Trùng lặp boilerplate giữa các văn bản là CÓ CHỦ ĐÍCH (nhiễu tự nhiên cho dense/BM25).

def qd_opening(can_cu, de_nghi="Giám đốc Khối Pháp chế và Tuân thủ"):
    """Phần mở đầu Quyết định nội bộ: thẩm quyền + căn cứ + 'QUYẾT ĐỊNH:'."""
    out = [P("TỔNG GIÁM ĐỐC NGÂN HÀNG TMCP ĐÔNG ĐÔ", "trichyeu"),
           CC("Căn cứ Điều lệ tổ chức và hoạt động của Ngân hàng TMCP Đông Đô;")]
    out += [CC(c) for c in can_cu]
    out += [CC("Theo đề nghị của %s," % de_nghi), sp(), H("QUYẾT ĐỊNH:")]
    return out


def dieu_phamvi(so, doi_tuong, noi_dung):
    """Điều phạm vi điều chỉnh + đối tượng áp dụng (boilerplate có tham số)."""
    return [
        D("Điều %d. Phạm vi điều chỉnh và đối tượng áp dụng" % so),
        K("1. Văn bản này quy định về %s tại Ngân hàng TMCP Đông Đô (DongDoBank - DDB)." % noi_dung),
        K("2. Đối tượng áp dụng: %s." % doi_tuong),
    ]


def dieu_giaithich(so, terms):
    out = [D("Điều %d. Giải thích từ ngữ" % so)]
    for i, (t, d) in enumerate(terms, 1):
        out.append(K("%d. **%s** là %s" % (i, t, d)))
    return out


def chuong_tochuc(so, duties):
    """Chương Tổ chức thực hiện: duties = [(đơn vị, [nhiệm vụ,...]), ...]."""
    out = [H("Chương cuối. TỔ CHỨC THỰC HIỆN"),
           D("Điều %d. Trách nhiệm của các đơn vị" % so)]
    for unit, ds in duties:
        out.append(K("**%s:**" % unit))
        out += bullets(ds)
    return out


def dieu_kiemtra(so, extra=""):
    body = ("Khối Kiểm toán nội bộ và Khối Pháp chế và Tuân thủ định kỳ kiểm tra việc tuân thủ "
            "văn bản này. Cá nhân, đơn vị vi phạm bị xử lý theo Quy chế xử lý kỷ luật lao động "
            "của Ngân hàng; trường hợp gây thiệt hại phải bồi thường theo quy định pháp luật.")
    if extra:
        body += " " + extra
    return [D("Điều %d. Kiểm tra, giám sát và xử lý vi phạm" % so), B(body)]


def dieu_hieuluc(so, ngay, thaythe="", extra=""):
    body = "Văn bản này có hiệu lực thi hành kể từ ngày **%s**." % ngay
    if thaythe:
        body += " " + thaythe
    if extra:
        body += " " + extra
    return [D("Điều %d. Hiệu lực thi hành" % so), B(body)]


def ky_tgd(ten="Lê Văn C", noinhan_items=None):
    return sign_block("TỔNG GIÁM ĐỐC\n(mô phỏng)", ten,
                      extra_left=noinhan(noinhan_items or
                                         ["Ban Tổng Giám đốc", "Các Khối/Trung tâm/Chi nhánh",
                                          "Lưu: VT, PC"]))


def ky_ptgd(ten="Phạm Thị D", noinhan_items=None):
    return sign_block("KT. TỔNG GIÁM ĐỐC\nPHÓ TỔNG GIÁM ĐỐC\n(mô phỏng)", ten,
                      extra_left=noinhan(noinhan_items or
                                         ["Ban Tổng Giám đốc", "Các đơn vị liên quan", "Lưu: VT"]))


# =====================================================================
# NHÓM A — GIAO DỊCH ĐIỆN TỬ & XÁC THỰC (chuỗi phiên bản chính)
# =====================================================================

# 11 — NĐ 52/2024/NĐ-CP — Giao dịch điện tử tài chính-ngân hàng (STATE tầng 1)
@register
def doc_nd52():
    s = []
    s += state_header(
        "52/2024/NĐ-CP", "CHÍNH PHỦ", "NGHỊ ĐỊNH",
        "Về giao dịch điện tử trong hoạt động tài chính - ngân hàng",
        "Hà Nội, ngày 20 tháng 5 năm 2024",
    )
    s += [
        CC("Căn cứ Luật Tổ chức Chính phủ ngày 19 tháng 6 năm 2015;"),
        CC("Căn cứ Luật Giao dịch điện tử ngày 22 tháng 6 năm 2023;"),
        CC("Căn cứ Luật Các tổ chức tín dụng ngày 18 tháng 01 năm 2024;"),
        CC("Theo đề nghị của Thống đốc Ngân hàng Nhà nước Việt Nam;"),
        B("Chính phủ ban hành Nghị định về giao dịch điện tử trong hoạt động tài chính - ngân hàng."),
        sp(),
        H("Chương I. QUY ĐỊNH CHUNG"),
        D("Điều 1. Phạm vi điều chỉnh"),
        B("Nghị định này quy định về việc thực hiện giao dịch bằng phương tiện điện tử trong hoạt động tài chính - ngân hàng, bao gồm chứng từ điện tử, chữ ký điện tử và bảo đảm an toàn cho hệ thống thông tin phục vụ giao dịch điện tử."),
    ]
    s += dieu_giaithich(2, [
        ("Chứng từ điện tử", "chứng từ được tạo lập, gửi, nhận và lưu trữ bằng phương tiện điện tử trong hoạt động tài chính - ngân hàng."),
        ("Chữ ký điện tử an toàn", "chữ ký điện tử được tạo lập bằng biện pháp kiểm soát riêng của người ký và cho phép phát hiện mọi thay đổi sau thời điểm ký."),
        ("Phương tiện xác thực giao dịch", "mã khóa bí mật dùng một lần (OTP), chứng thư chữ ký số, yếu tố sinh trắc học hoặc các yếu tố tương đương dùng để xác nhận ý chí của khách hàng."),
    ])
    s += [
        D("Điều 4. Giá trị pháp lý của chứng từ điện tử"),
        K("1. Chứng từ điện tử có giá trị pháp lý như chứng từ giấy khi bảo đảm tính toàn vẹn, xác thực được người khởi tạo và định dạng cho phép truy cập, sử dụng được."),
        K("2. Chứng từ điện tử đã ký bằng chữ ký điện tử an toàn không bị phủ nhận giá trị pháp lý chỉ vì được thể hiện dưới dạng thông điệp dữ liệu."),
        D("Điều 7. Lưu trữ chứng từ điện tử"),
        B("Chứng từ điện tử phải được lưu trữ an toàn trong thời hạn **tối thiểu 10 (mười) năm** kể từ thời điểm hoàn thành giao dịch, bảo đảm khả năng truy xuất nguyên vẹn nội dung và lịch sử chỉnh sửa."),
        D("Điều 9. An toàn hệ thống thông tin phục vụ giao dịch điện tử"),
        K("1. Tổ chức cung cấp dịch vụ phải phân loại giao dịch theo mức độ rủi ro và áp dụng biện pháp xác thực tương xứng."),
        K("2. Ngân hàng Nhà nước Việt Nam hướng dẫn chi tiết về phân loại giao dịch, phương thức xác thực tối thiểu và hạn mức áp dụng đối với từng phương thức."),
        D("Điều 15. Hiệu lực thi hành"),
        B("Nghị định này có hiệu lực thi hành kể từ ngày **05 tháng 6 năm 2024**."),
    ]
    s += sign_block("TM. CHÍNH PHỦ\nTHỦ TƯỚNG\n(mô phỏng)", "Nguyễn Văn A",
                    extra_left=noinhan(["Các Bộ, cơ quan ngang Bộ", "Ngân hàng Nhà nước Việt Nam",
                                        "Các tổ chức tín dụng", "Lưu: VT, KTTH"]))
    build_pdf("11_ND_52_2024_NDCP_giao_dich_dien_tu.pdf", s)


# 12 — TT 35/2024/TT-NHNN — An toàn giao dịch trực tuyến (STATE tầng 2, căn cứ NĐ 52)
@register
def doc_tt35():
    s = []
    s += state_header(
        "35/2024/TT-NHNN", "NGÂN HÀNG NHÀ NƯỚC\nVIỆT NAM", "THÔNG TƯ",
        "Quy định về an toàn, bảo mật cho việc cung cấp dịch vụ ngân hàng trên môi trường trực tuyến",
        "Hà Nội, ngày 20 tháng 11 năm 2024",
    )
    s += [
        CC("Căn cứ Luật Ngân hàng Nhà nước Việt Nam ngày 16 tháng 6 năm 2010;"),
        CC("Căn cứ Luật Các tổ chức tín dụng ngày 18 tháng 01 năm 2024;"),
        CC("Căn cứ Nghị định số 52/2024/NĐ-CP ngày 20 tháng 5 năm 2024 của Chính phủ về giao dịch điện tử trong hoạt động tài chính - ngân hàng;"),
        CC("Theo đề nghị của Cục trưởng Cục Công nghệ thông tin;"),
        B("Thống đốc Ngân hàng Nhà nước Việt Nam ban hành Thông tư quy định về an toàn, bảo mật cho việc cung cấp dịch vụ ngân hàng trên môi trường trực tuyến."),
        sp(),
        D("Điều 1. Phạm vi điều chỉnh và đối tượng áp dụng"),
        B("Thông tư này quy định các yêu cầu an toàn, bảo mật tối thiểu khi cung cấp dịch vụ ngân hàng trực tuyến cho khách hàng; áp dụng đối với tổ chức tín dụng, chi nhánh ngân hàng nước ngoài và tổ chức cung ứng dịch vụ trung gian thanh toán."),
    ]
    s += tbl_block("Điều 3. Phân loại giao dịch theo mức độ rủi ro", [
        ["Nhóm giao dịch", "Phạm vi giá trị (VND/giao dịch)", "Ghi chú"],
        ["Nhóm I", "Đến 5.000.000", "Tra cứu, thanh toán giá trị nhỏ"],
        ["Nhóm II", "Trên 5.000.000 đến 10.000.000", "Chuyển tiền giá trị thấp"],
        ["Nhóm III", "Trên 10.000.000 đến 500.000.000", "Chuyển tiền giá trị trung bình - cao"],
        ["Nhóm IV", "Trên 500.000.000", "Giao dịch giá trị lớn"],
    ], [3 * cm, 8 * cm, 5.5 * cm])
    s += tbl_block("Điều 5. Phương thức xác thực tối thiểu theo nhóm giao dịch", [
        ["Nhóm", "Phương thức xác thực tối thiểu"],
        ["Nhóm I", "Mã khóa bí mật (mật khẩu) hoặc SMS OTP"],
        ["Nhóm II", "SMS OTP hoặc Soft OTP"],
        ["Nhóm III", "**Soft OTP kết hợp xác thực bằng dấu hiệu sinh trắc học** của khách hàng"],
        ["Nhóm IV", "Soft OTP nâng cao hoặc chữ ký số, kết hợp sinh trắc học"],
    ], [3 * cm, 13.5 * cm])
    s += [
        D("Điều 6. Xác thực sinh trắc học bắt buộc"),
        K("1. Việc chuyển tiền trên môi trường trực tuyến có giá trị **trên 10.000.000 (mười triệu) đồng/giao dịch** phải được xác thực bằng dấu hiệu sinh trắc học của khách hàng khớp đúng với dữ liệu sinh trắc học đã được kiểm tra với cơ sở dữ liệu định danh."),
        K("2. Trường hợp giá trị từng giao dịch không vượt ngưỡng tại khoản 1 nhưng **tổng giá trị giao dịch trong ngày vượt 20.000.000 (hai mươi triệu) đồng**, giao dịch kế tiếp phải xác thực bằng sinh trắc học."),
        K("3. SMS OTP chỉ được sử dụng cho giao dịch thuộc nhóm I và nhóm II."),
        D("Điều 8. Trách nhiệm của tổ chức cung cấp dịch vụ"),
    ]
    s += bullets([
        "Xây dựng quy định nội bộ về hạn mức và phương thức xác thực, không thấp hơn yêu cầu tối thiểu tại Thông tư này;",
        "Giám sát giao dịch bất thường và cảnh báo khách hàng theo thời gian thực;",
        "Bảo vệ dữ liệu sinh trắc học của khách hàng theo pháp luật về bảo vệ dữ liệu cá nhân;",
        "Báo cáo Ngân hàng Nhà nước khi xảy ra sự cố an toàn thông tin theo quy định hiện hành.",
    ])
    s += [
        D("Điều 12. Hiệu lực thi hành"),
        B("Thông tư này có hiệu lực thi hành kể từ ngày **01 tháng 01 năm 2025**."),
    ]
    s += sign_block("KT. THỐNG ĐỐC\nPHÓ THỐNG ĐỐC\n(mô phỏng)", "Trần Thị B",
                    extra_left=noinhan(["Các tổ chức tín dụng, chi nhánh NHNNg",
                                        "Cục Công nghệ thông tin", "Lưu: VT, CNTT"]))
    build_pdf("12_TT_35_2024_TT-NHNN_an_toan_giao_dich_truc_tuyen.pdf", s)


# 13 — QĐ 118/2021/QĐ-DDB — Ngân hàng điện tử v1 (BỊ THAY THẾ MỘT PHẦN — giữ Phụ lục 03)
@register
def doc_qd118():
    s = []
    s += internal_header(
        "118/2021/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định cung cấp và sử dụng dịch vụ Ngân hàng điện tử",
        "Hà Nội, ngày 01 tháng 3 năm 2021",
    )
    s += qd_opening(
        ["Căn cứ quy định của Ngân hàng Nhà nước về an toàn, bảo mật trong hoạt động ngân hàng điện tử;"],
        "Giám đốc Khối Ngân hàng số",
    )
    s += dieu_phamvi(1, "các đơn vị kinh doanh, Khối Ngân hàng số, Trung tâm Công nghệ thông tin và khách hàng sử dụng dịch vụ",
                     "việc cung cấp, quản lý và sử dụng dịch vụ Ngân hàng điện tử (Internet Banking, Mobile Banking)")
    s += dieu_giaithich(2, [
        ("Dịch vụ Ngân hàng điện tử", "dịch vụ ngân hàng được cung cấp qua kênh Internet Banking và ứng dụng Mobile Banking của DDB."),
        ("SMS OTP", "mã xác thực một lần gửi qua tin nhắn đến số điện thoại khách hàng đã đăng ký."),
        ("Soft OTP", "mã xác thực một lần sinh bởi phần mềm cài đặt trên thiết bị di động của khách hàng."),
    ])
    s += [
        D("Điều 5. Đăng ký và kích hoạt dịch vụ"),
        K("1. Khách hàng đăng ký dịch vụ tại quầy hoặc qua kênh trực tuyến với xác minh danh tính theo quy định nhận biết khách hàng của Ngân hàng."),
        K("2. Thiết bị kích hoạt Soft OTP phải được định danh và gắn với duy nhất một khách hàng tại một thời điểm."),
        D("Điều 7. Phương thức xác thực giao dịch"),
        K("1. Giao dịch chuyển tiền có giá trị **đến 100.000.000 (một trăm triệu) đồng/giao dịch** được xác thực bằng **SMS OTP** hoặc Soft OTP."),
        K("2. Giao dịch trên 100.000.000 đồng/giao dịch phải xác thực bằng Soft OTP."),
        K("3. Hạn mức giao dịch theo từng kênh thực hiện theo **Phụ lục 03** ban hành kèm theo Quyết định này."),
        D("Điều 9. Tạm khóa và chấm dứt dịch vụ"),
        B("Ngân hàng tạm khóa dịch vụ khi phát hiện dấu hiệu gian lận, đăng nhập bất thường hoặc theo đề nghị của khách hàng; việc mở khóa thực hiện sau khi xác minh lại danh tính."),
    ]
    s += chuong_tochuc(11, [
        ("Khối Ngân hàng số", ["Vận hành dịch vụ, quản lý hạn mức và phương thức xác thực;",
                               "Đầu mối rà soát, đề xuất sửa đổi Quy định này;"]),
        ("Trung tâm Công nghệ thông tin", ["Bảo đảm hạ tầng, an toàn hệ thống cung cấp dịch vụ;"]),
        ("Đơn vị kinh doanh", ["Hướng dẫn khách hàng đăng ký, sử dụng dịch vụ đúng quy định;"]),
    ])
    s += dieu_hieuluc(12, "15 tháng 3 năm 2021",
                      extra="Phụ lục 01, 02, 03 ban hành kèm theo là bộ phận không tách rời của Quyết định này.")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối Ngân hàng số", "TT CNTT", "Lưu: VT, NHS"])
    s += [
        sp(10),
        H("PHỤ LỤC 03 — BIỂU HẠN MỨC GIAO DỊCH THEO KÊNH"),
        P("(Ban hành kèm theo Quyết định số 118/2021/QĐ-DDB)", "cancu"),
    ]
    s += [value_table([
        ["Kênh giao dịch", "Hạn mức tối đa/giao dịch", "Hạn mức tối đa/ngày"],
        ["Internet Banking (KHCN)", "1.000.000.000 VND", "**3.000.000.000 VND**"],
        ["Mobile Banking (KHCN)", "500.000.000 VND", "**1.000.000.000 VND**"],
        ["Thanh toán QR", "50.000.000 VND", "200.000.000 VND"],
        ["Rút tiền ATM", "Theo Quy định về thẻ hiện hành", "Theo Quy định về thẻ hiện hành"],
    ], [5.5 * cm, 5.5 * cm, 5.5 * cm]), sp(4),
        P("Ghi chú: Hạn mức áp dụng cho khách hàng cá nhân hạng chuẩn; hạng ưu tiên và khách hàng tổ chức theo thỏa thuận riêng nhưng không vượt quá 02 lần biểu trên.", "khoan")]
    build_pdf("13_QD_118_2021_QD-DDB_ngan_hang_dien_tu_v1_BI_THAY_THE_MOT_PHAN.pdf", s)


# 14 — QĐ 267/2023/QĐ-DDB — SỬA ĐỔI QĐ 118 (hết hiệu lực cùng 118 khi 385 thay thế)
@register
def doc_qd267():
    s = []
    s += internal_header(
        "267/2023/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc sửa đổi, bổ sung một số điều của Quy định cung cấp và sử dụng dịch vụ Ngân hàng điện tử ban hành kèm theo Quyết định số 118/2021/QĐ-DDB",
        "Hà Nội, ngày 01 tháng 8 năm 2023",
    )
    s += qd_opening(
        ["Căn cứ Quyết định số 118/2021/QĐ-DDB ngày 01 tháng 3 năm 2021 của Tổng Giám đốc về dịch vụ Ngân hàng điện tử;",
         "Căn cứ kết quả đánh giá rủi ro gian lận qua kênh số 6 tháng đầu năm 2023;"],
        "Giám đốc Khối Ngân hàng số",
    )
    s += [
        D("Điều 1. Sửa đổi, bổ sung Điều 7 Quyết định số 118/2021/QĐ-DDB"),
        K("1. Sửa đổi khoản 1 Điều 7 như sau: “Giao dịch chuyển tiền có giá trị **đến 50.000.000 (năm mươi triệu) đồng/giao dịch** được xác thực bằng SMS OTP hoặc Soft OTP.”"),
        K("2. Sửa đổi khoản 2 Điều 7 như sau: “Giao dịch **trên 50.000.000 đồng/giao dịch** phải được xác thực bằng **Soft OTP**; khuyến khích áp dụng thêm yếu tố sinh trắc học trên thiết bị.”"),
        D("Điều 2. Điều khoản thi hành"),
        K("1. Quyết định này có hiệu lực kể từ ngày **10 tháng 8 năm 2023**."),
        K("2. Các nội dung khác của Quyết định số 118/2021/QĐ-DDB, bao gồm các Phụ lục ban hành kèm theo, giữ nguyên hiệu lực thi hành."),
    ]
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối Ngân hàng số", "TT CNTT", "Lưu: VT, NHS"])
    build_pdf("14_QD_267_2023_QD-DDB_sua_doi_QD118_HET_HIEU_LUC.pdf", s)


# 15 — QĐ 385/2025/QĐ-DDB — Kênh số v2 (hiện hành; thay 118+267 TRỪ Phụ lục 03)
@register
def doc_qd385():
    s = []
    s += internal_header(
        "385/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định cung cấp và sử dụng dịch vụ ngân hàng trên kênh số",
        "Hà Nội, ngày 05 tháng 6 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Thông tư số 35/2024/TT-NHNN ngày 20 tháng 11 năm 2024 của Ngân hàng Nhà nước quy định về an toàn, bảo mật cho việc cung cấp dịch vụ ngân hàng trên môi trường trực tuyến;"],
        "Giám đốc Khối Ngân hàng số",
    )
    s += dieu_phamvi(1, "các đơn vị kinh doanh, Khối Ngân hàng số, Trung tâm Công nghệ thông tin và khách hàng sử dụng kênh số",
                     "việc cung cấp, quản lý và sử dụng dịch vụ ngân hàng trên kênh số (Internet Banking, Mobile Banking, QR)")
    s += [
        D("Điều 4. Phương thức xác thực giao dịch"),
        K("1. Phân loại giao dịch và phương thức xác thực tối thiểu thực hiện theo Điều 3, Điều 5 và Điều 6 Thông tư số 35/2024/TT-NHNN; **Soft OTP là phương thức xác thực mặc định** trên kênh số của DDB."),
        K("2. Áp dụng nội bộ chặt hơn quy định tối thiểu: **SMS OTP chỉ được sử dụng cho giao dịch có giá trị đến 5.000.000 (năm triệu) đồng/giao dịch**."),
        K("3. Giao dịch chuyển tiền **trên 10.000.000 đồng/giao dịch** hoặc khi tổng giá trị giao dịch trong ngày **vượt 20.000.000 đồng** phải xác thực bằng **dấu hiệu sinh trắc học** khớp đúng dữ liệu đã đăng ký, theo Điều 6 Thông tư số 35/2024/TT-NHNN."),
        D("Điều 6. Thiết bị tin cậy và quản lý phiên"),
        K("1. Mỗi khách hàng chỉ kích hoạt Soft OTP trên tối đa 02 thiết bị đã định danh; việc đổi thiết bị phải xác thực lại bằng sinh trắc học."),
        K("2. Ứng dụng phải hiển thị lịch sử đăng nhập và cho phép khách hàng chủ động hủy phiên trên thiết bị khác."),
        D("Điều 8. Hạn mức giao dịch theo kênh"),
        B("Trong thời gian Ngân hàng chưa ban hành biểu hạn mức mới, hạn mức giao dịch theo từng kênh **tiếp tục thực hiện theo Phụ lục 03 ban hành kèm theo Quyết định số 118/2021/QĐ-DDB**."),
        D("Điều 9. Giám sát gian lận"),
        B("Khối Ngân hàng số phối hợp Trung tâm Công nghệ thông tin giám sát giao dịch bất thường theo thời gian thực; các biện pháp hạn chế tạm thời khi có chiến dịch tấn công được ban hành bằng Thông báo riêng và tự động hết hiệu lực theo thời hạn ghi trong Thông báo."),
    ]
    s += chuong_tochuc(11, [
        ("Khối Ngân hàng số", ["Vận hành dịch vụ và các phương thức xác thực;",
                               "Trình ban hành biểu hạn mức mới thay thế Phụ lục 03 Quyết định 118/2021/QĐ-DDB;"]),
        ("Trung tâm Công nghệ thông tin", ["Bảo đảm hạ tầng, giám sát an toàn hệ thống kênh số;"]),
        ("Đơn vị kinh doanh", ["Hỗ trợ khách hàng đăng ký sinh trắc học và thiết bị tin cậy;"]),
    ])
    s += dieu_kiemtra(12)
    s += dieu_hieuluc(
        13, "01 tháng 7 năm 2025",
        thaythe=("Quyết định này **thay thế Quyết định số 118/2021/QĐ-DDB và Quyết định số 267/2023/QĐ-DDB**, "
                 "**trừ Phụ lục 03 ban hành kèm theo Quyết định số 118/2021/QĐ-DDB tiếp tục có hiệu lực** "
                 "cho đến khi Ngân hàng ban hành biểu hạn mức giao dịch mới."),
    )
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối Ngân hàng số", "TT CNTT", "Các CN/PGD", "Lưu: VT, NHS"])
    build_pdf("15_QD_385_2025_QD-DDB_kenh_so_v2.pdf", s)


# 16 — TB 51/2025/TB-DDB — Triển khai QĐ 385 + điều khoản chuyển tiếp
@register
def doc_tb51():
    s = []
    s += internal_header(
        "51/2025/TB-DDB", "THÔNG BÁO",
        "Về việc triển khai Quy định kênh số theo Quyết định số 385/2025/QĐ-DDB và lộ trình chuyển tiếp xác thực sinh trắc học",
        "Hà Nội, ngày 20 tháng 6 năm 2025",
    )
    s += [
        B("Ngày 05/6/2025, Tổng Giám đốc đã ký Quyết định số 385/2025/QĐ-DDB ban hành Quy định cung cấp và sử dụng dịch vụ ngân hàng trên kênh số, có hiệu lực từ **01/7/2025**. Ngân hàng thông báo lộ trình triển khai như sau:"),
        D("1. Giai đoạn chuyển tiếp (từ 01/7/2025 đến hết 30/9/2025)"),
        K("a) Khách hàng **chưa hoàn thành đăng ký dữ liệu sinh trắc học** được tiếp tục sử dụng **Soft OTP cho giao dịch có giá trị đến 20.000.000 (hai mươi triệu) đồng/giao dịch**; giao dịch vượt mức này phải thực hiện tại quầy."),
        K("b) Ứng dụng hiển thị nhắc đăng ký sinh trắc học mỗi lần đăng nhập trong giai đoạn chuyển tiếp."),
        D("2. Từ ngày 01/10/2025"),
        K("Toàn bộ giao dịch chuyển tiền trên 10.000.000 đồng/giao dịch bắt buộc xác thực sinh trắc học theo đúng Quyết định số 385/2025/QĐ-DDB và Thông tư số 35/2024/TT-NHNN; khách hàng chưa đăng ký sẽ bị giới hạn ở nhóm giao dịch I, II."),
        D("3. Tổ chức thực hiện"),
        K("Đơn vị kinh doanh hỗ trợ khách hàng thu thập sinh trắc học tại quầy; Khối Ngân hàng số báo cáo tiến độ hằng tuần về Ban Tổng Giám đốc."),
        B("Thông báo này là văn bản triển khai, hướng dẫn chuyển tiếp cho Quyết định số 385/2025/QĐ-DDB và hết hiệu lực khi kết thúc lộ trình nêu trên."),
    ]
    s += ky_ptgd("Phạm Thị D", ["Các đơn vị kinh doanh", "Khối Ngân hàng số", "Lưu: VT"])
    build_pdf("16_TB_51_2025_TB-DDB_trien_khai_QD385_chuyen_tiep.pdf", s)


# =====================================================================
# NHÓM B — HẠ TẦNG CNTT & SỰ CỐ
# =====================================================================

# 17 — QĐ 173/2023/QĐ-DDB — Phân loại hệ thống CNTT (dẫn chiếu PL02 QĐ 215)
@register
def doc_qd173():
    s = []
    s += internal_header(
        "173/2023/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định phân loại và quản lý hệ thống công nghệ thông tin",
        "Hà Nội, ngày 05 tháng 5 năm 2023",
    )
    s += qd_opening(
        ["Căn cứ Quy chế An toàn thông tin hiện hành của Ngân hàng;"],
        "Giám đốc Trung tâm Công nghệ thông tin",
    )
    s += dieu_phamvi(1, "Trung tâm Công nghệ thông tin, các đơn vị chủ quản nghiệp vụ của hệ thống",
                     "nguyên tắc phân loại, danh mục và yêu cầu quản lý đối với các hệ thống công nghệ thông tin")
    s += tbl_block("Điều 3. Phân loại hệ thống công nghệ thông tin", [
        ["Mức phân loại", "Tiêu chí chính", "Ví dụ"],
        ["Hệ thống trọng yếu", "Gián đoạn gây ảnh hưởng nghiêm trọng đến hoạt động thanh toán, dữ liệu khách hàng hoặc nghĩa vụ với NHNN", "Core banking, hệ thống thanh toán, kênh số"],
        ["Hệ thống quan trọng", "Gián đoạn ảnh hưởng một mảng nghiệp vụ, có phương án thủ công thay thế ngắn hạn", "Quản lý thẻ, LOS tín dụng"],
        ["Hệ thống thông thường", "Gián đoạn không ảnh hưởng trực tiếp khách hàng", "Cổng thông tin nội bộ, đào tạo trực tuyến"],
    ], [3.8 * cm, 8.2 * cm, 4.5 * cm])
    s += [
        D("Điều 5. Danh mục hệ thống trọng yếu"),
        K("1. **Danh mục hệ thống thông tin trọng yếu của Ngân hàng thực hiện theo Phụ lục 02 ban hành kèm theo Quyết định số 215/2022/QĐ-DDB** (Quy chế An toàn thông tin); mọi cập nhật danh mục phải được Tổng Giám đốc phê duyệt."),
        K("2. Trung tâm Công nghệ thông tin rà soát danh mục **tối thiểu mỗi năm một lần** hoặc khi triển khai hệ thống mới."),
        D("Điều 7. Yêu cầu quản lý theo mức phân loại"),
    ]
    s += bullets([
        "Hệ thống trọng yếu: giám sát 24/7, đánh giá an toàn định kỳ hằng năm, phương án dự phòng thảm họa bắt buộc;",
        "Hệ thống quan trọng: giám sát trong giờ vận hành mở rộng, đánh giá an toàn 02 năm/lần;",
        "Hệ thống thông thường: quản lý theo quy trình vận hành tiêu chuẩn.",
    ])
    s += chuong_tochuc(9, [
        ("Trung tâm Công nghệ thông tin", ["Chủ trì phân loại, trình phê duyệt danh mục;",
                                           "Áp dụng biện pháp quản lý tương ứng từng mức;"]),
        ("Đơn vị chủ quản nghiệp vụ", ["Cung cấp đánh giá tác động nghiệp vụ khi phân loại;"]),
    ])
    s += dieu_hieuluc(10, "12 tháng 5 năm 2023")
    s += ky_ptgd("Phạm Thị D", ["Ban Tổng Giám đốc", "TT CNTT", "Các đơn vị chủ quản", "Lưu: VT, CNTT"])
    build_pdf("17_QD_173_2023_QD-DDB_phan_loai_he_thong_CNTT.pdf", s)


# 18 — QĐ 356/2024/QĐ-DDB — Sao lưu & khôi phục (RTO/RPO theo phân loại 173)
@register
def doc_qd356():
    s = []
    s += internal_header(
        "356/2024/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định sao lưu dữ liệu và khôi phục hệ thống sau thảm họa",
        "Hà Nội, ngày 12 tháng 9 năm 2024",
    )
    s += qd_opening(
        ["Căn cứ Quyết định số 173/2023/QĐ-DDB ngày 05 tháng 5 năm 2023 về phân loại và quản lý hệ thống công nghệ thông tin;"],
        "Giám đốc Trung tâm Công nghệ thông tin",
    )
    s += dieu_giaithich(2, [
        ("RPO (Recovery Point Objective)", "lượng dữ liệu tối đa (tính theo thời gian) có thể chấp nhận mất khi xảy ra sự cố."),
        ("RTO (Recovery Time Objective)", "thời gian tối đa cho phép để khôi phục hệ thống hoạt động trở lại sau thảm họa."),
    ])
    s += tbl_block("Điều 4. Mục tiêu khôi phục theo mức phân loại hệ thống", [
        ["Mức hệ thống (theo QĐ 173/2023/QĐ-DDB)", "RPO tối đa", "RTO tối đa", "Tần suất sao lưu"],
        ["Trọng yếu", "**15 phút**", "**02 giờ**", "Sao lưu liên tục (near-realtime)"],
        ["Quan trọng", "04 giờ", "08 giờ", "04 giờ/lần"],
        ["Thông thường", "24 giờ", "72 giờ", "Hằng ngày"],
    ], [6.5 * cm, 2.8 * cm, 2.8 * cm, 4.4 * cm])
    s += [
        D("Điều 6. Diễn tập khôi phục"),
        K("1. Hệ thống trọng yếu phải diễn tập chuyển đổi sang trung tâm dự phòng **tối thiểu 01 lần/năm**; kết quả báo cáo Tổng Giám đốc."),
        K("2. Bản sao lưu phải được kiểm tra tính toàn vẹn định kỳ hằng quý và lưu tách biệt về vật lý hoặc logic với hệ thống chính."),
        D("Điều 8. Kích hoạt phương án khôi phục"),
        B("Việc kích hoạt phương án khôi phục sau thảm họa thực hiện theo quy trình quản lý sự cố công nghệ thông tin hiện hành; sự cố mức 3 đương nhiên kích hoạt đánh giá chuyển đổi trung tâm dự phòng."),
    ]
    s += chuong_tochuc(10, [
        ("Trung tâm Công nghệ thông tin", ["Vận hành sao lưu, bảo đảm mục tiêu RPO/RTO;",
                                           "Tổ chức diễn tập và báo cáo kết quả;"]),
        ("Đơn vị chủ quản nghiệp vụ", ["Phối hợp kiểm thử nghiệp vụ sau khôi phục;"]),
    ])
    s += dieu_kiemtra(11)
    s += dieu_hieuluc(12, "20 tháng 9 năm 2024")
    s += ky_ptgd("Phạm Thị D", ["Ban Tổng Giám đốc", "TT CNTT", "Lưu: VT, CNTT"])
    build_pdf("18_QD_356_2024_QD-DDB_sao_luu_khoi_phuc.pdf", s)


# 19 — QĐ 428/2025/QĐ-DDB — Quản lý sự cố CNTT (2 giờ nội bộ)
@register
def doc_qd428():
    s = []
    s += internal_header(
        "428/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định quản lý và ứng cứu sự cố công nghệ thông tin",
        "Hà Nội, ngày 10 tháng 2 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Quy chế An toàn thông tin ban hành kèm theo Quyết định số 342/2024/QĐ-DDB;",
         "Căn cứ Quyết định số 356/2024/QĐ-DDB về sao lưu dữ liệu và khôi phục hệ thống sau thảm họa;"],
        "Giám đốc Trung tâm Công nghệ thông tin",
    )
    s += tbl_block("Điều 3. Phân loại mức độ sự cố", [
        ["Mức", "Mô tả", "Ví dụ"],
        ["Mức 1 (thấp)", "Ảnh hưởng cục bộ, một người dùng hoặc một thiết bị", "Máy trạm lỗi, tài khoản bị khóa"],
        ["Mức 2 (trung bình)", "Ảnh hưởng một đơn vị hoặc một dịch vụ không trọng yếu", "Hệ thống LOS chậm trên diện rộng"],
        ["Mức 3 (nghiêm trọng)", "Ảnh hưởng hệ thống trọng yếu, dữ liệu khách hàng hoặc nhiều đơn vị", "Core banking gián đoạn, nghi ngờ lộ dữ liệu"],
    ], [3.2 * cm, 7 * cm, 6.3 * cm])
    s += [
        D("Điều 5. Tiếp nhận và báo cáo sự cố"),
        K("1. Mọi cán bộ phát hiện sự cố phải ghi nhận vào hệ thống quản lý sự cố hoặc báo bộ phận trực Trung tâm Công nghệ thông tin."),
        K("2. **Sự cố từ mức 2 trở lên phải được báo cáo về Trung tâm Công nghệ thông tin trong vòng 02 (hai) giờ** kể từ khi phát hiện; sự cố mức 3 đồng thời báo cáo ngay Ban Tổng Giám đốc."),
        K("3. Việc báo cáo sự cố cho Ngân hàng Nhà nước và các nghĩa vụ thông báo bên ngoài thực hiện theo Quy định báo cáo sự cố an toàn thông tin hiện hành của Ngân hàng."),
        D("Điều 6. Ứng cứu và khắc phục"),
        K("1. Sự cố mức 3 kích hoạt đội ứng cứu sự cố và đánh giá kích hoạt phương án khôi phục theo Quyết định số 356/2024/QĐ-DDB."),
        K("2. Trong vòng **05 ngày làm việc** sau khi khắc phục sự cố mức 2 trở lên, đơn vị đầu mối phải hoàn thành báo cáo phân tích nguyên nhân gốc và biện pháp phòng ngừa tái diễn."),
    ]
    s += chuong_tochuc(8, [
        ("Trung tâm Công nghệ thông tin", ["Trực tiếp nhận, điều phối ứng cứu 24/7;",
                                           "Duy trì hệ thống quản lý sự cố và kho tri thức;"]),
        ("Các đơn vị", ["Báo cáo đúng thời hạn, phối hợp ứng cứu và cung cấp thông tin;"]),
    ])
    s += dieu_kiemtra(9)
    s += dieu_hieuluc(10, "15 tháng 02 năm 2025")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "TT CNTT", "Các đơn vị", "Lưu: VT, CNTT"])
    build_pdf("19_QD_428_2025_QD-DDB_quan_ly_su_co_CNTT.pdf", s)


# 20 — QĐ 445/2025/QĐ-DDB — Báo cáo sự cố ATTT cho NHNN (24 giờ; nhắc NĐ 88 72h)
@register
def doc_qd445():
    s = []
    s += internal_header(
        "445/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định báo cáo sự cố an toàn thông tin cho cơ quan quản lý",
        "Hà Nội, ngày 05 tháng 3 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Thông tư số 09/2024/TT-NHNN về bảo đảm an toàn hệ thống thông tin trong hoạt động ngân hàng;",
         "Căn cứ Thông tư số 50/2025/TT-NHNN sửa đổi, bổ sung một số điều của Thông tư số 09/2024/TT-NHNN;",
         "Căn cứ Nghị định số 88/2024/NĐ-CP về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng;"],
        "Giám đốc Khối Pháp chế và Tuân thủ",
    )
    s += [
        D("Điều 2. Sự cố phải báo cáo Ngân hàng Nhà nước"),
        B("Sự cố an toàn thông tin nghiêm trọng — bao gồm gián đoạn hệ thống trọng yếu quá mục tiêu khôi phục, tấn công mạng thành công, hoặc nghi ngờ lộ, mất dữ liệu khách hàng — phải được báo cáo Ngân hàng Nhà nước (Cục Công nghệ thông tin) **trong vòng 24 (hai mươi bốn) giờ** kể từ khi phát hiện, theo Điều 11 Thông tư số 09/2024/TT-NHNN (đã được sửa đổi bởi Thông tư số 50/2025/TT-NHNN)."),
        D("Điều 3. Nghĩa vụ thông báo khi vi phạm dữ liệu cá nhân"),
        B("Trường hợp sự cố dẫn đến vi phạm dữ liệu cá nhân, ngoài nghĩa vụ tại Điều 2, Ngân hàng phải thông báo cho Ngân hàng Nhà nước và **chủ thể dữ liệu bị ảnh hưởng trong thời hạn 72 (bảy mươi hai) giờ** theo Điều 13 Nghị định số 88/2024/NĐ-CP."),
        D("Điều 4. Nội dung và hình thức báo cáo"),
    ]
    s += bullets([
        "Báo cáo lần đầu: mô tả sự cố, thời điểm phát hiện, phạm vi ảnh hưởng sơ bộ, biện pháp đã áp dụng;",
        "Báo cáo cập nhật: khi có thay đổi đáng kể về phạm vi hoặc mức độ ảnh hưởng;",
        "Báo cáo kết thúc: trong 05 ngày làm việc sau khi khắc phục, kèm phân tích nguyên nhân gốc;",
        "Hình thức: văn bản điện tử qua hệ thống báo cáo của Ngân hàng Nhà nước, đồng gửi thư điện tử.",
    ])
    s += [
        D("Điều 5. Đầu mối báo cáo"),
        B("Khối Pháp chế và Tuân thủ là đầu mối rà soát pháp lý và gửi báo cáo; Trung tâm Công nghệ thông tin cung cấp thông tin kỹ thuật theo quy trình quản lý sự cố nội bộ (Quyết định số 428/2025/QĐ-DDB)."),
    ]
    s += dieu_kiemtra(6)
    s += dieu_hieuluc(7, "10 tháng 3 năm 2025")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối PC&TT", "TT CNTT", "Lưu: VT, PC"])
    build_pdf("20_QD_445_2025_QD-DDB_bao_cao_su_co_NHNN.pdf", s)


# 21 — HD 12/2023/HD-DDB — Hướng dẫn vận hành TTDL (NOISE: viết theo QĐ 215 cũ)
@register
def doc_hd12():
    s = []
    s += internal_header(
        "12/2023/HD-DDB", "HƯỚNG DẪN",
        "Vận hành và bảo đảm an toàn Trung tâm dữ liệu",
        "Hà Nội, ngày 01 tháng 11 năm 2023",
    )
    s += [
        CC("Thực hiện Quy chế An toàn thông tin ban hành kèm theo Quyết định số 215/2022/QĐ-DDB;"),
        CC("Trung tâm Công nghệ thông tin hướng dẫn thống nhất việc vận hành Trung tâm dữ liệu như sau:"),
        sp(),
        D("1. Kiểm soát ra vào"),
        K("Việc ra vào khu vực Trung tâm dữ liệu phải được phê duyệt trước, sử dụng thẻ từ kết hợp sinh trắc học và ghi nhật ký tự động; khách bên ngoài phải có cán bộ giám sát đi kèm trong suốt thời gian làm việc."),
        D("2. Môi trường vận hành"),
        K("Nhiệt độ phòng thiết bị duy trì 22±2°C, độ ẩm 45–60%; hệ thống UPS và máy phát dự phòng được kiểm tra tải định kỳ hằng tháng; cảm biến khói, rò nước giám sát 24/7."),
        D("3. Tài khoản vận hành"),
        K("Tài khoản vận hành hệ thống tại Trung tâm dữ liệu đặt **mật khẩu tối thiểu 8 ký tự theo Điều 2 Quy chế An toàn thông tin (Quyết định số 215/2022/QĐ-DDB)**, thay đổi định kỳ và không dùng chung giữa các ca trực."),
        D("4. Nhật ký vận hành"),
        K("Ca trực ghi nhật ký đầy đủ các thao tác can thiệp thiết bị; nhật ký hệ thống lưu trữ **tối thiểu 06 tháng theo Quy chế An toàn thông tin hiện hành tại thời điểm ban hành Hướng dẫn này**."),
        D("5. Bảo trì định kỳ"),
        K("Lịch bảo trì thiết bị được lập hằng quý; việc bảo trì hệ thống đang phục vụ khách hàng phải thực hiện ngoài giờ giao dịch và có phương án hoàn tác."),
        sp(),
        P("Lưu ý: Hướng dẫn này được soạn theo Quy chế An toàn thông tin năm 2022; các đơn vị đối chiếu quy định hiện hành khi áp dụng.", "cancu"),
    ]
    s += ky_ptgd("Phạm Thị D", ["TT CNTT", "Ca trực TTDL", "Lưu: VT, CNTT"])
    build_pdf("21_HD_12_2023_HD-DDB_van_hanh_TTDL_LOI_THOI.pdf", s)


# 22 — TT 50/2025/TT-NHNN — SỬA ĐỔI TT 09/2024 (72h -> 24h; state-level amendment)
@register
def doc_tt50():
    s = []
    s += state_header(
        "50/2025/TT-NHNN", "NGÂN HÀNG NHÀ NƯỚC\nVIỆT NAM", "THÔNG TƯ",
        "Sửa đổi, bổ sung một số điều của Thông tư số 09/2024/TT-NHNN quy định về bảo đảm an toàn hệ thống thông tin trong hoạt động ngân hàng",
        "Hà Nội, ngày 28 tháng 3 năm 2025",
    )
    s += [
        CC("Căn cứ Luật Ngân hàng Nhà nước Việt Nam ngày 16 tháng 6 năm 2010;"),
        CC("Căn cứ Luật Các tổ chức tín dụng ngày 18 tháng 01 năm 2024;"),
        CC("Theo đề nghị của Cục trưởng Cục Công nghệ thông tin;"),
        B("Thống đốc Ngân hàng Nhà nước Việt Nam ban hành Thông tư sửa đổi, bổ sung một số điều của Thông tư số 09/2024/TT-NHNN."),
        sp(),
        D("Điều 1. Sửa đổi, bổ sung một số điều của Thông tư số 09/2024/TT-NHNN"),
        K("1. Sửa đổi khoản 1 Điều 11 như sau: “Tổ chức tín dụng phải báo cáo Ngân hàng Nhà nước (Cục Công nghệ thông tin) về sự cố an toàn thông tin nghiêm trọng **trong vòng 24 (hai mươi bốn) giờ** kể từ thời điểm phát hiện sự cố.”"),
        K("2. Bổ sung Điều 13a như sau: “Điều 13a. Diễn tập khôi phục sau thảm họa. Tổ chức tín dụng phải tổ chức diễn tập chuyển đổi hệ thống thông tin quan trọng sang trung tâm dự phòng **tối thiểu 01 (một) lần mỗi năm** và lưu hồ sơ kết quả diễn tập tối thiểu 05 năm.”"),
        D("Điều 2. Điều khoản thi hành"),
        K("1. Thông tư này có hiệu lực thi hành kể từ ngày **15 tháng 4 năm 2025**."),
        K("2. Các quy định khác của Thông tư số 09/2024/TT-NHNN giữ nguyên hiệu lực thi hành."),
    ]
    s += sign_block("KT. THỐNG ĐỐC\nPHÓ THỐNG ĐỐC\n(mô phỏng)", "Trần Thị B",
                    extra_left=noinhan(["Các tổ chức tín dụng, chi nhánh NHNNg",
                                        "Cục Công nghệ thông tin", "Lưu: VT, CNTT"]))
    build_pdf("22_TT_50_2025_TT-NHNN_sua_doi_TT09.pdf", s)


# =====================================================================
# NHÓM C — DỮ LIỆU CÁ NHÂN & MARKETING
# =====================================================================

# 23 — QĐ 133/2022/QĐ-DDB — Quản lý TTKH v1 (BỊ 455/2025 THAY THẾ TRỪ Phụ lục 01)
@register
def doc_qd133():
    s = []
    s += internal_header(
        "133/2022/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định quản lý thông tin khách hàng",
        "Hà Nội, ngày 01 tháng 6 năm 2022",
    )
    s += qd_opening(
        ["Căn cứ quy định pháp luật về bảo mật thông tin khách hàng của tổ chức tín dụng;"],
    )
    s += dieu_phamvi(1, "toàn bộ đơn vị, cán bộ nhân viên có tiếp cận thông tin khách hàng",
                     "việc thu thập, cập nhật, khai thác và bảo mật thông tin khách hàng")
    s += [
        D("Điều 3. Thu thập và cập nhật thông tin"),
        K("1. Thông tin khách hàng chỉ được thu thập cho mục đích cung cấp sản phẩm, dịch vụ và tuân thủ nghĩa vụ pháp lý của Ngân hàng."),
        K("2. Việc thu thập phải kèm theo văn bản đồng ý của khách hàng **theo Mẫu tại Phụ lục 01** ban hành kèm theo Quyết định này."),
        D("Điều 5. Khai thác thông tin"),
        B("Cán bộ chỉ được khai thác thông tin khách hàng trong phạm vi nhiệm vụ được giao; nghiêm cấm sao chép, chia sẻ thông tin ra ngoài hệ thống khi chưa được phê duyệt."),
        D("Điều 8. Thời hạn lưu giữ hồ sơ thông tin khách hàng"),
        B("Hồ sơ thông tin khách hàng được lưu giữ trong thời hạn **07 (bảy) năm** kể từ ngày khách hàng chấm dứt quan hệ với Ngân hàng, trừ trường hợp pháp luật có quy định khác."),
    ]
    s += chuong_tochuc(10, [
        ("Khối Vận hành", ["Quản lý kho hồ sơ khách hàng tập trung;"]),
        ("Đơn vị kinh doanh", ["Thu thập, cập nhật thông tin đúng mẫu và đúng mục đích;"]),
    ])
    s += dieu_hieuluc(11, "10 tháng 6 năm 2022",
                      extra="Phụ lục 01 (Mẫu văn bản đồng ý của khách hàng) là bộ phận không tách rời của Quyết định này.")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối Vận hành", "Các CN/PGD", "Lưu: VT"])
    s += [
        sp(10),
        H("PHỤ LỤC 01 — MẪU VĂN BẢN ĐỒNG Ý CỦA KHÁCH HÀNG"),
        P("(Ban hành kèm theo Quyết định số 133/2022/QĐ-DDB)", "cancu"),
        B("Tôi, [Họ tên khách hàng], số giấy tờ tùy thân [số CCCD/Hộ chiếu], đồng ý cho Ngân hàng TMCP Đông Đô thu thập và xử lý thông tin cá nhân của tôi cho các mục đích sau:"),
    ]
    s += bullets([
        "☐ Mở và quản lý tài khoản, cung cấp sản phẩm dịch vụ đã đăng ký;",
        "☐ Tuân thủ nghĩa vụ pháp lý của Ngân hàng (nhận biết khách hàng, phòng chống rửa tiền);",
        "☐ Nhận thông tin tiếp thị, giới thiệu sản phẩm (có thể rút lại bất kỳ lúc nào);",
        "☐ Mục đích khác (ghi rõ): ................................................",
    ])
    s += [B("Tôi hiểu rằng tôi có quyền yêu cầu truy cập, chỉnh sửa, xóa dữ liệu và rút lại sự đồng ý theo quy định pháp luật. Chữ ký khách hàng: .................... Ngày: ..../..../......")]
    build_pdf("23_QD_133_2022_QD-DDB_thong_tin_khach_hang_v1_BI_THAY_THE_MOT_PHAN.pdf", s)


# 24 — QĐ 476/2025/QĐ-DDB — Tiếp thị số & quản lý sự đồng ý
@register
def doc_qd476():
    s = []
    s += internal_header(
        "476/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định hoạt động tiếp thị trên kênh số và quản lý sự đồng ý của khách hàng",
        "Hà Nội, ngày 28 tháng 4 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Nghị định số 88/2024/NĐ-CP về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng;",
         "Căn cứ Quy định bảo vệ dữ liệu cá nhân của khách hàng ban hành kèm theo Quyết định số 455/2025/QĐ-DDB;"],
        "Giám đốc Khối Khách hàng cá nhân",
    )
    s += dieu_phamvi(1, "Khối Khách hàng cá nhân, Khối Khách hàng doanh nghiệp, Khối Ngân hàng số và các đơn vị kinh doanh",
                     "hoạt động tiếp thị, giới thiệu sản phẩm qua tin nhắn, thư điện tử và thông báo trên ứng dụng")
    s += [
        D("Điều 3. Nguyên tắc tiếp thị dựa trên sự đồng ý"),
        K("1. Chỉ gửi nội dung tiếp thị cho khách hàng **đã có sự đồng ý riêng cho mục đích tiếp thị**; sự đồng ý cho mục đích cung cấp dịch vụ không đương nhiên bao gồm mục đích tiếp thị."),
        K("2. **Việc sử dụng dữ liệu lịch sử giao dịch để phân tích và cá nhân hóa ưu đãi là mục đích khác với mục đích thu thập ban đầu**, phải được sự đồng ý mới của khách hàng theo khoản 2 Điều 5 Nghị định số 88/2024/NĐ-CP và Quyết định số 455/2025/QĐ-DDB."),
        D("Điều 4. Tần suất và khung giờ"),
        K("1. Gửi **tối đa 04 (bốn) tin nhắn/thư tiếp thị mỗi tháng** cho một khách hàng trên tất cả các kênh cộng lại."),
        K("2. Không gửi tin tiếp thị ngoài khung giờ 08h00–20h00; không gửi vào ngày lễ, Tết."),
        D("Điều 5. Quyền từ chối (opt-out)"),
        K("1. Mọi tin tiếp thị phải kèm hướng dẫn từ chối nhận tin đơn giản, miễn phí."),
        K("2. Yêu cầu từ chối phải được xử lý và có hiệu lực **trong vòng 72 (bảy mươi hai) giờ**; sau thời điểm này mọi tin tiếp thị gửi tới khách hàng là vi phạm."),
        D("Điều 6. Loại trừ"),
        B("Thông báo giao dịch, cảnh báo an toàn, thông tin thay đổi chính sách bắt buộc không được coi là tin tiếp thị và không chịu giới hạn tại Điều 4."),
    ]
    s += chuong_tochuc(8, [
        ("Khối Khách hàng cá nhân", ["Quản lý danh sách đồng ý/từ chối tập trung;",
                                     "Phê duyệt nội dung chiến dịch trước khi gửi;"]),
        ("Khối Ngân hàng số", ["Bảo đảm cơ chế opt-out một chạm trên ứng dụng;"]),
    ])
    s += dieu_kiemtra(9)
    s += dieu_hieuluc(10, "05 tháng 5 năm 2025")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối KHCN/KHDN", "Khối NHS", "Lưu: VT"])
    build_pdf("24_QD_476_2025_QD-DDB_tiep_thi_so.pdf", s)


# 25 — CV 88/2025/CV-DDB — Công văn giải đáp chia sẻ dữ liệu (diễn giải, không tạo quy định)
@register
def doc_cv88():
    s = []
    s += internal_header(
        "88/2025/CV-DDB", "CÔNG VĂN",
        "V/v giải đáp vướng mắc về chia sẻ dữ liệu khách hàng với đối tác phân phối bảo hiểm",
        "Hà Nội, ngày 12 tháng 6 năm 2025",
    )
    s += [
        B("Kính gửi: Giám đốc các Chi nhánh, Phòng giao dịch."),
        B("Khối Pháp chế và Tuân thủ nhận được đề nghị hướng dẫn của một số Chi nhánh về việc chuyển danh sách khách hàng cho đối tác phân phối bảo hiểm để giới thiệu sản phẩm liên kết. Sau khi rà soát, Khối Pháp chế và Tuân thủ có ý kiến như sau:"),
        K("1. Đối tác phân phối bảo hiểm là **bên xử lý dữ liệu** theo khoản 5 Điều 2 Nghị định số 88/2024/NĐ-CP. Việc chia sẻ dữ liệu chỉ được thực hiện khi: (i) đã ký **thỏa thuận xử lý dữ liệu (DPA)** quy định rõ mục đích, phạm vi, biện pháp bảo vệ và trách nhiệm hoàn trả/xóa dữ liệu; và (ii) khách hàng đã có **sự đồng ý cho mục đích giới thiệu sản phẩm của bên thứ ba** theo Quyết định số 455/2025/QĐ-DDB."),
        K("2. Sự đồng ý nhận tin tiếp thị của Ngân hàng **không tự động bao gồm** việc chia sẻ dữ liệu cho bên thứ ba; hai mục đích này phải được ghi nhận đồng ý riêng."),
        K("3. Chi nhánh không tự ký thỏa thuận chia sẻ dữ liệu; mọi hợp đồng với đối tác có yếu tố dữ liệu khách hàng phải qua thẩm định của Khối Pháp chế và Tuân thủ."),
        B("Công văn này **chỉ có giá trị giải thích, hướng dẫn áp dụng** các quy định hiện hành (Nghị định số 88/2024/NĐ-CP, Quyết định số 455/2025/QĐ-DDB, Quyết định số 476/2025/QĐ-DDB) và không tạo ra quy định mới. Trường hợp có mâu thuẫn, áp dụng theo văn bản quy định gốc."),
    ]
    s += ky_ptgd("Phạm Thị D", ["Các CN/PGD", "Khối KHCN", "Lưu: VT, PC"])
    build_pdf("25_CV_88_2025_CV-DDB_giai_dap_chia_se_du_lieu.pdf", s)


# 26 — QĐ 512/2025/QĐ-DDB — Chuyển DLCN ra nước ngoài
@register
def doc_qd512():
    s = []
    s += internal_header(
        "512/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định chuyển dữ liệu cá nhân của khách hàng ra nước ngoài",
        "Hà Nội, ngày 15 tháng 5 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Nghị định số 88/2024/NĐ-CP về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng;",
         "Căn cứ Quyết định số 455/2025/QĐ-DDB về bảo vệ dữ liệu cá nhân của khách hàng;"],
    )
    s += [
        D("Điều 2. Điều kiện chuyển dữ liệu ra nước ngoài"),
        K("1. Trước khi chuyển dữ liệu cá nhân ra nước ngoài, đơn vị đề xuất phải hoàn thành **Báo cáo đánh giá tác động chuyển dữ liệu** và được Tổng Giám đốc phê duyệt."),
        K("2. Chỉ chuyển dữ liệu tới quốc gia, vùng lãnh thổ có quy định bảo vệ dữ liệu cá nhân **tương đương hoặc cao hơn** pháp luật Việt Nam, hoặc khi bên nhận cam kết bằng hợp đồng áp dụng biện pháp bảo vệ tương đương."),
        K("3. Dữ liệu cá nhân nhạy cảm chuyển ra nước ngoài phải được **mã hóa trong toàn bộ quá trình truyền và lưu trữ**."),
        D("Điều 3. Hồ sơ và báo cáo"),
    ]
    s += bullets([
        "Lưu hồ sơ đánh giá tác động và hợp đồng tối thiểu 05 năm sau khi kết thúc việc chuyển;",
        "Báo cáo danh mục các luồng chuyển dữ liệu ra nước ngoài về Khối Pháp chế và Tuân thủ trước ngày 31/01 hằng năm;",
        "Thông báo ngay khi bên nhận dữ liệu xảy ra sự cố ảnh hưởng dữ liệu của khách hàng DDB.",
    ])
    s += [
        D("Điều 4. Chế tài"),
        B("Hành vi chuyển dữ liệu cá nhân ra nước ngoài không đúng quy định có thể bị xử phạt hành chính tới mức **200–300 triệu đồng** theo Điều 14 Nghị định số 88/2024/NĐ-CP, không loại trừ trách nhiệm kỷ luật nội bộ và bồi thường thiệt hại."),
    ]
    s += dieu_kiemtra(5)
    s += dieu_hieuluc(6, "20 tháng 5 năm 2025")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối PC&TT", "TT CNTT", "Lưu: VT, PC"])
    build_pdf("26_QD_512_2025_QD-DDB_chuyen_du_lieu_ra_nuoc_ngoai.pdf", s)


# =====================================================================
# NHÓM D — KYC & PCRT MỞ RỘNG
# =====================================================================

# 27 — QĐ 301/2023/QĐ-DDB — KYC v1 (BỊ 480/2025 THAY THẾ TOÀN BỘ — trap giá trị cũ)
@register
def doc_qd301():
    s = []
    s += internal_header(
        "301/2023/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định nhận biết khách hàng",
        "Hà Nội, ngày 10 tháng 4 năm 2023",
    )
    s += qd_opening(
        ["Căn cứ quy định pháp luật về phòng, chống rửa tiền hiện hành;"],
    )
    s += [
        D("Điều 2. Nhận biết khách hàng"),
        B("Đơn vị kinh doanh thu thập, xác minh thông tin nhận biết khách hàng trước khi thiết lập quan hệ; hồ sơ nhận biết gồm giấy tờ tùy thân, thông tin nghề nghiệp và mục đích sử dụng dịch vụ."),
    ]
    s += tbl_block("Điều 4. Ngưỡng giám sát giao dịch (áp dụng nội bộ)", [
        ["Loại giao dịch", "Ngưỡng giám sát", "Ghi chú"],
        ["Giao dịch tiền mặt trong ngày", "≥ 200.000.000 VND", "Lập cảnh báo trên hệ thống"],
        ["Chuyển tiền quốc tế", "≥ 2.000 USD", "Kiểm tra bổ sung nguồn tiền"],
    ], [5.5 * cm, 4.5 * cm, 6.5 * cm])
    s += [
        D("Điều 6. Cập nhật thông tin định kỳ"),
        B("Thông tin nhận biết khách hàng được rà soát, cập nhật **định kỳ 03 (ba) năm một lần**; khách hàng có rủi ro cao cập nhật khi phát sinh giao dịch bất thường."),
    ]
    s += chuong_tochuc(8, [
        ("Đơn vị kinh doanh", ["Thu thập, xác minh và cập nhật hồ sơ nhận biết;"]),
        ("Bộ phận AML", ["Giám sát cảnh báo, xử lý nghi vấn;"]),
    ])
    s += dieu_hieuluc(9, "15 tháng 4 năm 2023")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Bộ phận AML", "Các CN/PGD", "Lưu: VT"])
    build_pdf("27_QD_301_2023_QD-DDB_KYC_v1_HET_HIEU_LUC.pdf", s)


# 28 — QĐ 517/2025/QĐ-DDB — KYC khách hàng tổ chức (scope KHDN, bổ sung 480)
@register
def doc_qd517():
    s = []
    s += internal_header(
        "517/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định nhận biết khách hàng tổ chức và xác định chủ sở hữu hưởng lợi",
        "Hà Nội, ngày 20 tháng 5 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Thông tư số 20/2024/TT-NHNN hướng dẫn thực hiện phòng, chống rửa tiền trong hoạt động ngân hàng;",
         "Căn cứ Quy định nhận biết khách hàng và phòng, chống rửa tiền ban hành kèm theo Quyết định số 480/2025/QĐ-DDB;"],
    )
    s += [
        D("Điều 1. Phạm vi áp dụng"),
        B("Quy định này hướng dẫn **bổ sung** Quyết định số 480/2025/QĐ-DDB đối với khách hàng là tổ chức, doanh nghiệp; các nội dung không quy định tại đây thực hiện theo Quyết định số 480/2025/QĐ-DDB."),
        D("Điều 3. Xác định chủ sở hữu hưởng lợi"),
        K("1. Phải xác định và xác minh mọi cá nhân **sở hữu trực tiếp hoặc gián tiếp từ 25% vốn điều lệ trở lên** của khách hàng tổ chức."),
        K("2. Trường hợp không xác định được theo tỷ lệ sở hữu, xác định cá nhân có quyền chi phối hoạt động của tổ chức (qua điều lệ, thỏa thuận hoặc thực tế điều hành)."),
        K("3. Thông tin chủ sở hữu hưởng lợi được rà soát lại khi tổ chức thay đổi cơ cấu sở hữu và tối thiểu **01 năm/lần đối với khách hàng rủi ro cao**."),
    ]
    s += tbl_block("Điều 4. Hồ sơ pháp lý tối thiểu theo loại hình tổ chức", [
        ["Loại hình", "Hồ sơ tối thiểu"],
        ["Doanh nghiệp trong nước", "GCN đăng ký doanh nghiệp; điều lệ; danh sách cổ đông/thành viên ≥ 25%; giấy tờ người đại diện"],
        ["Tổ chức nước ngoài", "Giấy phép thành lập hợp pháp hóa lãnh sự; cấu trúc sở hữu tới cá nhân cuối cùng"],
        ["Hộ kinh doanh", "GCN đăng ký hộ kinh doanh; giấy tờ tùy thân chủ hộ"],
    ], [4.5 * cm, 12 * cm])
    s += [
        D("Điều 6. Từ chối thiết lập quan hệ"),
        B("Từ chối mở tài khoản khi không xác minh được chủ sở hữu hưởng lợi hoặc khách hàng cố tình che giấu cấu trúc sở hữu; trường hợp nghi ngờ rửa tiền, lập báo cáo giao dịch đáng ngờ theo quy định hiện hành."),
    ]
    s += dieu_kiemtra(7)
    s += dieu_hieuluc(8, "25 tháng 5 năm 2025")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối KHDN", "Bộ phận AML", "Lưu: VT, PC"])
    build_pdf("28_QD_517_2025_QD-DDB_KYC_khach_hang_to_chuc.pdf", s)


# 29 — HD 04/2024/HD-DDB — Hướng dẫn giao dịch đáng ngờ tại quầy (nhiễu BM25 với TT 20)
@register
def doc_hd04():
    s = []
    s += internal_header(
        "04/2024/HD-DDB", "HƯỚNG DẪN",
        "Nhận biết và xử lý giao dịch đáng ngờ tại quầy giao dịch",
        "Hà Nội, ngày 20 tháng 8 năm 2024",
    )
    s += [
        CC("Thực hiện Thông tư số 20/2024/TT-NHNN và quy định phòng, chống rửa tiền nội bộ;"),
        CC("Khối Pháp chế và Tuân thủ hướng dẫn giao dịch viên nhận biết tình huống đáng ngờ như sau:"),
        sp(),
        D("1. Dấu hiệu cần chú ý khi tiếp khách"),
    ]
    s += bullets([
        "Khách hàng chia một khoản tiền lớn thành nhiều giao dịch nhỏ trong ngày hoặc nhiều ngày liên tiếp nhằm tránh ngưỡng phải báo cáo;",
        "Giá trị giao dịch không phù hợp với nghề nghiệp, thu nhập đã khai;",
        "Khách hàng lúng túng, từ chối hoặc trì hoãn cung cấp thông tin nhận biết;",
        "Nhiều người cùng chuyển tiền vào một tài khoản rồi rút ngay trong thời gian ngắn;",
        "Khách yêu cầu thực hiện giao dịch cho bên thứ ba không rõ quan hệ.",
    ])
    s += [
        D("2. Tình huống ví dụ"),
        K("Tình huống A: Khách hàng nộp 180 triệu tiền mặt buổi sáng và 150 triệu buổi chiều cùng ngày, khai mục đích khác nhau. Tổng giao dịch tiền mặt trong ngày đã vượt ngưỡng giám sát nội bộ — giao dịch viên lập cảnh báo trên hệ thống và chuyển bộ phận AML, không từ chối giao dịch khi chưa có chỉ đạo."),
        K("Tình huống B: Khách hàng mới mở tài khoản một tuần nhận 12 khoản chuyển đến từ các tỉnh khác nhau và đề nghị rút toàn bộ. Giao dịch viên đề nghị bổ sung thông tin mục đích; nếu khách từ chối, lập báo cáo dấu hiệu đáng ngờ."),
        D("3. Nguyên tắc xử lý"),
    ]
    s += bullets([
        "Không thông báo cho khách hàng việc lập báo cáo đáng ngờ (nghiêm cấm tiết lộ);",
        "Ghi nhận đầy đủ diễn biến vào hệ thống trong ngày làm việc;",
        "Ngưỡng giám sát và thời hạn báo cáo thực hiện theo quy định KYC-PCRT hiện hành của Ngân hàng.",
    ])
    s += ky_ptgd("Phạm Thị D", ["Các CN/PGD", "Bộ phận AML", "Lưu: VT, PC"])
    build_pdf("29_HD_04_2024_HD-DDB_giao_dich_dang_ngo_tai_quay.pdf", s)


# =====================================================================
# NHÓM E — RỦI RO HOẠT ĐỘNG & THUÊ NGOÀI
# =====================================================================

# 30 — TT 41/2024/TT-NHNN — Rủi ro hoạt động & thuê ngoài (STATE)
@register
def doc_tt41():
    s = []
    s += state_header(
        "41/2024/TT-NHNN", "NGÂN HÀNG NHÀ NƯỚC\nVIỆT NAM", "THÔNG TƯ",
        "Quy định về quản lý rủi ro hoạt động và hoạt động thuê ngoài của tổ chức tín dụng",
        "Hà Nội, ngày 25 tháng 11 năm 2024",
    )
    s += [
        CC("Căn cứ Luật Ngân hàng Nhà nước Việt Nam ngày 16 tháng 6 năm 2010;"),
        CC("Căn cứ Luật Các tổ chức tín dụng ngày 18 tháng 01 năm 2024;"),
        CC("Theo đề nghị của Chánh Thanh tra, giám sát ngân hàng;"),
        B("Thống đốc Ngân hàng Nhà nước Việt Nam ban hành Thông tư quy định về quản lý rủi ro hoạt động và hoạt động thuê ngoài của tổ chức tín dụng."),
        sp(),
        D("Điều 3. Ba tuyến bảo vệ"),
        B("Tổ chức tín dụng tổ chức quản lý rủi ro hoạt động theo ba tuyến: đơn vị kinh doanh trực tiếp nhận diện và kiểm soát rủi ro; bộ phận quản lý rủi ro và tuân thủ giám sát độc lập; kiểm toán nội bộ đánh giá độc lập định kỳ."),
        D("Điều 7. Điều kiện đối với hoạt động thuê ngoài"),
        K("1. Trước khi ký hợp đồng thuê ngoài chức năng có ảnh hưởng trọng yếu, tổ chức tín dụng phải **đánh giá năng lực, an toàn thông tin và tính liên tục kinh doanh** của bên cung cấp dịch vụ."),
        K("2. Hợp đồng thuê ngoài phải bảo đảm **quyền kiểm tra, kiểm toán** của tổ chức tín dụng và của Ngân hàng Nhà nước đối với phạm vi dịch vụ thuê ngoài."),
        K("3. **Không được thuê ngoài toàn bộ chức năng quản lý rủi ro, tuân thủ hoặc kiểm toán nội bộ.**"),
        K("4. Tổ chức tín dụng chịu trách nhiệm cuối cùng trước khách hàng và cơ quan quản lý đối với dịch vụ thuê ngoài như đối với hoạt động tự thực hiện."),
        D("Điều 9. Báo cáo"),
        B("Tổ chức tín dụng báo cáo Ngân hàng Nhà nước danh mục hợp đồng thuê ngoài trọng yếu định kỳ hằng năm và báo cáo đột xuất khi xảy ra sự kiện rủi ro hoạt động gây gián đoạn dịch vụ trên 04 giờ hoặc thiệt hại ước tính trên 05 tỷ đồng."),
        D("Điều 12. Hiệu lực thi hành"),
        B("Thông tư này có hiệu lực thi hành kể từ ngày **10 tháng 12 năm 2024**."),
    ]
    s += sign_block("KT. THỐNG ĐỐC\nPHÓ THỐNG ĐỐC\n(mô phỏng)", "Trần Thị B",
                    extra_left=noinhan(["Các tổ chức tín dụng, chi nhánh NHNNg",
                                        "Cơ quan Thanh tra, giám sát ngân hàng", "Lưu: VT, TTGS"]))
    build_pdf("30_TT_41_2024_TT-NHNN_rui_ro_hoat_dong_thue_ngoai.pdf", s)


# 31 — QĐ 468/2025/QĐ-DDB — Thuê ngoài & bên thứ ba (DPA, đánh giá NCC)
@register
def doc_qd468():
    s = []
    s += internal_header(
        "468/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định quản lý hoạt động thuê ngoài và bên thứ ba",
        "Hà Nội, ngày 10 tháng 4 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Thông tư số 41/2024/TT-NHNN quy định về quản lý rủi ro hoạt động và hoạt động thuê ngoài của tổ chức tín dụng;",
         "Căn cứ Nghị định số 88/2024/NĐ-CP về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng;"],
        "Giám đốc Khối Quản trị rủi ro",
    )
    s += tbl_block("Điều 3. Phân loại nhà cung cấp", [
        ["Mức", "Tiêu chí", "Yêu cầu quản lý"],
        ["Mức 1 — Trọng yếu", "Tiếp cận hệ thống trọng yếu hoặc dữ liệu khách hàng quy mô lớn", "Đánh giá trước ký + đánh giá lại hằng năm; điều khoản kiểm toán; phương án thoát (exit plan)"],
        ["Mức 2 — Quan trọng", "Ảnh hưởng một mảng nghiệp vụ, dữ liệu hạn chế", "Đánh giá trước ký; đánh giá lại 02 năm/lần"],
        ["Mức 3 — Thông thường", "Không tiếp cận dữ liệu khách hàng", "Điều khoản bảo mật tiêu chuẩn"],
    ], [3.6 * cm, 6.2 * cm, 6.7 * cm])
    s += [
        D("Điều 4. Bảo vệ dữ liệu trong thuê ngoài"),
        K("1. Nhà cung cấp **có xử lý dữ liệu cá nhân của khách hàng** phải ký **thỏa thuận xử lý dữ liệu (DPA)** trước khi được cấp quyền truy cập, nêu rõ mục đích, phạm vi, thời hạn, biện pháp bảo vệ và nghĩa vụ xóa/hoàn trả dữ liệu khi kết thúc hợp đồng."),
        K("2. Việc nhà cung cấp chuyển dữ liệu ra nước ngoài phải tuân thủ Quy định chuyển dữ liệu cá nhân ra nước ngoài của Ngân hàng."),
        D("Điều 5. Sự cố tại nhà cung cấp"),
        B("Sự cố an toàn thông tin phát sinh tại nhà cung cấp ảnh hưởng đến dịch vụ hoặc dữ liệu của Ngân hàng được tiếp nhận, phân loại và báo cáo **như sự cố nội bộ** theo Quyết định số 428/2025/QĐ-DDB và Quyết định số 445/2025/QĐ-DDB; hợp đồng phải quy định nghĩa vụ thông báo của nhà cung cấp trong vòng 04 giờ."),
        D("Điều 6. Giới hạn thuê ngoài"),
        B("Không thuê ngoài toàn bộ chức năng quản lý rủi ro, tuân thủ, kiểm toán nội bộ theo khoản 3 Điều 7 Thông tư số 41/2024/TT-NHNN."),
    ]
    s += chuong_tochuc(8, [
        ("Khối Quản trị rủi ro", ["Thẩm định, phân loại nhà cung cấp; theo dõi đánh giá định kỳ;"]),
        ("Khối Pháp chế và Tuân thủ", ["Thẩm định DPA và điều khoản kiểm toán;"]),
        ("Đơn vị sử dụng dịch vụ", ["Giám sát chất lượng, báo cáo sự cố của nhà cung cấp;"]),
    ])
    s += dieu_kiemtra(9)
    s += dieu_hieuluc(10, "15 tháng 4 năm 2025")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối QTRR", "Khối PC&TT", "Lưu: VT, QTRR"])
    build_pdf("31_QD_468_2025_QD-DDB_thue_ngoai_ben_thu_ba.pdf", s)


# 32 — NQ 09/2025/NQ-HĐQT-DDB — Nghị quyết HĐQT khung quản trị ATTT & dữ liệu
@register
def doc_nq09():
    s = []
    s += internal_header(
        "09/2025/NQ-HĐQT-DDB", "NGHỊ QUYẾT",
        "Của Hội đồng Quản trị về Khung quản trị an toàn thông tin và dữ liệu",
        "Hà Nội, ngày 02 tháng 01 năm 2025",
    )
    s += [
        P("HỘI ĐỒNG QUẢN TRỊ NGÂN HÀNG TMCP ĐÔNG ĐÔ", "trichyeu"),
        CC("Căn cứ Điều lệ tổ chức và hoạt động của Ngân hàng TMCP Đông Đô;"),
        CC("Căn cứ kết quả họp Hội đồng Quản trị ngày 28 tháng 12 năm 2024;"),
        sp(),
        H("QUYẾT NGHỊ:"),
        D("Điều 1. Khẩu vị rủi ro an toàn thông tin và dữ liệu"),
        K("1. Ngân hàng không chấp nhận rủi ro dẫn đến lộ, mất dữ liệu khách hàng quy mô lớn hoặc gián đoạn hệ thống trọng yếu vượt mục tiêu khôi phục đã phê duyệt."),
        K("2. Mọi sáng kiến kinh doanh sử dụng dữ liệu khách hàng phải được đánh giá tác động bảo vệ dữ liệu trước khi triển khai."),
        D("Điều 2. Phân cấp phê duyệt"),
        K("1. Hội đồng Quản trị phê duyệt: khung quản trị, khẩu vị rủi ro, và **việc triển khai các mô hình trí tuệ nhân tạo được phân loại rủi ro cao** theo quy định quản lý rủi ro AI hiện hành."),
        K("2. Tổng Giám đốc ban hành các quy định, quy trình chi tiết về an toàn thông tin, bảo vệ dữ liệu, quản lý sự cố và các lĩnh vực liên quan trong phạm vi Khung này."),
        D("Điều 3. Báo cáo"),
        B("Tổng Giám đốc báo cáo Hội đồng Quản trị **định kỳ hằng quý** về tình hình an toàn thông tin, sự cố trọng yếu và tiến độ khắc phục khuyến nghị kiểm toán."),
        D("Điều 4. Hiệu lực"),
        B("Nghị quyết có hiệu lực kể từ ngày **05 tháng 01 năm 2025**. Tổng Giám đốc, các Khối, đơn vị liên quan chịu trách nhiệm thi hành."),
    ]
    s += sign_block("TM. HỘI ĐỒNG QUẢN TRỊ\nCHỦ TỊCH\n(mô phỏng)", "Đỗ Văn E",
                    extra_left=noinhan(["Thành viên HĐQT", "Ban Kiểm soát", "Tổng Giám đốc", "Lưu: VP HĐQT"]))
    build_pdf("32_NQ_09_2025_NQ-HDQT-DDB_khung_quan_tri_ATTT_du_lieu.pdf", s)


# =====================================================================
# NHÓM F — TRUY CẬP & THIẾT BỊ
# =====================================================================

# 33 — QĐ 361/2024/QĐ-DDB — Truy cập đặc quyền (mật khẩu 16 ký tự / 90 ngày)
@register
def doc_qd361():
    s = []
    s += internal_header(
        "361/2024/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định quản lý truy cập đặc quyền",
        "Hà Nội, ngày 18 tháng 10 năm 2024",
    )
    s += qd_opening(
        ["Căn cứ Quy chế An toàn thông tin hiện hành của Ngân hàng;"],
        "Giám đốc Trung tâm Công nghệ thông tin",
    )
    s += dieu_giaithich(2, [
        ("Tài khoản đặc quyền", "tài khoản có quyền quản trị hệ thống, cơ sở dữ liệu, thiết bị mạng hoặc quyền can thiệp dữ liệu vượt phạm vi người dùng nghiệp vụ thông thường."),
        ("Truy cập tức thời (JIT)", "cơ chế cấp quyền đặc quyền có thời hạn theo từng phiên làm việc, tự động thu hồi khi hết thời hạn."),
    ])
    s += [
        D("Điều 3. Yêu cầu đối với tài khoản đặc quyền"),
        K("1. **Mật khẩu tài khoản đặc quyền có độ dài tối thiểu 16 (mười sáu) ký tự**, gồm đủ bốn nhóm ký tự, và **được thay đổi tối thiểu 90 (chín mươi) ngày một lần**. Yêu cầu này áp dụng riêng cho tài khoản đặc quyền, **chặt hơn quy định chung đối với người dùng thông thường tại Quy chế An toàn thông tin**."),
        K("2. Tài khoản đặc quyền bắt buộc xác thực đa yếu tố khi đăng nhập và chỉ được sử dụng qua hệ thống quản lý truy cập đặc quyền (PAM) tập trung."),
        K("3. Nghiêm cấm dùng chung tài khoản đặc quyền; mỗi phiên phải gắn với một cá nhân được phê duyệt."),
        D("Điều 4. Phiên làm việc đặc quyền"),
        K("1. Toàn bộ phiên đặc quyền được **ghi hình thao tác** và lưu tối thiểu 12 tháng phục vụ điều tra, kiểm toán."),
        K("2. Quyền đặc quyền được cấp theo cơ chế **truy cập tức thời (JIT)** với thời hạn tối đa 08 giờ/phiên; gia hạn phải phê duyệt lại."),
        D("Điều 6. Rà soát"),
        B("Danh sách tài khoản đặc quyền được rà soát hằng quý; tài khoản không phát sinh phiên trong 90 ngày bị thu hồi tự động."),
    ]
    s += chuong_tochuc(8, [
        ("Trung tâm Công nghệ thông tin", ["Vận hành hệ thống PAM, lưu trữ ghi hình phiên;"]),
        ("Khối Kiểm toán nội bộ", ["Kiểm tra mẫu phiên đặc quyền định kỳ;"]),
    ])
    s += dieu_kiemtra(9)
    s += dieu_hieuluc(10, "25 tháng 10 năm 2024")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "TT CNTT", "Khối KTNB", "Lưu: VT, CNTT"])
    build_pdf("33_QD_361_2024_QD-DDB_truy_cap_dac_quyen.pdf", s)


# 34 — QĐ 412/2025/QĐ-DDB — Thiết bị cá nhân BYOD (khóa màn hình 5 phút)
@register
def doc_qd412():
    s = []
    s += internal_header(
        "412/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định sử dụng thiết bị cá nhân trong công việc (BYOD)",
        "Hà Nội, ngày 22 tháng 01 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Quy chế An toàn thông tin ban hành kèm theo Quyết định số 342/2024/QĐ-DDB;",
         "Căn cứ Quy định làm việc từ xa ban hành kèm theo Quyết định số 401/2024/QĐ-DDB;"],
        "Giám đốc Trung tâm Công nghệ thông tin",
    )
    s += dieu_phamvi(1, "cán bộ nhân viên được phê duyệt sử dụng thiết bị cá nhân truy cập tài nguyên công việc",
                     "điều kiện an toàn khi sử dụng thiết bị di động, máy tính cá nhân cho công việc")
    s += [
        D("Điều 3. Điều kiện đăng ký thiết bị"),
        K("1. Thiết bị cá nhân phải cài đặt phần mềm quản lý thiết bị di động (MDM) của Ngân hàng và tách vùng dữ liệu công việc trước khi được cấp quyền truy cập."),
        K("2. **Màn hình thiết bị di động phải tự động khóa sau tối đa 05 (năm) phút không thao tác** và mở khóa bằng sinh trắc học hoặc mã PIN tối thiểu 6 số. Quy định này áp dụng cho **màn hình thiết bị di động cá nhân**, độc lập với thời gian tự khóa phiên ứng dụng nội bộ và phiên làm việc từ xa theo các quy định tương ứng."),
        D("Điều 4. Hành vi bị cấm"),
    ]
    s += bullets([
        "Lưu trữ dữ liệu khách hàng xuống bộ nhớ cá nhân của thiết bị dưới mọi hình thức;",
        "Chụp màn hình, sao chép nội dung từ vùng dữ liệu công việc sang ứng dụng cá nhân;",
        "Sử dụng thiết bị đã can thiệp hệ điều hành (root/jailbreak);",
        "Cho người khác sử dụng thiết bị khi đang đăng nhập vùng công việc.",
    ])
    s += [
        D("Điều 5. Xử lý khi mất thiết bị"),
        B("Cán bộ báo Trung tâm Công nghệ thông tin **trong vòng 01 giờ** kể từ khi phát hiện mất thiết bị; Trung tâm thực hiện xóa từ xa (remote wipe) vùng dữ liệu công việc và thu hồi phiên truy cập."),
    ]
    s += dieu_kiemtra(6)
    s += dieu_hieuluc(7, "30 tháng 01 năm 2025")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "TT CNTT", "Các đơn vị", "Lưu: VT, CNTT"])
    build_pdf("34_QD_412_2025_QD-DDB_thiet_bi_ca_nhan_BYOD.pdf", s)


# 35 — HD 03/2025/HD-DDB — Phân quyền core banking (nhiễu thuật ngữ với 361)
@register
def doc_hd03():
    s = []
    s += internal_header(
        "03/2025/HD-DDB", "HƯỚNG DẪN",
        "Phân quyền người dùng trên hệ thống ngân hàng lõi (core banking)",
        "Hà Nội, ngày 05 tháng 02 năm 2025",
    )
    s += [
        CC("Thực hiện Quy chế An toàn thông tin và Quy định quản lý truy cập đặc quyền hiện hành;"),
        CC("Trung tâm Công nghệ thông tin hướng dẫn phân quyền trên hệ thống ngân hàng lõi như sau:"),
        sp(),
        D("1. Nguyên tắc phân quyền"),
    ]
    s += bullets([
        "Quyền tối thiểu: người dùng chỉ được cấp đúng chức năng cần cho vị trí công việc;",
        "Nguyên tắc bốn mắt: giao dịch vượt hạn mức của giao dịch viên phải được kiểm soát viên phê duyệt trên hệ thống;",
        "Tách bạch nhiệm vụ: người khởi tạo không đồng thời là người phê duyệt cùng một giao dịch;",
        "Quyền quản trị hệ thống core banking là quyền đặc quyền, quản lý theo Quy định quản lý truy cập đặc quyền (Quyết định số 361/2024/QĐ-DDB).",
    ])
    s += tbl_block("2. Ma trận vai trò tiêu chuẩn", [
        ["Vai trò", "Chức năng chính", "Giới hạn"],
        ["Giao dịch viên", "Khởi tạo giao dịch tiền gửi, thanh toán", "Trong hạn mức giao dịch viên"],
        ["Kiểm soát viên", "Phê duyệt giao dịch vượt hạn mức GDV", "Không tự khởi tạo và tự duyệt"],
        ["Cán bộ tín dụng", "Khởi tạo hồ sơ vay, giải ngân theo phê duyệt", "Không truy cập nghiệp vụ tiền gửi"],
        ["Quản trị ứng dụng", "Tham số hóa sản phẩm, quản lý người dùng", "Không thực hiện giao dịch tài chính"],
    ], [3.6 * cm, 7.2 * cm, 5.7 * cm])
    s += [
        D("3. Rà soát định kỳ"),
        K("Trưởng đơn vị xác nhận lại (recertify) danh sách người dùng và vai trò **06 tháng một lần** theo Quy định quản lý vòng đời tài khoản người dùng; kết quả gửi Trung tâm Công nghệ thông tin trước ngày 15 của tháng kế tiếp kỳ rà soát."),
    ]
    s += ky_ptgd("Phạm Thị D", ["Các CN/PGD", "TT CNTT", "Lưu: VT, CNTT"])
    build_pdf("35_HD_03_2025_HD-DDB_phan_quyen_core_banking.pdf", s)


# 36 — QĐ 296/2024/QĐ-DDB — Vòng đời tài khoản người dùng (hop "Quy chế ATTT hiện hành")
@register
def doc_qd296():
    s = []
    s += internal_header(
        "296/2024/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định quản lý vòng đời tài khoản người dùng nội bộ",
        "Hà Nội, ngày 08 tháng 8 năm 2024",
    )
    s += qd_opening(
        ["Căn cứ Quy chế An toàn thông tin hiện hành của Ngân hàng;"],
        "Giám đốc Trung tâm Công nghệ thông tin",
    )
    s += [
        D("Điều 2. Cấp mới tài khoản"),
        B("Tài khoản người dùng được cấp theo đề nghị của trưởng đơn vị và phê duyệt của Trung tâm Công nghệ thông tin; quyền truy cập gắn với vị trí công việc theo ma trận vai trò của từng hệ thống."),
        D("Điều 3. Yêu cầu mật khẩu"),
        B("Độ dài, độ phức tạp và chu kỳ thay đổi mật khẩu của tài khoản người dùng **thực hiện theo Quy chế An toàn thông tin hiện hành của Ngân hàng**; hệ thống từ chối mật khẩu không đạt chuẩn ngay khi thiết lập."),
        D("Điều 4. Thu hồi và tạm khóa"),
        K("1. Khi cán bộ nghỉ việc hoặc chuyển công tác, toàn bộ tài khoản và quyền truy cập phải được **thu hồi trong vòng 24 (hai mươi bốn) giờ** kể từ thời điểm quyết định nhân sự có hiệu lực."),
        K("2. Tài khoản **không đăng nhập trong 90 ngày liên tục** bị tạm khóa tự động; mở lại theo quy trình cấp mới rút gọn."),
        D("Điều 5. Rà soát quyền định kỳ"),
        B("Trưởng đơn vị phối hợp Trung tâm Công nghệ thông tin rà soát danh sách tài khoản và quyền truy cập **định kỳ 06 (sáu) tháng một lần**; kết quả rà soát lưu hồ sơ phục vụ kiểm toán."),
    ]
    s += chuong_tochuc(7, [
        ("Trung tâm Công nghệ thông tin", ["Thực hiện cấp, thu hồi, tạm khóa tài khoản đúng thời hạn;"]),
        ("Khối Nhân sự", ["Thông báo quyết định nhân sự cho TT CNTT ngay trong ngày hiệu lực;"]),
        ("Trưởng đơn vị", ["Đề nghị quyền đúng vị trí; xác nhận kết quả rà soát định kỳ;"]),
    ])
    s += dieu_kiemtra(8)
    s += dieu_hieuluc(9, "15 tháng 8 năm 2024")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "TT CNTT", "Khối Nhân sự", "Lưu: VT, CNTT"])
    build_pdf("36_QD_296_2024_QD-DDB_vong_doi_tai_khoan_nguoi_dung.pdf", s)


# =====================================================================
# NHÓM G — NHIỄU CÓ CHỦ ĐÍCH
# =====================================================================

# 37 — QT 07/2024/QT-CN-HT — Quy trình sự cố CN Hà Thành (scope trap: chỉ 1 chi nhánh)
@register
def doc_qt07():
    s = []
    s += internal_header(
        "07/2024/QT-CN-HT", "QUY TRÌNH",
        "Xử lý sự cố công nghệ thông tin tại Chi nhánh Hà Thành",
        "Hà Nội, ngày 01 tháng 7 năm 2024",
    )
    s += [
        CC("Căn cứ quy định quản lý sự cố công nghệ thông tin của Hội sở;"),
        CC("Giám đốc Chi nhánh Hà Thành ban hành quy trình nội bộ chi nhánh như sau:"),
        sp(),
        D("1. Phạm vi áp dụng"),
        B("Quy trình này **chỉ áp dụng tại Chi nhánh Hà Thành và các Phòng giao dịch trực thuộc**; quy định bước phối hợp nội bộ chi nhánh khi phát sinh sự cố công nghệ thông tin, **không thay thế** nghĩa vụ báo cáo về Hội sở theo quy định toàn hàng."),
        D("2. Các bước xử lý"),
        K("Bước 1 — Ghi nhận: cán bộ phát hiện sự cố báo ngay cán bộ đầu mối CNTT chi nhánh và ghi nhận vào sổ theo dõi."),
        K("Bước 2 — Báo cáo Hội sở: cán bộ đầu mối thực hiện báo cáo Trung tâm Công nghệ thông tin **theo thời hạn quy định toàn hàng** (quy định quản lý sự cố hiện hành của Hội sở)."),
        K("Bước 3 — Báo cáo nội bộ chi nhánh: đồng thời, cán bộ đầu mối tổng hợp báo cáo **Giám đốc Chi nhánh trong vòng 04 (bốn) giờ** kể từ khi phát hiện sự cố, kèm đánh giá ảnh hưởng tới khách hàng tại quầy."),
        K("Bước 4 — Khắc phục tại chỗ: chỉ thao tác trong phạm vi được Trung tâm Công nghệ thông tin hướng dẫn; nghiêm cấm tự can thiệp máy chủ, thiết bị mạng."),
        K("Bước 5 — Đóng sự cố: cập nhật kết quả vào sổ theo dõi và hồ sơ báo cáo tháng của chi nhánh."),
        D("3. Lưu ý"),
        B("Thời hạn 04 giờ tại Bước 3 là yêu cầu **quản trị nội bộ chi nhánh**, không thay thế và không nới lỏng thời hạn báo cáo Trung tâm Công nghệ thông tin theo quy định của Hội sở."),
    ]
    s += sign_block("GIÁM ĐỐC CHI NHÁNH\n(mô phỏng)", "Vũ Thị F",
                    extra_left=noinhan(["Các phòng thuộc CN Hà Thành", "Lưu: VT CN"]))
    build_pdf("37_QT_07_2024_QT-CN-HT_su_co_chi_nhanh_Ha_Thanh.pdf", s)


# 38 — BB 15/2025 — Biên bản họp UB ATTT (đề xuất 20 phút — CHƯA phê duyệt)
@register
def doc_bb15():
    s = []
    s += internal_header(
        "15/2025/BB-UBATTT", "BIÊN BẢN HỌP",
        "Ủy ban An toàn thông tin — Phiên họp thường kỳ quý II năm 2025",
        "Hà Nội, ngày 15 tháng 5 năm 2025",
    )
    s += [
        B("Thời gian: 14h00 ngày 15/5/2025. Địa điểm: Phòng họp A3, Hội sở chính."),
        B("Thành phần: Chủ tịch Ủy ban (Phó Tổng Giám đốc phụ trách CNTT), Giám đốc TT CNTT, Giám đốc Khối QTRR, Giám đốc Khối PC&TT, đại diện Khối NHS."),
        D("I. Nội dung thảo luận"),
        K("1. TT CNTT báo cáo tình hình sự cố quý II: 03 sự cố mức 2, không có sự cố mức 3; các chỉ tiêu khôi phục trong ngưỡng phê duyệt."),
        K("2. Khối NHS phản ánh ý kiến người dùng về thời gian tự khóa phiên nội bộ 15 phút gây gián đoạn khi xử lý hồ sơ dài; đề nghị xem xét nới lên 20 phút."),
        K("3. Khối PC&TT lưu ý mọi thay đổi giá trị trong Quy chế An toàn thông tin phải sửa đổi Quyết định số 342/2024/QĐ-DDB, không áp dụng bằng biên bản họp."),
        D("II. Kết luận của Chủ tịch Ủy ban"),
        K("1. **Thống nhất ĐỀ XUẤT trình Tổng Giám đốc xem xét việc nâng thời gian tự khóa phiên nội bộ từ 15 phút lên 20 phút**; giao TT CNTT đánh giá tác động an toàn, hoàn thành trong quý III/2025."),
        K("2. **Trong thời gian chưa có quyết định sửa đổi, giá trị 15 phút tại Quyết định số 342/2024/QĐ-DDB tiếp tục áp dụng nguyên trạng.**"),
        K("3. Các đơn vị tiếp tục rà soát tài khoản đặc quyền theo Quyết định số 361/2024/QĐ-DDB."),
        B("Biên bản này ghi nhận nội dung phiên họp, **không phải văn bản quy định nội bộ** và không làm thay đổi hiệu lực của bất kỳ quy định nào."),
    ]
    s += sign_block("TM. ỦY BAN AN TOÀN THÔNG TIN\nCHỦ TỊCH ỦY BAN\n(mô phỏng)", "Phạm Thị D",
                    extra_left=noinhan(["Thành viên Ủy ban", "Lưu: Thư ký UB"]))
    build_pdf("38_BB_15_2025_BB-UBATTT_bien_ban_hop_quy_II.pdf", s)


# 39 — DỰ THẢO QĐ ATTT v3 (CHƯA HIỆU LỰC — version trap mạnh nhất)
@register
def doc_dtv3():
    s = []
    s += internal_header(
        "…/2025/QĐ-DDB (DỰ THẢO)", "DỰ THẢO QUYẾT ĐỊNH",
        "Về việc ban hành Quy chế An toàn thông tin (phiên bản 3.0) — BẢN LẤY Ý KIẾN, CHƯA CÓ HIỆU LỰC",
        "Hà Nội, tháng 6 năm 2025",
    )
    s += [
        P("BẢN DỰ THẢO LẤY Ý KIẾN LẦN 1 — KHÔNG SỬ DỤNG LÀM CĂN CỨ ÁP DỤNG", "trichyeu"),
        CC("Thời hạn góp ý: trước ngày 30/6/2025, gửi về Khối Pháp chế và Tuân thủ;"),
        CC("Văn bản hiện hành trong thời gian lấy ý kiến: Quy chế An toàn thông tin ban hành kèm theo Quyết định số 342/2024/QĐ-DDB;"),
        sp(),
        D("Điều 2 (dự thảo). Quản lý mật khẩu"),
        K("1. Mật khẩu người dùng có độ dài tối thiểu **14 (mười bốn) ký tự** [dự kiến nâng từ 12 ký tự], gồm đủ bốn nhóm ký tự, thay đổi tối thiểu 180 ngày một lần."),
        K("2. Khuyến khích chuyển sang xác thực không mật khẩu (passkey) cho ứng dụng nội bộ trong lộ trình 2026."),
        D("Điều 5 (dự thảo). Quản lý phiên làm việc"),
        K("1. Phiên làm việc trên hệ thống nội bộ tự động khóa sau **10 (mười) phút** không có thao tác [dự kiến siết từ 15 phút]."),
        K("2. Phương án thay thế đang cân nhắc: giữ 15 phút và bổ sung khóa thông minh theo ngữ cảnh rủi ro."),
        D("Điều 9 (dự thảo). Điều khoản chuyển tiếp"),
        B("Dự kiến Quy chế v3.0 khi ban hành sẽ thay thế Quyết định số 342/2024/QĐ-DDB; nội dung chuyển tiếp cụ thể sẽ được xác định tại quyết định ban hành chính thức."),
        sp(),
        P("Lưu ý quan trọng: Đây là tài liệu DỰ THẢO đang lấy ý kiến. Mọi giá trị nêu trong tài liệu (14 ký tự, 10 phút, ...) CHƯA có hiệu lực áp dụng. Quy định hiện hành vẫn là Quyết định số 342/2024/QĐ-DDB.", "cancu"),
    ]
    s += ky_ptgd("Phạm Thị D", ["Các đơn vị (để góp ý)", "Lưu: VT, PC"])
    build_pdf("39_DT_QD_ATTT_v3_2025_DU_THAO_chua_hieu_luc.pdf", s)


# 40 — FAQ 02/2025 — Hỏi đáp ATTT (câu trả lời khóa phiên THIẾU ngoại lệ)
@register
def doc_faq02():
    s = []
    s += internal_header(
        "02/2025/PC-DDB", "TÀI LIỆU HỎI ĐÁP NỘI BỘ",
        "Hỏi đáp thường gặp về an toàn thông tin và bảo mật dành cho cán bộ nhân viên",
        "Hà Nội, ngày 10 tháng 3 năm 2025",
    )
    s += [
        CC("Tài liệu phổ biến kiến thức do Khối Pháp chế và Tuân thủ biên soạn; khi có khác biệt, áp dụng theo văn bản quy định gốc."),
        sp(),
        D("Câu 1. Mật khẩu đăng nhập hệ thống nội bộ phải đặt thế nào?"),
        B("Tối thiểu 12 ký tự, đủ bốn nhóm ký tự và đổi mỗi 180 ngày theo Quy chế An toàn thông tin (QĐ 342/2024). Không dùng lại 5 mật khẩu gần nhất."),
        D("Câu 2. Máy tính của tôi tự khóa màn hình sau bao lâu?"),
        B("Phiên làm việc tự động khóa sau **15 phút** không thao tác — quy định này áp dụng cho **mọi trường hợp**; bạn cũng nên chủ động khóa máy (Win+L) khi rời chỗ ngồi."),
        D("Câu 3. Tôi phát hiện email đáng ngờ thì làm gì?"),
        B("Không bấm liên kết, không mở tệp đính kèm; dùng nút Báo cáo phishing trên trình thư hoặc chuyển tiếp tới hộp thư an ninh thông tin; sự cố nghi ngờ đã bấm phải báo TT CNTT trong 2 giờ."),
        D("Câu 4. Được dùng USB cá nhân sao chép tài liệu không?"),
        B("Không. Cổng USB lưu trữ bị chặn mặc định; nhu cầu trao đổi dữ liệu dùng thư mục chia sẻ được cấp quyền hoặc đề nghị mở tạm thời có phê duyệt."),
        D("Câu 5. Làm việc từ xa cần lưu ý gì?"),
        B("Kết nối VPN, dùng thiết bị được phê duyệt và tuân thủ Quy định làm việc từ xa (QĐ 401/2024); không làm việc qua Wi-Fi công cộng không mã hóa."),
        D("Câu 6. Mất điện thoại cài Soft OTP/ứng dụng nội bộ thì sao?"),
        B("Báo ngay TT CNTT trong vòng 1 giờ để khóa vùng dữ liệu công việc và thu hồi phiên; đổi mật khẩu các tài khoản liên quan."),
        D("Câu 7. Ai được cấp tài khoản quản trị hệ thống?"),
        B("Chỉ cán bộ được phê duyệt theo Quy định quản lý truy cập đặc quyền (QĐ 361/2024); tài khoản quản trị có yêu cầu mật khẩu và giám sát riêng, chặt hơn tài khoản thường."),
        D("Câu 8. Tôi có được cài phần mềm ngoài danh mục lên máy công ty?"),
        B("Không; phần mềm ngoài danh mục chuẩn phải được TT CNTT thẩm định và phê duyệt trước khi cài đặt."),
        sp(),
        P("Tài liệu mang tính phổ biến, tóm lược. Nội dung chi tiết và ngoại lệ (nếu có) thực hiện theo văn bản quy định hiện hành của Ngân hàng.", "cancu"),
    ]
    s += ky_ptgd("Phạm Thị D", ["Toàn thể CBNV", "Lưu: VT, PC"])
    build_pdf("40_FAQ_02_2025_PC-DDB_hoi_dap_ATTT.pdf", s)


# 41 — TB 44/2025 — Thông báo tăng cường tạm thời 30 ngày (ĐÃ HẾT HIỆU LỰC)
@register
def doc_tb44():
    s = []
    s += internal_header(
        "44/2025/TB-DDB", "THÔNG BÁO",
        "Về việc áp dụng biện pháp tăng cường tạm thời ứng phó chiến dịch lừa đảo trực tuyến",
        "Hà Nội, ngày 22 tháng 4 năm 2025",
    )
    s += [
        B("Trước diễn biến chiến dịch lừa đảo mạo danh ngân hàng quy mô lớn, căn cứ Điều 9 Quy định kênh số hiện hành, Ngân hàng áp dụng biện pháp tăng cường **tạm thời trong 30 ngày, từ ngày 22/4/2025 đến hết ngày 22/5/2025** như sau:"),
        K("1. **Giảm hạn mức giao dịch xác thực bằng Soft OTP xuống tối đa 10.000.000 (mười triệu) đồng/giao dịch**; giao dịch vượt mức xác thực bằng sinh trắc học hoặc thực hiện tại quầy."),
        K("2. Tăng tần suất cảnh báo trong ứng dụng về thủ đoạn giả mạo tin nhắn thương hiệu."),
        K("3. Tạm dừng tính năng thay đổi thiết bị nhận Soft OTP qua kênh trực tuyến; khách hàng đổi thiết bị thực hiện tại quầy."),
        B("Các biện pháp trên **tự động hết hiệu lực sau ngày 22/5/2025** trừ khi có thông báo gia hạn; sau thời điểm này, hạn mức và phương thức xác thực trở lại theo quy định kênh số hiện hành."),
        B("Đơn vị kinh doanh chủ động giải thích cho khách hàng; Khối Ngân hàng số theo dõi và báo cáo hằng ngày về Ban Tổng Giám đốc trong thời gian áp dụng."),
    ]
    s += ky_ptgd("Phạm Thị D", ["Các đơn vị kinh doanh", "Khối NHS", "TT CNTT", "Lưu: VT"])
    build_pdf("41_TB_44_2025_TB-DDB_tang_cuong_chong_phishing_TAM_THOI.pdf", s)


# =====================================================================
# NHÓM H — THẺ & THANH TOÁN
# =====================================================================

# 42 — TT 18/2024/TT-NHNN — Hoạt động thẻ (STATE)
@register
def doc_tt18():
    s = []
    s += state_header(
        "18/2024/TT-NHNN", "NGÂN HÀNG NHÀ NƯỚC\nVIỆT NAM", "THÔNG TƯ",
        "Quy định về hoạt động thẻ ngân hàng",
        "Hà Nội, ngày 20 tháng 8 năm 2024",
    )
    s += [
        CC("Căn cứ Luật Ngân hàng Nhà nước Việt Nam ngày 16 tháng 6 năm 2010;"),
        CC("Căn cứ Luật Các tổ chức tín dụng ngày 18 tháng 01 năm 2024;"),
        CC("Theo đề nghị của Vụ trưởng Vụ Thanh toán;"),
        B("Thống đốc Ngân hàng Nhà nước Việt Nam ban hành Thông tư quy định về hoạt động thẻ ngân hàng."),
        sp(),
        D("Điều 3. Phát hành thẻ"),
        B("Tổ chức phát hành thẻ thực hiện nhận biết khách hàng theo pháp luật phòng, chống rửa tiền trước khi phát hành; thẻ ghi nợ chỉ phát hành cho chủ tài khoản thanh toán mở tại chính tổ chức phát hành."),
        D("Điều 8. Hạn mức giao dịch thẻ"),
        K("1. Tổ chức phát hành thẻ quy định hạn mức giao dịch phù hợp với loại thẻ, hạng khách hàng và mức độ rủi ro, bảo đảm cân đối giữa trải nghiệm và an toàn."),
        K("2. Giao dịch rút tiền mặt bằng thẻ tại nước ngoài không vượt quá 30.000.000 đồng/ngày đối với một thẻ."),
        D("Điều 11. Tra soát, khiếu nại"),
        K("1. Tổ chức phát hành thẻ tiếp nhận đề nghị tra soát của chủ thẻ và xử lý **trong thời hạn tối đa 45 (bốn mươi lăm) ngày** kể từ ngày tiếp nhận đối với giao dịch trong nước."),
        K("2. Đối với giao dịch có yếu tố nước ngoài, thời hạn xử lý theo quy định của tổ chức thẻ quốc tế nhưng tổ chức phát hành phải thông báo tiến độ cho chủ thẻ tối thiểu 15 ngày một lần."),
        D("Điều 14. An toàn, bảo mật thẻ"),
        B("Tổ chức phát hành áp dụng xác thực giao dịch thẻ trực tuyến theo quy định về an toàn giao dịch trên môi trường trực tuyến; cung cấp công cụ khóa thẻ khẩn cấp cho chủ thẻ trên kênh số hoạt động 24/7."),
        D("Điều 18. Hiệu lực thi hành"),
        B("Thông tư này có hiệu lực thi hành kể từ ngày **05 tháng 9 năm 2024**."),
    ]
    s += sign_block("KT. THỐNG ĐỐC\nPHÓ THỐNG ĐỐC\n(mô phỏng)", "Trần Thị B",
                    extra_left=noinhan(["Các tổ chức tín dụng, chi nhánh NHNNg", "Vụ Thanh toán", "Lưu: VT, TT"]))
    build_pdf("42_TT_18_2024_TT-NHNN_hoat_dong_the.pdf", s)


# 43 — QĐ 205/2022/QĐ-DDB — Thẻ v1 (BỊ 490/2025 THAY THẾ TOÀN BỘ — trap 50tr)
@register
def doc_qd205():
    s = []
    s += internal_header(
        "205/2022/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định phát hành và sử dụng thẻ",
        "Hà Nội, ngày 15 tháng 02 năm 2022",
    )
    s += qd_opening(
        ["Căn cứ quy định của Ngân hàng Nhà nước về hoạt động thẻ ngân hàng;"],
        "Giám đốc Khối Khách hàng cá nhân",
    )
    s += [
        D("Điều 3. Phát hành thẻ"),
        B("Thẻ ghi nợ phát hành cho khách hàng có tài khoản thanh toán tại DDB sau khi hoàn thành nhận biết khách hàng; thẻ tín dụng phát hành theo kết quả thẩm định hạn mức."),
    ]
    s += tbl_block("Điều 5. Hạn mức giao dịch thẻ ghi nợ", [
        ["Loại giao dịch", "Hạng chuẩn", "Hạng vàng"],
        ["Rút tiền mặt ATM", "**50.000.000 VND/ngày**", "80.000.000 VND/ngày"],
        ["Thanh toán POS", "100.000.000 VND/ngày", "200.000.000 VND/ngày"],
        ["Thanh toán trực tuyến", "50.000.000 VND/ngày", "100.000.000 VND/ngày"],
    ], [6 * cm, 5.2 * cm, 5.2 * cm])
    s += [
        D("Điều 7. Khóa thẻ"),
        B("Chủ thẻ đề nghị khóa thẻ tại quầy trong giờ làm việc hoặc qua tổng đài chăm sóc khách hàng; Ngân hàng chủ động khóa khi phát hiện giao dịch bất thường."),
    ]
    s += chuong_tochuc(9, [
        ("Khối Khách hàng cá nhân", ["Quản lý danh mục sản phẩm thẻ và hạn mức;"]),
        ("Trung tâm Thẻ", ["Vận hành phát hành, tra soát giao dịch thẻ;"]),
    ])
    s += dieu_hieuluc(10, "20 tháng 02 năm 2022")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối KHCN", "Trung tâm Thẻ", "Lưu: VT"])
    build_pdf("43_QD_205_2022_QD-DDB_the_v1_HET_HIEU_LUC.pdf", s)


# 44 — QĐ 490/2025/QĐ-DDB — Thẻ v2 (thay thế TOÀN BỘ 205; ATM 30tr)
@register
def doc_qd490():
    s = []
    s += internal_header(
        "490/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định phát hành và sử dụng thẻ (phiên bản 2.0)",
        "Hà Nội, ngày 10 tháng 4 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Thông tư số 18/2024/TT-NHNN ngày 20 tháng 8 năm 2024 của Ngân hàng Nhà nước quy định về hoạt động thẻ ngân hàng;"],
        "Giám đốc Khối Khách hàng cá nhân",
    )
    s += tbl_block("Điều 5. Hạn mức giao dịch thẻ ghi nợ", [
        ["Loại giao dịch", "Hạng chuẩn", "Hạng bạch kim"],
        ["Rút tiền mặt ATM", "**30.000.000 VND/ngày**", "**100.000.000 VND/ngày**"],
        ["Thanh toán POS", "200.000.000 VND/ngày", "500.000.000 VND/ngày"],
        ["Thanh toán trực tuyến", "Theo hạn mức kênh số hiện hành", "Theo hạn mức kênh số hiện hành"],
        ["Rút tiền mặt tại nước ngoài", "30.000.000 VND/ngày (trần theo TT 18/2024/TT-NHNN)", "30.000.000 VND/ngày"],
    ], [5.4 * cm, 5.6 * cm, 5.5 * cm])
    s += [
        D("Điều 6. Xác thực giao dịch thẻ trực tuyến"),
        B("Giao dịch thẻ trên môi trường trực tuyến áp dụng phương thức xác thực theo Quy định kênh số hiện hành của Ngân hàng và Thông tư số 35/2024/TT-NHNN."),
        D("Điều 7. Khóa thẻ khẩn cấp"),
        B("Chủ thẻ khóa thẻ **tức thời 24/7** trên ứng dụng Mobile Banking hoặc tổng đài; việc mở khóa yêu cầu xác thực sinh trắc học hoặc xác minh tại quầy."),
        D("Điều 8. Tra soát"),
        B("Việc tiếp nhận và xử lý tra soát, khiếu nại giao dịch thẻ thực hiện theo Quy định tra soát, khiếu nại hiện hành của Ngân hàng và Điều 11 Thông tư số 18/2024/TT-NHNN."),
    ]
    s += chuong_tochuc(10, [
        ("Khối Khách hàng cá nhân", ["Quản lý sản phẩm, chính sách hạn mức thẻ;"]),
        ("Trung tâm Thẻ", ["Vận hành phát hành, giám sát gian lận thẻ;"]),
    ])
    s += dieu_kiemtra(11)
    s += dieu_hieuluc(12, "15 tháng 4 năm 2025",
                      thaythe="Quyết định này **thay thế toàn bộ Quyết định số 205/2022/QĐ-DDB**.")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối KHCN", "Trung tâm Thẻ", "Lưu: VT"])
    build_pdf("44_QD_490_2025_QD-DDB_the_v2.pdf", s)


# 45 — QĐ 521/2025/QĐ-DDB — Tra soát khiếu nại (cross-chain thẻ + kênh số)
@register
def doc_qd521():
    s = []
    s += internal_header(
        "521/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định tra soát, xử lý khiếu nại giao dịch thẻ và kênh số",
        "Hà Nội, ngày 26 tháng 5 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Thông tư số 18/2024/TT-NHNN quy định về hoạt động thẻ ngân hàng;",
         "Căn cứ Quy định phát hành và sử dụng thẻ ban hành kèm theo Quyết định số 490/2025/QĐ-DDB;",
         "Căn cứ Quy định kênh số ban hành kèm theo Quyết định số 385/2025/QĐ-DDB;"],
        "Giám đốc Khối Vận hành",
    )
    s += [
        D("Điều 2. Tiếp nhận đề nghị tra soát"),
        B("Ngân hàng tiếp nhận đề nghị tra soát qua quầy, tổng đài và ứng dụng; **xác nhận tiếp nhận cho khách hàng trong vòng 24 (hai mươi bốn) giờ** kèm mã hồ sơ theo dõi."),
    ]
    s += tbl_block("Điều 3. Thời hạn xử lý tra soát", [
        ["Loại giao dịch", "Thời hạn tối đa", "Căn cứ"],
        ["Thẻ/chuyển tiền trong nước", "**45 ngày**", "Điều 11 Thông tư 18/2024/TT-NHNN"],
        ["Giao dịch có yếu tố nước ngoài", "**60 ngày**", "Quy tắc tổ chức thẻ quốc tế; cập nhật tiến độ 15 ngày/lần"],
        ["Giao dịch lỗi do hệ thống DDB", "05 ngày làm việc", "Chính sách nội bộ"],
    ], [6 * cm, 3.6 * cm, 6.9 * cm])
    s += [
        D("Điều 4. Tạm ứng cho khách hàng"),
        B("Trường hợp xác định lỗi thuộc hệ thống của Ngân hàng, đơn vị xử lý thực hiện **tạm ứng/hoàn trả cho khách hàng trong tối đa 05 ngày làm việc**, không chờ kết thúc quy trình đối soát với bên thứ ba."),
        D("Điều 5. Phạm vi áp dụng chung"),
        B("Quy định này áp dụng thống nhất cho khiếu nại giao dịch thẻ (theo Quyết định số 490/2025/QĐ-DDB) và giao dịch trên kênh số (theo Quyết định số 385/2025/QĐ-DDB)."),
    ]
    s += dieu_kiemtra(6)
    s += dieu_hieuluc(7, "30 tháng 5 năm 2025")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối Vận hành", "Trung tâm Thẻ", "Khối NHS", "Lưu: VT"])
    build_pdf("45_QD_521_2025_QD-DDB_tra_soat_khieu_nai.pdf", s)


# =====================================================================
# NHÓM I — AI MỞ RỘNG
# =====================================================================

# 46 — QĐ 530/2025/QĐ-DDB — Chatbot & trợ lý ảo (nối cả hai bên conflict AI)
@register
def doc_qd530():
    s = []
    s += internal_header(
        "530/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định triển khai chatbot và trợ lý ảo phục vụ khách hàng",
        "Hà Nội, ngày 05 tháng 6 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Thông tư số 04/2025/TT-NHNN về quản lý rủi ro khi ứng dụng trí tuệ nhân tạo trong hoạt động ngân hàng;",
         "Căn cứ Quy định bảo vệ dữ liệu cá nhân của khách hàng ban hành kèm theo Quyết định số 455/2025/QĐ-DDB;",
         "Căn cứ Quy định sử dụng trí tuệ nhân tạo trong hoạt động nội bộ ban hành kèm theo Quyết định số 502/2025/QĐ-DDB;"],
        "Giám đốc Khối Ngân hàng số",
    )
    s += [
        D("Điều 3. Nguyên tắc triển khai"),
        K("1. Chatbot phải tự giới thiệu là trợ lý ảo ngay đầu phiên; khách hàng có quyền yêu cầu **chuyển tiếp cán bộ hỗ trợ** bất kỳ lúc nào."),
        K("2. **Chatbot không được tự động ra quyết định phê duyệt tín dụng, mở/đóng tài khoản hoặc thay đổi hạn mức**; các đề nghị này chỉ được ghi nhận và chuyển quy trình nghiệp vụ có con người phê duyệt."),
        K("3. Mô hình dùng cho chatbot được phân loại, đánh giá rủi ro trước triển khai theo Thông tư số 04/2025/TT-NHNN và hướng dẫn nội bộ hiện hành."),
        D("Điều 4. Dữ liệu hội thoại"),
        K("1. Nội dung hội thoại được lưu trữ **tối đa 02 (hai) năm** phục vụ tra soát và cải thiện chất lượng; khách hàng được thông báo về việc ghi nhận hội thoại."),
        K("2. **Việc sử dụng nội dung hội thoại để huấn luyện, cải thiện mô hình phải qua quy trình ẩn danh hóa theo Điều 6 Quyết định số 502/2025/QĐ-DDB**, đồng thời **rà soát yêu cầu sự đồng ý riêng đối với dữ liệu cá nhân theo Điều 5 Quyết định số 455/2025/QĐ-DDB** trước khi đưa vào tập huấn luyện."),
        K("3. Không đưa vào tập huấn luyện các trường dữ liệu định danh trực tiếp (họ tên, số giấy tờ, số tài khoản) dưới mọi hình thức."),
        D("Điều 5. Giám sát chất lượng"),
        B("Khối Ngân hàng số đo lường tỷ lệ trả lời sai, tỷ lệ chuyển tiếp cán bộ và phản hồi khách hàng hằng tháng; mô hình có dấu hiệu suy giảm chất lượng phải được kiểm định lại theo hướng dẫn đánh giá rủi ro mô hình AI."),
    ]
    s += dieu_kiemtra(6)
    s += dieu_hieuluc(7, "10 tháng 6 năm 2025")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối NHS", "Khối PC&TT", "Lưu: VT, NHS"])
    build_pdf("46_QD_530_2025_QD-DDB_chatbot_tro_ly_ao.pdf", s)


# 47 — HD 09/2025/HD-DDB — Đánh giá rủi ro mô hình AI (3 mức; mức cao → HĐQT)
@register
def doc_hd09():
    s = []
    s += internal_header(
        "09/2025/HD-DDB", "HƯỚNG DẪN",
        "Đánh giá và phân loại rủi ro mô hình trí tuệ nhân tạo",
        "Hà Nội, ngày 16 tháng 6 năm 2025",
    )
    s += [
        CC("Thực hiện Thông tư số 04/2025/TT-NHNN và Nghị quyết số 09/2025/NQ-HĐQT-DDB về Khung quản trị an toàn thông tin và dữ liệu;"),
        CC("Khối Quản trị rủi ro hướng dẫn đánh giá rủi ro mô hình trí tuệ nhân tạo như sau:"),
        sp(),
    ]
    s += tbl_block("1. Phân loại mức rủi ro mô hình", [
        ["Mức", "Tiêu chí", "Ví dụ", "Cấp phê duyệt"],
        ["Thấp", "Không dùng dữ liệu cá nhân; không ảnh hưởng quyết định với khách hàng", "Gợi ý nội dung đào tạo nội bộ", "Giám đốc Khối chủ quản"],
        ["Trung bình", "Có dùng dữ liệu cá nhân đã ẩn danh; ảnh hưởng gián tiếp", "Phân nhóm khách hàng phục vụ chăm sóc", "Tổng Giám đốc"],
        ["Cao", "Ảnh hưởng trực tiếp quyền lợi khách hàng hoặc quyết định tự động", "**Chấm điểm tín dụng tự động**, định giá động", "**Hội đồng Quản trị** (theo NQ 09/2025/NQ-HĐQT-DDB)"],
    ], [2.2 * cm, 5.8 * cm, 4.6 * cm, 3.9 * cm])
    s += [
        D("2. Hồ sơ mô hình bắt buộc"),
    ]
    s += bullets([
        "Mô tả mục đích, phạm vi và dữ liệu huấn luyện (nguồn, cơ sở pháp lý sử dụng dữ liệu);",
        "Kết quả kiểm định độ chính xác, độ thiên lệch trước triển khai;",
        "Phương án giám sát sau triển khai và ngưỡng dừng khẩn cấp;",
        "Đánh giá tuân thủ bảo vệ dữ liệu cá nhân (NĐ 88/2024/NĐ-CP, QĐ 455/2025, QĐ 502/2025).",
    ])
    s += [
        D("3. Giám sát sau triển khai"),
        K("Mô hình mức trung bình trở lên được đánh giá lại **tối thiểu 06 tháng một lần** hoặc khi dữ liệu đầu vào thay đổi đáng kể (drift); kết quả cập nhật vào hồ sơ mô hình."),
        D("4. Danh mục mô hình"),
        K("Khối Quản trị rủi ro duy trì danh mục tập trung toàn bộ mô hình AI đang vận hành, cập nhật theo quý và báo cáo Ủy ban Quản lý rủi ro."),
    ]
    s += ky_ptgd("Phạm Thị D", ["Các Khối/đơn vị chủ quản mô hình", "Khối QTRR", "Lưu: VT, QTRR"])
    build_pdf("47_HD_09_2025_HD-DDB_danh_gia_rui_ro_mo_hinh_AI.pdf", s)


# =====================================================================
# NHÓM J — LƯU TRỮ & MẬT MÃ
# =====================================================================

# 48 — QĐ 260/2023/QĐ-DDB — Lưu trữ hồ sơ (bảng tổng hợp carve-out)
@register
def doc_qd260():
    s = []
    s += internal_header(
        "260/2023/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định lưu trữ hồ sơ, chứng từ",
        "Hà Nội, ngày 08 tháng 9 năm 2023",
    )
    s += qd_opening(
        ["Căn cứ quy định pháp luật về kế toán, giao dịch điện tử và lưu trữ trong hoạt động ngân hàng;"],
        "Giám đốc Khối Vận hành",
    )
    s += [
        D("Điều 2. Nguyên tắc chung"),
        K("1. Thời hạn lưu trữ xác định **theo loại hồ sơ**; một bộ hồ sơ chứa nhiều loại tài liệu thì áp dụng thời hạn dài nhất trong số các tài liệu thành phần."),
        K("2. **Trường hợp pháp luật chuyên ngành quy định thời hạn khác với quy định chung, áp dụng theo pháp luật chuyên ngành** — đây là nguyên tắc phân định, không phải xung đột giữa các văn bản."),
    ]
    s += tbl_block("Điều 3. Bảng thời hạn lưu trữ theo loại hồ sơ", [
        ["Loại hồ sơ, chứng từ", "Thời hạn lưu trữ", "Căn cứ"],
        ["Chứng từ kế toán tổng hợp", "10 năm", "Pháp luật kế toán"],
        ["Hồ sơ tín dụng", "**15 năm** kể từ ngày tất toán", "Chính sách nội bộ"],
        ["Hồ sơ, dữ liệu cá nhân khách hàng", "Theo quy định pháp luật về bảo vệ dữ liệu cá nhân trong từng thời kỳ", "Văn bản pháp luật hiện hành về DLCN"],
        ["Hồ sơ nhận biết khách hàng, PCRT", "Tối thiểu 10 năm", "Pháp luật phòng, chống rửa tiền"],
        ["Chứng từ giao dịch điện tử", "Tối thiểu 10 năm", "Pháp luật giao dịch điện tử"],
        ["Thư bảo lãnh, cam kết", "10 năm sau khi hết hiệu lực", "Chính sách nội bộ"],
    ], [6.4 * cm, 4.6 * cm, 5.5 * cm])
    s += [
        D("Điều 5. Tiêu hủy hồ sơ hết thời hạn"),
        B("Hồ sơ hết thời hạn lưu trữ được tiêu hủy theo quyết định của Hội đồng tiêu hủy; hồ sơ chứa dữ liệu cá nhân phải tiêu hủy bằng phương pháp không thể khôi phục và lập biên bản."),
    ]
    s += chuong_tochuc(7, [
        ("Khối Vận hành", ["Quản lý kho lưu trữ tập trung, theo dõi thời hạn;"]),
        ("Các đơn vị", ["Nộp lưu đúng hạn, phân loại đúng danh mục;"]),
    ])
    s += dieu_hieuluc(8, "15 tháng 9 năm 2023")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Khối Vận hành", "Các đơn vị", "Lưu: VT"])
    build_pdf("48_QD_260_2023_QD-DDB_luu_tru_ho_so.pdf", s)


# 49 — QĐ 535/2025/QĐ-DDB — Khóa mật mã & chứng thư số (HSM cho trọng yếu)
@register
def doc_qd535():
    s = []
    s += internal_header(
        "535/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc ban hành Quy định quản lý khóa mật mã và chứng thư số",
        "Hà Nội, ngày 18 tháng 6 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ Nghị định số 88/2024/NĐ-CP về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng;",
         "Căn cứ Quy chế An toàn thông tin ban hành kèm theo Quyết định số 342/2024/QĐ-DDB;"],
        "Giám đốc Trung tâm Công nghệ thông tin",
    )
    s += [
        D("Điều 2. Chuẩn mã hóa"),
        K("1. Dữ liệu cá nhân nhạy cảm của khách hàng khi lưu trữ phải được mã hóa **tối thiểu chuẩn AES-256**; khi truyền trên môi trường mạng sử dụng TLS phiên bản 1.2 trở lên."),
        K("2. Thuật toán, độ dài khóa yếu (DES, RC4, SHA-1 cho chữ ký) không được sử dụng cho hệ thống mới và phải có lộ trình loại bỏ khỏi hệ thống hiện hữu."),
        D("Điều 3. Quản lý khóa"),
        K("1. **Khóa mật mã của các hệ thống thuộc danh mục hệ thống trọng yếu** (xác định theo Quy định phân loại hệ thống công nghệ thông tin — Quyết định số 173/2023/QĐ-DDB) **phải được sinh và lưu giữ trong thiết bị HSM đạt chuẩn**, không xuất khóa ra ngoài dưới dạng rõ."),
        K("2. Khóa mã hóa dữ liệu được **thay đổi (rotate) tối thiểu 12 (mười hai) tháng một lần** hoặc ngay khi nghi ngờ lộ khóa."),
        K("3. Việc chia tách quyền quản lý khóa thực hiện theo nguyên tắc không một cá nhân nào nắm toàn bộ thành phần khóa chính."),
        D("Điều 4. Chứng thư số"),
        K("1. Chứng thư số cấp cho cán bộ được thu hồi **trong vòng 24 giờ** khi cán bộ nghỉ việc, đồng bộ với quy trình thu hồi tài khoản người dùng."),
        K("2. Danh mục chứng thư số hệ thống được rà soát hằng quý; chứng thư sắp hết hạn phải gia hạn trước tối thiểu 15 ngày."),
    ]
    s += dieu_kiemtra(5)
    s += dieu_hieuluc(6, "25 tháng 6 năm 2025")
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "TT CNTT", "Lưu: VT, CNTT"])
    build_pdf("49_QD_535_2025_QD-DDB_khoa_mat_ma_chung_thu_so.pdf", s)


# 50 — HD 15/2024/HD-DDB — Xử lý yêu cầu quyền chủ thể dữ liệu (dùng PL01 QĐ 133)
@register
def doc_hd15():
    s = []
    s += internal_header(
        "15/2024/HD-DDB", "HƯỚNG DẪN",
        "Tiếp nhận và xử lý yêu cầu thực hiện quyền của chủ thể dữ liệu",
        "Hà Nội, ngày 02 tháng 12 năm 2024",
    )
    s += [
        CC("Thực hiện Nghị định số 88/2024/NĐ-CP về bảo vệ dữ liệu cá nhân trong hoạt động của tổ chức tín dụng;"),
        CC("Khối Pháp chế và Tuân thủ hướng dẫn thống nhất việc xử lý yêu cầu của khách hàng như sau:"),
        sp(),
        D("1. Các quyền được tiếp nhận"),
        B("Quyền được biết, quyền truy cập/chỉnh sửa, quyền yêu cầu xóa, quyền rút lại sự đồng ý và quyền phản đối xử lý cho mục đích tiếp thị theo Điều 12 Nghị định số 88/2024/NĐ-CP."),
        D("2. Kênh tiếp nhận và thời hạn"),
        K("a) Tiếp nhận tại quầy, tổng đài hoặc mục Quản lý dữ liệu cá nhân trên ứng dụng; mọi yêu cầu được cấp mã theo dõi."),
        K("b) **Xác nhận đã tiếp nhận trong vòng 72 (bảy mươi hai) giờ**; **giải quyết trong 15 (mười lăm) ngày** kể từ ngày tiếp nhận. Trường hợp phức tạp được gia hạn một lần tối đa 15 ngày và phải thông báo lý do."),
        D("3. Xác minh và biểu mẫu"),
        K("a) Xác minh danh tính người yêu cầu trước khi xử lý để tránh lộ dữ liệu cho người không có quyền."),
        K("b) Việc ghi nhận sự đồng ý mới hoặc thay đổi phạm vi đồng ý sử dụng **Mẫu văn bản đồng ý tại Phụ lục 01 ban hành kèm theo Quyết định số 133/2022/QĐ-DDB** cho đến khi Ngân hàng ban hành biểu mẫu thay thế."),
        D("4. Trường hợp từ chối"),
        B("Chỉ từ chối khi pháp luật cho phép (ví dụ: dữ liệu buộc phải lưu theo pháp luật phòng, chống rửa tiền); văn bản trả lời phải nêu rõ căn cứ pháp lý và quyền khiếu nại của khách hàng."),
        D("5. Lưu hồ sơ"),
        B("Hồ sơ tiếp nhận – xử lý yêu cầu được lưu tối thiểu 05 năm phục vụ chứng minh tuân thủ."),
    ]
    s += ky_ptgd("Phạm Thị D", ["Các CN/PGD", "Khối Vận hành", "Lưu: VT, PC"])
    build_pdf("50_HD_15_2024_HD-DDB_quyen_chu_the_du_lieu.pdf", s)


# 51 — QĐ 540/2025/QĐ-DDB — Công bố danh mục văn bản hết hiệu lực (nguồn khai báo THAY_THE)
@register
def doc_qd540():
    s = []
    s += internal_header(
        "540/2025/QĐ-DDB", "QUYẾT ĐỊNH",
        "Về việc công bố Danh mục văn bản quy định nội bộ hết hiệu lực toàn bộ hoặc một phần",
        "Hà Nội, ngày 30 tháng 6 năm 2025",
    )
    s += qd_opening(
        ["Căn cứ kết quả rà soát định kỳ hệ thống văn bản quy định nội bộ 6 tháng đầu năm 2025;"],
    )
    s += [
        D("Điều 1. Công bố danh mục"),
        B("Công bố kèm theo Quyết định này Danh mục văn bản quy định nội bộ của Ngân hàng TMCP Đông Đô **hết hiệu lực toàn bộ hoặc một phần** tính đến ngày 30/6/2025."),
    ]
    s += tbl_block("DANH MỤC VĂN BẢN HẾT HIỆU LỰC", [
        ["Văn bản", "Phạm vi hết hiệu lực", "Văn bản thay thế", "Phần còn hiệu lực"],
        ["QĐ 215/2022/QĐ-DDB (Quy chế ATTT v1)", "Một phần", "QĐ 342/2024/QĐ-DDB", "**Phụ lục 02 — Danh mục hệ thống trọng yếu**"],
        ["QĐ 118/2021/QĐ-DDB (Ngân hàng điện tử v1)", "Một phần", "QĐ 385/2025/QĐ-DDB", "**Phụ lục 03 — Biểu hạn mức theo kênh** (đến khi có biểu mới)"],
        ["QĐ 267/2023/QĐ-DDB (sửa đổi QĐ 118)", "**Toàn bộ**", "QĐ 385/2025/QĐ-DDB", "Không"],
        ["QĐ 133/2022/QĐ-DDB (Quản lý TTKH)", "Một phần", "QĐ 455/2025/QĐ-DDB", "**Phụ lục 01 — Mẫu văn bản đồng ý** (đến khi có mẫu mới)"],
        ["QĐ 301/2023/QĐ-DDB (Nhận biết khách hàng)", "**Toàn bộ**", "QĐ 480/2025/QĐ-DDB", "Không"],
        ["QĐ 205/2022/QĐ-DDB (Phát hành thẻ v1)", "**Toàn bộ**", "QĐ 490/2025/QĐ-DDB", "Không"],
    ], [4.6 * cm, 2.6 * cm, 3.6 * cm, 5.7 * cm])
    s += [
        D("Điều 2. Nguyên tắc áp dụng"),
        K("1. Văn bản hết hiệu lực toàn bộ không được viện dẫn làm căn cứ nghiệp vụ kể từ ngày văn bản thay thế có hiệu lực."),
        K("2. Đối với văn bản hết hiệu lực một phần, **chỉ phần được liệt kê tại cột \"Phần còn hiệu lực\" tiếp tục được áp dụng**; việc viện dẫn phải ghi rõ tên phụ lục và số hiệu văn bản gốc."),
        K("3. Tài liệu hướng dẫn, FAQ, quy trình đơn vị viện dẫn các văn bản trong Danh mục phải được đơn vị chủ trì rà soát, cập nhật trong quý III/2025."),
        D("Điều 3. Hiệu lực thi hành"),
        B("Quyết định này có hiệu lực kể từ ngày ký. Danh mục được cập nhật định kỳ 6 tháng một lần."),
    ]
    s += ky_tgd("Lê Văn C", ["Ban Tổng Giám đốc", "Các Khối/đơn vị", "Các CN/PGD", "Lưu: VT, PC"])
    build_pdf("51_QD_540_2025_QD-DDB_danh_muc_van_ban_het_hieu_luc.pdf", s)


if __name__ == "__main__":
    print("Đang sinh bộ văn bản mô phỏng v2 (tài liệu 11–51) ...")
    for fn in DOCS:
        fn()
    print("Xong %d văn bản v2." % len(DOCS))
