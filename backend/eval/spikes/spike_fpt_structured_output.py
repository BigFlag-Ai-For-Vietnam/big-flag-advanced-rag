"""Spike (LIVE): FPT chat model có chạy được structured output của ragas 0.4 không?

Chạy tay, không bao giờ được import bởi test/app:
    cd backend && python eval/spikes/spike_fpt_structured_output.py
"""
from __future__ import annotations

import asyncio
import traceback

import instructor
import openai
from pydantic import BaseModel

from app.config import settings  # cwd=backend nên import được


class ProbeAnswer(BaseModel):
    # Đủ lồng nhau (list + float) để lộ lỗi parse JSON thô sơ
    verdict: str
    reasons: list[str]
    confidence: float


PROBE_PROMPT = (
    "Câu sau có nói về phí thẻ tín dụng không: "
    "'Phí thường niên của thẻ là 500.000 VND'? "
    "Trả lời verdict yes/no, liệt kê lý do, độ tin cậy 0-1."
)


def _raw_client() -> openai.OpenAI:
    # Mirror llm_client._client() — spike-only exception to the LLM boundary
    return openai.OpenAI(
        api_key=settings.fpt_api_key,
        base_url=settings.fpt_base_url,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
    )


def probe_a_llm_factory():
    """Modern path: ragas llm_factory, instructor default mode."""
    from ragas.llms import llm_factory
    llm = llm_factory(settings.fpt_chat_model, client=_raw_client())
    return llm, llm.generate(PROBE_PROMPT, ProbeAnswer)


def probe_a2_llm_factory_no_thinking():
    """GLM-thinking variant: llm_factory + extra_body tắt reasoning (chat_template_kwargs.enable_thinking=False).

    settings.fpt_chat_model là model reasoning (GLM-5.x) — mặc định "nghĩ" trước khi trả lời,
    content rỗng nếu max_tokens thấp (xem app/config.py:22, llm_client._thinking_extra).
    llm_factory's **kwargs (temperature/max_tokens/extra_body/...) truyền thẳng xuống
    client.chat.completions.create(...).
    """
    from ragas.llms import llm_factory
    llm = llm_factory(
        settings.fpt_chat_model,
        client=_raw_client(),
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    return llm, llm.generate(PROBE_PROMPT, ProbeAnswer)


def probe_b_md_json():
    """Escape hatch: instructor.Mode.MD_JSON (provider từ chối response_format/tools)."""
    from ragas.llms import llm_factory
    llm = llm_factory(
        settings.fpt_chat_model, client=_raw_client(), mode=instructor.Mode.MD_JSON
    )
    return llm, llm.generate(PROBE_PROMPT, ProbeAnswer)


def probe_c_legacy():
    """Last resort: LangchainLLMWrapper(ChatOpenAI) — deprecation-wrapped trên 0.4.x."""
    from langchain_openai import ChatOpenAI
    from ragas.llms import LangchainLLMWrapper
    return LangchainLLMWrapper(ChatOpenAI(
        model=settings.fpt_chat_model,
        api_key=settings.fpt_api_key,
        base_url=settings.fpt_base_url,
        timeout=settings.llm_timeout,
        max_retries=settings.llm_max_retries,
        # GLM reasoning: nếu content rỗng, thử biến thể tắt thinking:
        # extra_body={"chat_template_kwargs": {"enable_thinking": False}}
    ))


def probe_metric(llm) -> float:
    """Tầng 2: metric thật — đúng cách T05/FR-10 sẽ dùng judge."""
    from ragas import SingleTurnSample
    from ragas.metrics import Faithfulness  # DeprecationWarning trên 0.4.x là bình thường
    sample = SingleTurnSample(
        user_input="Phí thường niên là bao nhiêu?",
        response="Phí thường niên là 500.000 VND.",
        retrieved_contexts=["Phí thường niên của thẻ là 500.000 VND mỗi năm."],
    )
    return asyncio.run(Faithfulness(llm=llm).single_turn_ascore(sample))


def _run_probe(name: str, factory_fn, has_layer1: bool):
    print(f"\n{'=' * 60}\nPROBE {name}\n{'=' * 60}")
    llm = None
    layer1_ok = not has_layer1  # C skips layer 1
    layer2_ok = False
    try:
        if has_layer1:
            llm, result = factory_fn()
            print(f"[layer 1] generate() -> {result!r}")
            layer1_ok = isinstance(result, ProbeAnswer)
        else:
            llm = factory_fn()
            print("[layer 1] skipped (wrapper only used via metrics)")
    except Exception as exc:  # noqa: BLE001
        print(f"[layer 1] FAILED: {exc}")
        traceback.print_exc()
        return llm, False, False

    try:
        score = probe_metric(llm)
        print(f"[layer 2] Faithfulness score -> {score!r}")
        layer2_ok = isinstance(score, float) and score == score  # not NaN
    except Exception as exc:  # noqa: BLE001
        print(f"[layer 2] FAILED: {exc}")
        traceback.print_exc()

    return llm, layer1_ok, layer2_ok


if __name__ == "__main__":
    print(f"FPT_CHAT_MODEL={settings.fpt_chat_model!r}  FPT_BASE_URL={settings.fpt_base_url!r}")

    _, a1, a2 = _run_probe("A: llm_factory default", probe_a_llm_factory, has_layer1=True)
    if a1 and a2:
        print("\n>>> PROBE A PASSED BOTH LAYERS — stopping ladder.")
        raise SystemExit(0)

    # GLM-thinking variant: A thất bại với content rỗng -> thử tắt thinking qua extra_body.
    _, a2_1, a2_2 = _run_probe(
        "A2: llm_factory + disable-thinking (GLM variant)",
        probe_a2_llm_factory_no_thinking, has_layer1=True,
    )
    if a2_1 and a2_2:
        print("\n>>> PROBE A2 PASSED BOTH LAYERS — stopping ladder.")
        raise SystemExit(0)

    _, b1, b2 = _run_probe("B: llm_factory MD_JSON", probe_b_md_json, has_layer1=True)
    if b1 and b2:
        print("\n>>> PROBE B PASSED BOTH LAYERS — stopping ladder.")
        raise SystemExit(0)

    _, c1, c2 = _run_probe("C: LangchainLLMWrapper (legacy)", probe_c_legacy, has_layer1=False)
    if c2:
        print("\n>>> PROBE C PASSED (layer 2) — stopping ladder.")
        raise SystemExit(0)

    print("\n>>> NO PROBE PASSED — ESCALATE (M1 gate). Do not start T05.")
    raise SystemExit(1)
