"""Test query_distribution tường minh (FR-3) — offline, LLM là stub object()."""
import pytest

pytest.importorskip("ragas")

from ragas.testset.synthesizers import (
    MultiHopAbstractQuerySynthesizer,
    MultiHopSpecificQuerySynthesizer,
    SingleHopSpecificQuerySynthesizer,
)

from eval.distribution import DistributionWeights, build_query_distribution


def test_explicit_query_distribution():
    dist = build_query_distribution(llm=object())
    assert [type(s) for s, _ in dist] == [
        SingleHopSpecificQuerySynthesizer,
        MultiHopAbstractQuerySynthesizer,
        MultiHopSpecificQuerySynthesizer,
    ]
    assert [w for _, w in dist] == [0.5, 0.25, 0.25]


def test_invalid_weights_rejected():
    with pytest.raises(ValueError):
        build_query_distribution(
            llm=object(),
            weights=DistributionWeights(0.5, 0.25, 0.1),
        )
