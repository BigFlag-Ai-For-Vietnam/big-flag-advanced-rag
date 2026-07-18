# -*- coding: utf-8 -*-
"""Sinh bộ văn bản tuân thủ MÔ PHỎNG (fictional) phục vụ kiểm thử RAG + Graph extraction.

Ngân hàng giả định: Ngân hàng TMCP Đông Đô (DongDoBank - DDB). Mọi số hiệu/nội dung là
GIẢ LẬP, không phải văn bản pháp luật thật (mỗi trang có watermark + disclaimer).

Thiết kế để test 3 pain point:
  P1 - Hết hiệu lực & thay thế: QĐ 342/2024 THAY THẾ QĐ 215/2022 (một phần: giữ Phụ lục 02).
  P2 - Overlap/xung đột điều khoản: có ca tuyên bố ưu tiên, có ca im lặng.
  P3 - Liên kết văn bản Nhà nước <-> entity văn bản tuân thủ nội bộ (căn cứ / tham chiếu).
"""
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import Color, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    KeepTogether,
)

FONT_DIR = "/System/Library/Fonts/Supplemental"
pdfmetrics.registerFont(TTFont("TNR", os.path.join(FONT_DIR, "Times New Roman.ttf")))
pdfmetrics.registerFont(TTFont("TNR-B", os.path.join(FONT_DIR, "Times New Roman Bold.ttf")))
pdfmetrics.registerFont(TTFont("TNR-I", os.path.join(FONT_DIR, "Times New Roman Italic.ttf")))
pdfmetrics.registerFont(TTFont("TNR-BI", os.path.join(FONT_DIR, "Times New Roman Bold Italic.ttf")))
pdfmetrics.registerFontFamily("TNR", normal="TNR", bold="TNR-B", italic="TNR-I", boldItalic="TNR-BI")

OUT_DIR = "/Users/perfogic/Workspace/Research/big-flag-advanced-rag/sample_compliance_corpus"
os.makedirs(OUT_DIR, exist_ok=True)

# ------------------------------------------------------------------ styles
ss = getSampleStyleSheet()

def _st(name, **kw):
    base = dict(fontName="TNR", fontSize=13, leading=18, spaceAfter=6)
    base.update(kw)
    return ParagraphStyle(name, parent=ss["Normal"], **base)

S = {
    "quochieu": _st("quochieu", fontName="TNR-B", fontSize=13, alignment=TA_CENTER, spaceAfter=0, leading=16),
    "tieungu":  _st("tieungu", fontName="TNR-BI", fontSize=13, alignment=TA_CENTER, spaceAfter=2, leading=16),
    "sohieu":   _st("sohieu", fontName="TNR", fontSize=12, alignment=TA_CENTER, leading=15, spaceAfter=0),
    "sohieu_b": _st("sohieu_b", fontName="TNR-B", fontSize=12, alignment=TA_CENTER, leading=15, spaceAfter=0),
    "diadanh":  _st("diadanh", fontName="TNR-I", fontSize=13, alignment=TA_RIGHT, leading=16, spaceAfter=0),
    "loaivb":   _st("loaivb", fontName="TNR-B", fontSize=14, alignment=TA_CENTER, leading=19, spaceBefore=6, spaceAfter=2),
    "trichyeu": _st("trichyeu", fontName="TNR-B", fontSize=13, alignment=TA_CENTER, leading=18, spaceAfter=10),
    "cancu":    _st("cancu", fontName="TNR-I", fontSize=13, alignment=TA_JUSTIFY, leading=17, spaceAfter=3),
    "chuong":   _st("chuong", fontName="TNR-B", fontSize=13, alignment=TA_CENTER, leading=18, spaceBefore=8, spaceAfter=2),
    "dieu":     _st("dieu", fontName="TNR-B", fontSize=13, alignment=TA_JUSTIFY, leading=18, spaceBefore=6, spaceAfter=3),
    "body":     _st("body", fontName="TNR", fontSize=13, alignment=TA_JUSTIFY, leading=18, spaceAfter=5, firstLineIndent=0.8*cm),
    "khoan":    _st("khoan", fontName="TNR", fontSize=13, alignment=TA_JUSTIFY, leading=18, spaceAfter=5, leftIndent=0.6*cm),
    "kysig":    _st("kysig", fontName="TNR-B", fontSize=13, alignment=TA_CENTER, leading=17, spaceAfter=0),
    "kyrole":   _st("kyrole", fontName="TNR-BI", fontSize=12, alignment=TA_CENTER, leading=15, spaceAfter=0),
    "noinhan":  _st("noinhan", fontName="TNR-BI", fontSize=11, leading=13, spaceAfter=0),
    "noinhan_i":_st("noinhan_i", fontName="TNR-I", fontSize=11, leading=13, spaceAfter=0),
    "tblhdr":   _st("tblhdr", fontName="TNR-B", fontSize=11, alignment=TA_CENTER, leading=14, spaceAfter=0),
    "tbl":      _st("tbl", fontName="TNR", fontSize=11, alignment=TA_JUSTIFY, leading=14, spaceAfter=0),
}


