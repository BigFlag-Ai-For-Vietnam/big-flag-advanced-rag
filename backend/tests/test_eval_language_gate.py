"""Test cổng kiểm tra ngôn ngữ tiếng Việt (FR-5, NFR-5) — offline, thuần stdlib."""
from eval.language_gate import GATE_REASON, apply_language_gate, enforce_quality


def test_language_gate_filters_non_vietnamese():
    samples = [
        {"user_input": "Phí thường niên là bao nhiêu?", "reference": "Phí thường niên là 500.000đ."},
        {"user_input": "What is the annual fee?", "reference": "Phí thường niên là 500.000đ."},
    ]
    result = apply_language_gate(samples)

    assert len(result.retained) == 1
    assert result.retained[0]["user_input"] == "Phí thường niên là bao nhiêu?"
    assert len(result.excluded) == 1
    assert result.excluded[0]["reason"] == GATE_REASON
    assert "user_input" in result.excluded[0]["failed_fields"]


def test_quality_threshold_fails_run():
    vn_sample = {"user_input": "Phí thường niên là bao nhiêu?", "reference": "Phí thường niên là 500.000đ."}
    en_sample = {"user_input": "What is the fee?", "reference": "The fee is 500,000 VND."}
    samples = [vn_sample] * 7 + [en_sample] * 3

    result = apply_language_gate(samples)

    assert result.exclusion_rate == 0.3
    assert result.failed_quality is True
    assert enforce_quality(result) != 0
