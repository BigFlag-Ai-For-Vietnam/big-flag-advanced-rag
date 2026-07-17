"""Bước A — Parsing chất lượng cao bằng VLM.

Mỗi trang PDF -> render PNG -> gửi VLM (model vision trên FPT) -> Markdown sạch.
Giới hạn concurrency, có retry cho mỗi trang.

An toàn:
- Strip dấu ``` code fence mà model hay bọc quanh output.
- Nếu VLM trả rỗng cho 1 trang và bật PARSE_TEXT_FALLBACK, dùng text-layer của
  pdfplumber (page.extract_text) làm phương án dự phòng. Điều này giúp không bị
  "document rỗng" khi model cấu hình sai (không hỗ trợ vision) hoặc PDF có sẵn text layer.
"""
from __future__ import annotations

import io
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import pdfplumber
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.services import llm_client

logger = logging.getLogger("parsing_service")

VLM_PROMPT = (
    "Bạn là công cụ OCR/parse tài liệu. Hãy chuyển toàn bộ nội dung trang tài liệu "
    "trong ảnh sang MARKDOWN sạch bằng đúng ngôn ngữ gốc.\n"
    "- Giữ đúng heading, danh sách, và bảng (dùng cú pháp bảng Markdown).\n"
    "- Giữ nguyên số liệu, tên riêng, điều khoản.\n"
    "- KHÔNG bịa thêm nội dung không có trong ảnh. Nếu trang trống, trả về chuỗi rỗng.\n"
    "- KHÔNG bọc kết quả trong dấu ``` code fence. Chỉ trả về Markdown thuần, không lời giải thích."
)

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*\n?|\n?```\s*$")


def strip_code_fence(text: str) -> str:
    """Bỏ ```markdown ... ``` mà model hay bọc quanh output; trả về nội dung bên trong."""
    if not text:
        return ""
    t = text.strip()
    # Trường hợp bọc trọn: bắt đầu bằng ``` và kết thúc bằng ```
    if t.startswith("```") and t.endswith("```"):
        t = t[3:-3]
        # bỏ label ngôn ngữ ở dòng đầu (vd 'markdown')
        first_nl = t.find("\n")
        if first_nl != -1 and t[:first_nl].strip().isalpha():
            t = t[first_nl + 1 :]
        return t.strip()
    # Trường hợp chỉ có fence lẻ đầu/cuối
    t = _FENCE_RE.sub("", t)
    return t.strip()


def render_page_png(page, resolution: int = 200) -> bytes:
    """Render 1 page pdfplumber thành PNG bytes."""
    img = page.to_image(resolution=resolution)
    buf = io.BytesIO()
    img.original.save(buf, format="PNG")
    return buf.getvalue()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=20))
def _parse_page_image(png: bytes) -> str:
    raw = llm_client.vision(png, VLM_PROMPT, tag="vlm_parse")
    return strip_code_fence(raw)


def parse_pdf(file_path: str, image_dir: str | None = None) -> list[dict]:
    """Parse toàn bộ PDF. Trả về list[{page_number, parsed_text, image_ref, used_fallback}].

    image_dir: nếu có, lưu ảnh mỗi trang ra file để tham chiếu; nếu None thì không lưu.
    """
    rendered: list[tuple[int, bytes, str | None, str]] = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            png = render_page_png(page)
            text_layer = (page.extract_text() or "").strip()
            image_ref = None
            if image_dir:
                os.makedirs(image_dir, exist_ok=True)
                image_ref = os.path.join(image_dir, f"page_{i:04d}.png")
                with open(image_ref, "wb") as fh:
                    fh.write(png)
            rendered.append((i, png, image_ref, text_layer))

    results: dict[int, dict] = {}
    max_workers = max(1, settings.vlm_max_concurrency)
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_map = {
            pool.submit(_parse_page_image, png): (page_number, image_ref, text_layer)
            for page_number, png, image_ref, text_layer in rendered
        }
        for future in as_completed(future_map):
            page_number, image_ref, text_layer = future_map[future]
            vlm_text = future.result()  # đã retry bên trong; fail sẽ raise lên pipeline
            used_fallback = False
            parsed = vlm_text
            if not parsed.strip() and settings.parse_text_fallback and text_layer:
                # VLM rỗng -> dùng text layer của PDF làm dự phòng
                parsed = text_layer
                used_fallback = True
                logger.warning(
                    "Trang %s: VLM trả rỗng, dùng text-layer PDF làm dự phòng (%s ký tự).",
                    page_number,
                    len(text_layer),
                )
            results[page_number] = {
                "page_number": page_number,
                "parsed_text": parsed,
                "image_ref": image_ref,
                "used_fallback": used_fallback,
            }

    return [results[k] for k in sorted(results)]


def join_pages(pages: list[dict]) -> str:
    """Ghép parsed_text các trang (theo thứ tự) thành full_document_text."""
    parts = [p["parsed_text"].strip() for p in pages if (p.get("parsed_text") or "").strip()]
    return "\n\n".join(parts)
