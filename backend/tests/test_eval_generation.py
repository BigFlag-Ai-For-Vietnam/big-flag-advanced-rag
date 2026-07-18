"""Test query_distribution tường minh (FR-3) — offline, LLM là stub object()."""
import pytest

pytest.importorskip("ragas")

from ragas.testset.synthesizers import (
    MultiHopAbstractQuerySynthesizer,
    MultiHopSpecificQuerySynthesizer,
    SingleHopSpecificQuerySynthesizer,
)

from eval.distribution import (
    DistributionWeights,
    MultiHopAvailability,
    apply_backfill,
    build_query_distribution,
)


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


def test_multihop_shortfall_backfills_trivial():
    dist = build_query_distribution(llm=object())
    availability = [
        MultiHopAvailability("multi_hop_abstract_query_synthesizer", 0, False),
        MultiHopAvailability("multi_hop_specific_query_synthesizer", 0, False),
    ]

    new_dist, report = apply_backfill(dist, availability)

    assert len(new_dist) == 1
    synth, weight = new_dist[0]
    assert isinstance(synth, SingleHopSpecificQuerySynthesizer)
    assert weight == pytest.approx(1.0)

    reported_names = {row["synthesizer_name"] for row in report}
    assert reported_names == {
        "multi_hop_abstract_query_synthesizer",
        "multi_hop_specific_query_synthesizer",
    }
    for row in report:
        assert row["num_clusters"] == 0
        assert row["reallocated_weight"] == pytest.approx(0.25)
