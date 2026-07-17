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


def build_query_distribution(llm, weights: DistributionWeights | None = None):
    """Trả về query_distribution tường minh cho ragas TestsetGenerator.

    KHÔNG dùng default_query_distribution (nó lọc bỏ synthesizer thầm lặng và có thể raise).
    """
    weights = weights or DistributionWeights()  # __post_init__ đã validate
    return [
        (SingleHopSpecificQuerySynthesizer(llm=llm), weights.single_hop_specific),
        (MultiHopAbstractQuerySynthesizer(llm=llm), weights.multi_hop_abstract),
        (MultiHopSpecificQuerySynthesizer(llm=llm), weights.multi_hop_specific),
    ]


@dataclass
class MultiHopAvailability:
    synthesizer_name: str
    num_clusters: int
    available: bool


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
