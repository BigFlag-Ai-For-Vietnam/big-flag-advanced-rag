"""Regex số hiệu văn bản (vd "09/2024/TT-NHNN") — khoá tự nhiên dùng để gộp VanBan trùng
(entity_resolution.resolve_vanban) và trích citation edge (citation_extractor). Module
riêng, KHÔNG import gì khác — để citation_extractor.extract_citations_from_text() (pure
function, zero I/O, regex-only) test được mà không kéo theo lightrag/numpy (qua
entity_resolution -> llm_adapter)."""
import re

SO_HIEU_RE = re.compile(r"\d{1,4}/\d{4}/(?:NĐ-CP|TT-NHNN|QĐ-DDB)")
