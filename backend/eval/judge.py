"""Judge kit cho ragas: judge LLM (FPT), embeddings, 5 metric của spec, RunConfig.

QUAN TRỌNG (FR-10): judge_llm/embeddings LUÔN được truyền tường minh cho evaluate() —
không bao giờ để ragas rơi vào fallback ngầm OpenAI/gpt-4o-mini mặc định.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.services.llm_client import make_openai_client
from ragas import RunConfig
from ragas.llms import llm_factory
from ragas.embeddings import OpenAIEmbeddings
from ragas.metrics import (
    Faithfulness,
    FactualCorrectness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
    ResponseRelevancy,
)


def judge_model_id() -> str:
    """EVAL_JUDGE_MODEL nếu đặt, ngược lại fallback FPT_CHAT_MODEL (FR-10)."""
    return settings.eval_judge_model or settings.fpt_chat_model


@dataclass
class JudgeBundle:
    llm: object          # BaseRagasLLM — judge FPT, KHÔNG bao giờ None
    embeddings: object   # ragas OpenAIEmbeddings trỏ FPT
    metrics: list        # đúng 5 metric của spec, đã gắn llm/embeddings
    run_config: RunConfig


def _build_judge_llm():
    """MỘT điểm duy nhất quyết định mode structured-output.

    Kết luận spike T04 (backend/eval/spikes/DECISION-structured-output.md):
    model FPT_CHAT_MODEL (GLM-5.2) là model reasoning — llm_factory mặc định trả về
    content rỗng (thinking ăn hết output). Bắt buộc tắt thinking qua extra_body
    (chat_template_kwargs.enable_thinking=False) — xác nhận cả 2 tầng test (structured
    generate + metric Faithfulness thật) đều pass với cấu hình này.

    Không dùng mode=instructor.Mode.MD_JSON (probe B): lỗi TypeError trên ragas 0.4.3
    (`handle_response_model() got multiple values for keyword argument 'mode'`).
    Không dùng LangchainLLMWrapper (probe C, legacy): hoạt động nhưng bị deprecation-wrap
    trên 0.4.x — chỉ giữ lại làm phương án dự phòng nếu A2 hỏng ở version ragas sau này:
        from langchain_openai import ChatOpenAI
        from ragas.llms import LangchainLLMWrapper
        LangchainLLMWrapper(ChatOpenAI(model=judge_model_id(), base_url=settings.fpt_base_url,
                                        api_key=settings.fpt_api_key))
    """
    return llm_factory(
        judge_model_id(),
        client=make_openai_client(),
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def _build_embeddings():
    return OpenAIEmbeddings(client=make_openai_client(), model=settings.fpt_embed_model)


def build_judge() -> JudgeBundle:
    """Trả về JudgeBundle đầy đủ cho T14: gọi evaluate(dataset, metrics=b.metrics,
    llm=b.llm, embeddings=b.embeddings, run_config=b.run_config, raise_exceptions=False) —
    llm/embeddings tường minh ở CẢ construction metric lẫn evaluate(), triệt tiêu fallback
    ngầm gpt-4o-mini của ragas khi llm=None.
    """
    llm = _build_judge_llm()
    embeddings = _build_embeddings()
    metrics = [
        Faithfulness(llm=llm),
        ResponseRelevancy(llm=llm, embeddings=embeddings),
        LLMContextPrecisionWithReference(llm=llm),
        LLMContextRecall(llm=llm),
        FactualCorrectness(llm=llm),
    ]
    run_config = RunConfig(
        timeout=settings.llm_timeout,          # 120.0 mặc định (config.py)
        max_workers=settings.eval_max_workers,  # EVAL_MAX_WORKERS, mặc định 4 (T03)
        max_retries=settings.llm_max_retries,   # NFR-3 retry/backoff
    )
    return JudgeBundle(llm=llm, embeddings=embeddings, metrics=metrics, run_config=run_config)
