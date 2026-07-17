"""Persona ("user background"): load/validate personas.json, lập kế hoạch batch, gắn persona_name.

ragas KHÔNG lưu persona vào output sample (persona chỉ tồn tại trong lúc generate) —
module này tự chịu trách nhiệm gắn persona_name lên từng sample sau khi generate.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class PersonaError(RuntimeError):
    """Lỗi persona: thiếu personas.json hoặc nội dung không hợp lệ."""


@dataclass(frozen=True)
class PersonaSpec:
    name: str
    role_description: str  # tiếng Việt (user background)

    def to_ragas(self):
        # import trễ để test offline không cần cài ragas
        from ragas.testset.persona import Persona
        return Persona(name=self.name, role_description=self.role_description)


@dataclass(frozen=True)
class PersonaBatch:
    persona: PersonaSpec
    size: int


def load_personas(path: str | Path) -> list[PersonaSpec]:
    p = Path(path)
    if not p.exists():
        raise PersonaError(
            f"Không tìm thấy personas.json tại '{p}'. "
            "Bắt buộc cung cấp file personas.json (không tự sinh persona mặc định)."
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise PersonaError("personas.json phải là danh sách persona không rỗng.")
    personas: list[PersonaSpec] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict) or "name" not in item or "role_description" not in item:
            raise PersonaError(f"personas.json[{i}] thiếu 'name' hoặc 'role_description'.")
        personas.append(PersonaSpec(name=item["name"], role_description=item["role_description"]))
    return personas


def plan_persona_batches(personas: list[PersonaSpec], total_size: int) -> list[PersonaBatch]:
    n = len(personas)
    if n == 0:
        raise PersonaError("Không có persona nào để lập kế hoạch batch.")
    base, rem = divmod(total_size, n)  # chia đều, phần dư rải cho các persona đầu
    return [PersonaBatch(p, base + (1 if i < rem else 0)) for i, p in enumerate(personas)]


def stamp_persona_name(samples, persona_name: str):
    """Gán persona_name lên từng sample (ragas không lưu persona vào output)."""
    for s in samples:
        s.persona_name = persona_name
    return samples


def log_personas_artifact(path: str | Path) -> None:
    import mlflow
    mlflow.log_artifact(str(path))
