"""Xây query_distribution tường minh cho ragas TestsetGenerator (FR-3).

KHÔNG dùng ragas.testset.synthesizers.default_query_distribution — nó lọc bỏ
synthesizer thầm lặng (dựa trên cluster có sẵn trên KG) và có thể raise ValueError
nếu không synthesizer nào còn lại. FR-3 yêu cầu phân bổ tường minh, xác định trước.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ragas.testset.synthesizers import (
    MultiHopAbstractQuerySynthesizer,
    MultiHopSpecificQuerySynthesizer,
    SingleHopSpecificQuerySynthesizer,
)


@dataclass(frozen=True)
class DistributionWeights:
    """Trọng số phân bổ 3 loại câu hỏi; PHẢI cộng lại bằng 1.0."""
    single_hop_specific: float = 0.5
    multi_hop_abstract: float = 0.25
    multi_hop_specific: float = 0.25

    def __post_init__(self) -> None:
        total = self.single_hop_specific + self.multi_hop_abstract + self.multi_hop_specific
        if not math.isclose(total, 1.0, abs_tol=1e-9):
            raise ValueError(
                f"query_distribution weights phải cộng lại = 1.0 (nhận {total})"
            )


# Ràng buộc văn phong + de-reference tiêm THẲNG vào prompt sinh query của ragas (mọi synthesizer),
# để `dataset generate` sinh ra câu hỏi kiểu v3 NGAY LÚC generate — không cần bước rewrite hậu kỳ:
# câu hỏi tự nhiên như nhân viên ngân hàng thật hỏi, KHÔNG trích tên/số hiệu văn bản, số Điều/Khoản,
# nhãn phiên bản; chỉ hỏi về nội dung/tình huống. Answer vẫn phải trung thực theo context.
_STYLE_MARKER = "### Phong cách & ràng buộc de-reference"
_STYLE_INSTRUCTION = (
    "\n\n" + _STYLE_MARKER + " (BẮT BUỘC cho QUERY):\n"
    "- Viết QUERY bằng tiếng Việt tự nhiên, đúng giọng một nhân viên ngân hàng thật hỏi trong công "
    "việc (đời thường, hỏi thẳng vào tình huống), KHÔNG máy móc/sách vở.\n"
    "- TUYỆT ĐỐI KHÔNG nêu trong QUERY: tên/số hiệu văn bản (Nghị định, Thông tư, Quyết định kèm số "
    "như 88/2024/NĐ-CP, 04/2025/TT-NHNN, QĐ 342...), số Điều/Khoản, nhãn phiên bản (v1.0, phiên bản "
    "2.0), hay tiêu đề tài liệu.\n"
    "- Người hỏi KHÔNG biết & KHÔNG trích số hiệu văn bản — chỉ hỏi về NỘI DUNG/QUY ĐỊNH/tình huống "
    "(ngưỡng, thời hạn, quy trình, được phép hay không). Giữ nguyên các con số nội dung (tiền, năm, "
    "số ký tự...).\n"
    "- Nếu là câu so sánh giữa quy định cũ và mới, hỏi kiểu 'quy định ... hiện nay áp dụng thế nào / "
    "gần đây có thay đổi gì' mà KHÔNG nêu tên văn bản nào.\n"
    "- ANSWER vẫn phải trung thực 100% theo context (answer có thể nêu nguồn; chỉ QUERY là không được)."
)


def _apply_style(synth):
    """Tiêm ràng buộc de-reference + văn phong tự nhiên vào prompt sinh query của synthesizer
    (idempotent — không tiêm lại nếu đã có marker)."""
    prompt = getattr(synth, "generate_query_reference_prompt", None)
    if prompt is not None and _STYLE_MARKER not in prompt.instruction:
        prompt.instruction = prompt.instruction + _STYLE_INSTRUCTION
    return synth


def build_query_distribution(llm, weights: DistributionWeights | None = None):
    """Trả về query_distribution tường minh cho ragas TestsetGenerator.

    KHÔNG dùng default_query_distribution (nó lọc bỏ synthesizer thầm lặng và có thể raise).
    Mỗi synthesizer được tiêm ràng buộc de-reference + văn phong tự nhiên vào prompt (_apply_style)
    nên câu hỏi sinh ra đã ở dạng thực tế (không trích số hiệu văn bản) ngay từ đầu.
    """
    weights = weights or DistributionWeights()  # __post_init__ đã validate
    return [
        (_apply_style(SingleHopSpecificQuerySynthesizer(llm=llm)), weights.single_hop_specific),
        (_apply_style(MultiHopAbstractQuerySynthesizer(llm=llm)), weights.multi_hop_abstract),
        (_apply_style(MultiHopSpecificQuerySynthesizer(llm=llm)), weights.multi_hop_specific),
    ]


@dataclass
class MultiHopAvailability:
    synthesizer_name: str
    num_clusters: int
    available: bool


def apply_backfill(distribution, availability: list[MultiHopAvailability]):
    """Loại synthesizer 0-cluster khỏi distribution, dồn trọng số về SingleHopSpecific
    (trivial). Không bao giờ raise vì KG thiếu cluster — chỉ raise nếu bản thân
    reallocation phá vỡ bất biến tổng trọng số == 1.0 (lỗi lập trình, không phải input xấu).

    Trả về (new_distribution, shortfall_report); report rỗng nếu mọi synthesizer available."""
    unavailable = {a.synthesizer_name: a for a in availability if not a.available}
    if not unavailable:
        return distribution, []

    reallocated = 0.0
    reallocated_weight_by_name: dict[str, float] = {}
    kept: list[list] = []
    for synth, weight in distribution:
        if synth.name in unavailable:
            reallocated += weight
            reallocated_weight_by_name[synth.name] = weight
        else:
            kept.append([synth, weight])

    for entry in kept:
        if isinstance(entry[0], SingleHopSpecificQuerySynthesizer):
            entry[1] += reallocated
            break

    new_distribution = [(synth, weight) for synth, weight in kept]
    total = sum(weight for _, weight in new_distribution)
    if not math.isclose(total, 1.0, abs_tol=1e-9):
        raise ValueError(
            f"apply_backfill: tổng trọng số sau backfill phải = 1.0 (nhận {total})"
        )

    report = [
        {
            "synthesizer_name": a.synthesizer_name,
            "num_clusters": a.num_clusters,
            "reallocated_weight": reallocated_weight_by_name[a.synthesizer_name],
        }
        for a in availability if not a.available
    ]
    return new_distribution, report


def multi_hop_availability(kg, distribution) -> list[MultiHopAvailability]:
    """Báo cáo số cluster mỗi multi-hop synthesizer tìm được trên KG.

    Dùng để cảnh báo khi KG không sinh được cluster nào (multi-hop = 0 câu hỏi).
    Traversal thuần đồ thị, offline.
    """
    reports: list[MultiHopAvailability] = []
    for synth, _weight in distribution:
        if isinstance(synth, (MultiHopAbstractQuerySynthesizer, MultiHopSpecificQuerySynthesizer)):
            clusters = synth.get_node_clusters(kg)
            reports.append(MultiHopAvailability(synth.name, len(clusters), len(clusters) > 0))
    return reports
