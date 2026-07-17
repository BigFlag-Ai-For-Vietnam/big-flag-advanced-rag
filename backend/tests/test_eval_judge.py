"""Test judge factory (FR-10) — offline, không có network I/O thực sự."""
import pytest

pytest.importorskip("ragas")

from openai import AsyncOpenAI, OpenAI

from app.config import settings
from app.services.llm_client import LLMError, make_openai_client


def test_make_openai_client_defaults(monkeypatch):
    monkeypatch.setattr(settings, "fpt_api_key", "test-key")
    monkeypatch.setattr(settings, "fpt_base_url", "https://fpt.example/v1")
    client = make_openai_client()
    assert isinstance(client, OpenAI)
    assert str(client.base_url).startswith("https://fpt.example/v1")

    async_client = make_openai_client(async_client=True)
    assert isinstance(async_client, AsyncOpenAI)


def test_make_openai_client_requires_api_key(monkeypatch):
    monkeypatch.setattr(settings, "fpt_api_key", "")
    with pytest.raises(LLMError):
        make_openai_client()


def test_judge_defaults_and_override(monkeypatch):
    monkeypatch.setattr(settings, "fpt_api_key", "test-key")
    monkeypatch.setattr(settings, "fpt_base_url", "https://fpt.example/v1")
    monkeypatch.setattr(settings, "fpt_chat_model", "m1")
    monkeypatch.setattr(settings, "fpt_embed_model", "embed1")
    monkeypatch.setattr(settings, "eval_judge_model", "")
    monkeypatch.setattr(settings, "eval_max_workers", 2)

    from eval import judge

    assert judge.judge_model_id() == "m1"
    bundle = judge.build_judge()
    assert bundle.llm.model == "m1"
    assert str(bundle.llm.client.base_url).startswith("https://fpt.example/v1")
    assert bundle.run_config.max_workers == 2

    monkeypatch.setattr(settings, "eval_judge_model", "judge-x")
    assert judge.judge_model_id() == "judge-x"
    bundle2 = judge.build_judge()
    assert bundle2.llm.model == "judge-x"


def test_metric_set(monkeypatch):
    monkeypatch.setattr(settings, "fpt_api_key", "test-key")
    monkeypatch.setattr(settings, "fpt_base_url", "https://fpt.example/v1")
    monkeypatch.setattr(settings, "fpt_chat_model", "m1")
    monkeypatch.setattr(settings, "fpt_embed_model", "embed1")
    monkeypatch.setattr(settings, "eval_judge_model", "")

    from eval import judge
    from ragas.metrics import (
        Faithfulness,
        FactualCorrectness,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        ResponseRelevancy,
    )

    bundle = judge.build_judge()
    assert [type(m) for m in bundle.metrics] == [
        Faithfulness,
        ResponseRelevancy,
        LLMContextPrecisionWithReference,
        LLMContextRecall,
        FactualCorrectness,
    ]
    for m in bundle.metrics:
        assert m.llm is not None
    response_relevancy = bundle.metrics[1]
    assert response_relevancy.embeddings is not None
