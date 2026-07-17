"""Test persona batches (FR-4) — offline, không cần ragas cài."""
from types import SimpleNamespace

import pytest

from eval.personas import PersonaError, load_personas, plan_persona_batches, stamp_persona_name


def _write_personas(tmp_path, personas):
    import json
    path = tmp_path / "personas.json"
    path.write_text(json.dumps(personas), encoding="utf-8")
    return path


def test_per_persona_batches_and_stamping(tmp_path):
    path = _write_personas(tmp_path, [
        {"name": "Khách hàng cá nhân", "role_description": "Người dùng phổ thông, chưa rành sản phẩm tín dụng."},
        {"name": "Chuyên viên tài chính", "role_description": "Hiểu biết sâu về sản phẩm, hỏi câu hỏi kỹ thuật."},
    ])
    personas = load_personas(path)
    assert len(personas) == 2

    batches = plan_persona_batches(personas, 10)
    assert [b.size for b in batches] == [5, 5]

    samples = [SimpleNamespace(persona_name=None) for _ in range(3)]
    stamp_persona_name(samples, "kh_ca_nhan")
    assert all(s.persona_name == "kh_ca_nhan" for s in samples)


def test_missing_personas_file_fails(tmp_path):
    with pytest.raises(PersonaError, match="personas.json"):
        load_personas(tmp_path / "nope.json")
