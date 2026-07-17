"""Cổng kiểm tra ngôn ngữ tiếng Việt cho testset sinh tự động (offline, không gọi mạng)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Toàn bộ ký tự có dấu đặc trưng tiếng Việt (chữ thường; so khớp trên text.lower()).
_VN_DIACRITICS = set(
    "ăâđêôơư"
    "àảãáạằẳẵắặầẩẫấậ"
    "èẻẽéẹềểễếệ"
    "ìỉĩíị"
    "òỏõóọồổỗốộờởỡớợ"
    "ùủũúụừửữứự"
    "ỳỷỹýỵ"
)


def is_vietnamese(text: str) -> bool:
    """Heuristic: có ít nhất 1 ký tự dấu tiếng Việt => tiếng Việt.
    Câu thuần ASCII ("What is the annual fee?") => False. Không gọi mạng."""
    return any(ch in _VN_DIACRITICS for ch in text.lower())


GATE_REASON = "not-vietnamese"
DEFAULT_MAX_EXCLUSION_RATE = 0.2  # NFR-5
_CHECKED_FIELDS = ("user_input", "reference")


@dataclass
class GateResult:
    retained: list[dict]
    excluded: list[dict]          # sample + {"reason": GATE_REASON, "failed_fields": [...]}
    exclusion_rate: float         # excluded / total (0.0 nếu total == 0)
    failed_quality: bool          # exclusion_rate > threshold
    threshold: float = DEFAULT_MAX_EXCLUSION_RATE


def apply_language_gate(
    samples: list[dict],
    *,
    threshold: float = DEFAULT_MAX_EXCLUSION_RATE,
) -> GateResult:
    """Kiểm tra cả `user_input` và `reference`; sample bị loại nếu BẤT KỲ trường nào
    không phải tiếng Việt. Sample bị loại được gắn reason + failed_fields."""
    retained: list[dict] = []
    excluded: list[dict] = []
    for sample in samples:
        failed_fields = [
            field for field in _CHECKED_FIELDS
            if field in sample and not is_vietnamese(str(sample[field]))
        ]
        if failed_fields:
            excluded.append({**sample, "reason": GATE_REASON, "failed_fields": failed_fields})
        else:
            retained.append(sample)

    total = len(samples)
    exclusion_rate = (len(excluded) / total) if total else 0.0
    return GateResult(
        retained=retained,
        excluded=excluded,
        exclusion_rate=exclusion_rate,
        failed_quality=exclusion_rate > threshold,
        threshold=threshold,
    )


def write_exclusion_report(result: GateResult, path: Path) -> None:
    """Ghi JSON report (UTF-8, ensure_ascii=False)."""
    total = len(result.retained) + len(result.excluded)
    report = {
        "total": total,
        "retained": len(result.retained),
        "excluded": len(result.excluded),
        "exclusion_rate": result.exclusion_rate,
        "threshold": result.threshold,
        "failed_quality": result.failed_quality,
        "excluded_samples": result.excluded,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def enforce_quality(result: GateResult) -> int:
    """Trả về exit code: 0 nếu đạt, 2 nếu failed_quality (NFR-5)."""
    return 2 if result.failed_quality else 0