def esc(t: str) -> str:
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return t


def P(text, style="body"):
    return Paragraph(esc(text), S[style])


# ------------------------------------------------------------------ page decoration
def _decorate(c, doc):
    """Disclaimer đặt ở LỀ TRÊN + LỀ DƯỚI (ngoài vùng body text) để KHÔNG đè lên nội dung —
    tránh làm nhiễu VLM parsing (watermark chéo giữa trang sẽ bị OCR nuốt vào parsed_text
    và cắt ngang các dòng chữ, giảm độ chính xác)."""
    w, h = A4
    c.saveState()
    # tag mô phỏng ở lề trên (band trắng phía trên frame body)
    c.setFont("TNR-I", 8)
    c.setFillColor(Color(0.5, 0.5, 0.5))
    c.drawCentredString(w / 2, h - 0.9 * cm,
                        "TÀI LIỆU MÔ PHỎNG – DỮ LIỆU KIỂM THỬ – KHÔNG CÓ GIÁ TRỊ PHÁP LÝ")
    # footer ở lề dưới
    c.setFont("TNR-I", 8)
    c.setFillColor(Color(0.5, 0.5, 0.5))
    c.drawString(2 * cm, 1.05 * cm,
                 "Tài liệu giả lập phục vụ kiểm thử hệ thống RAG/Graph — không phải văn bản pháp luật hoặc quy định thật.")
    c.setFont("TNR", 9)
    c.setFillColor(Color(0.3, 0.3, 0.3))
    c.drawRightString(w - 2 * cm, 1.05 * cm, "Trang %d" % doc.page)
    c.restoreState()


def build_pdf(filename, story):
    path = os.path.join(OUT_DIR, filename)
    doc = BaseDocTemplate(
        path, pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title=filename,
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="body")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=_decorate)])
    doc.build(story)
    print("  ->", path)


# ------------------------------------------------------------------ header builders
def state_header(so_hieu, co_quan, loai, trich_yeu, dia_danh_ngay):
    """Header văn bản Nhà nước: quốc hiệu 2 cột."""
    left = [
        Paragraph(esc(co_quan), S["sohieu_b"]),
        Paragraph("<b>_______</b>", S["sohieu"]),
        Spacer(1, 4),
        Paragraph("Số: " + esc(so_hieu), S["sohieu"]),
    ]
    right = [
        Paragraph("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", S["quochieu"]),
        Paragraph("Độc lập - Tự do - Hạnh phúc", S["tieungu"]),
        Paragraph("<b>_______________</b>", S["sohieu"]),
        Spacer(1, 4),
        Paragraph(esc(dia_danh_ngay), S["diadanh"]),
    ]
    t = Table([[left, right]], colWidths=[6.5 * cm, 9.5 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [t, Spacer(1, 10),
            Paragraph(esc(loai), S["loaivb"]),
            Paragraph(esc(trich_yeu), S["trichyeu"])]


def internal_header(so_hieu, loai, trich_yeu, dia_danh_ngay):
    """Header văn bản nội bộ ngân hàng (letterhead giả định)."""
    left = [
        Paragraph("NGÂN HÀNG TMCP ĐÔNG ĐÔ", S["sohieu_b"]),
        Paragraph("<b>(DongDoBank - DDB)</b>", S["sohieu"]),
        Paragraph("<b>_______</b>", S["sohieu"]),
        Spacer(1, 4),
        Paragraph("Số: " + esc(so_hieu), S["sohieu"]),
    ]
    right = [
        Paragraph("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", S["quochieu"]),
        Paragraph("Độc lập - Tự do - Hạnh phúc", S["tieungu"]),
        Paragraph("<b>_______________</b>", S["sohieu"]),
        Spacer(1, 4),
        Paragraph(esc(dia_danh_ngay), S["diadanh"]),
    ]
    t = Table([[left, right]], colWidths=[6.5 * cm, 9.5 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [t, Spacer(1, 10),
            Paragraph(esc(loai), S["loaivb"]),
            Paragraph(esc(trich_yeu), S["trichyeu"])]


def sign_block(role, name, extra_left=None):
    left_cells = extra_left or [Paragraph("<b>Nơi nhận:</b>", S["noinhan_i"])]
    right = [
        Paragraph(esc(role), S["kyrole"]),
        Spacer(1, 40),
        Paragraph(esc(name), S["kysig"]),
    ]
    t = Table([[left_cells, right]], colWidths=[8.5 * cm, 7.5 * cm])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
    ]))
    return [Spacer(1, 12), t]


def noinhan(items):
    out = [Paragraph("<b>Nơi nhận:</b>", S["noinhan"])]
    for it in items:
        out.append(Paragraph("- " + esc(it) + ";", S["noinhan_i"]))
    return out


def value_table(rows, col_widths, header=True):
    data = []
    for i, r in enumerate(rows):
        style = "tblhdr" if (header and i == 0) else "tbl"
        data.append([Paragraph(esc(str(c)), S[style]) for c in r])
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.6, black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), Color(0.9, 0.9, 0.93) if header else Color(1, 1, 1)),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t
