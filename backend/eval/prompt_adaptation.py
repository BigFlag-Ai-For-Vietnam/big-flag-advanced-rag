"""Thích ứng (adapt) prompt ragas sang tiếng Việt: 3 synthesizer (FR-3) + extractor
LLM-based trong transforms pre-chunked (SummaryExtractor, ThemesExtractor, NERExtractor,
CustomNodeFilter). Lưu xuống thư mục prompts, `generate` nạp lại — không adapt lại mỗi lần chạy.

Toàn bộ import ragas nằm TRONG hàm (NFR-1/NFR-2): module này import được dù chưa cài
requirements-eval.txt; chỉ các hàm bên dưới mới cần ragas lúc gọi.
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("eval.prompt_adaptation")

# Thư mục mặc định lưu prompt đã adapt — cạnh module này, không phụ thuộc cwd khi chạy CLI.
DEFAULT_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts" / "vi"

LANGUAGE = "vietnamese"


def _synthesizer_classes():
    from ragas.testset.synthesizers import (
        MultiHopAbstractQuerySynthesizer,
        MultiHopSpecificQuerySynthesizer,
        SingleHopSpecificQuerySynthesizer,
    )
    return (
        SingleHopSpecificQuerySynthesizer,
        MultiHopAbstractQuerySynthesizer,
        MultiHopSpecificQuerySynthesizer,
    )


def _llm_based_extractor_factories(llm, filter_nodes):
    """4 extractor/filter LLM-based dùng trong default_transforms_for_prechunked
    (xem ragas.testset.transforms.default_transforms_for_prechunked nguồn thực tế)."""
    from ragas.testset.transforms.extractors.llm_based import (
        NERExtractor,
        SummaryExtractor,
        ThemesExtractor,
    )
    from ragas.testset.transforms.filters import CustomNodeFilter

    return [
        SummaryExtractor(llm=llm, filter_nodes=filter_nodes),
        ThemesExtractor(llm=llm, filter_nodes=filter_nodes),
        NERExtractor(llm=llm, filter_nodes=filter_nodes),
        CustomNodeFilter(llm=llm, filter_nodes=filter_nodes),
    ]


async def adapt_and_save_all(llm, prompts_dir: Path = DEFAULT_PROMPTS_DIR) -> None:
    """Adapt prompt của 3 synthesizer + 4 extractor LLM-based sang tiếng Việt, lưu xuống
    prompts_dir (mỗi object một thư mục con theo .name). In instruction đầu tiên của mỗi
    prompt đã adapt để người review soát ngôn ngữ (ragas cảnh báo: chất lượng adapt phụ
    thuộc LLM, có thể lệch ngôn ngữ — cần con người kiểm tra)."""
    from ragas.testset.graph import NodeType

    def _filter_chunks(node):
        return node.type == NodeType.CHUNK

    objects = [cls(llm=llm) for cls in _synthesizer_classes()]
    objects += _llm_based_extractor_factories(llm, _filter_chunks)

    prompts_dir.mkdir(parents=True, exist_ok=True)
    for obj in objects:
        adapted = await obj.adapt_prompts(LANGUAGE, llm=llm)
        obj.set_prompts(**adapted)
        out_dir = prompts_dir / obj.name
        out_dir.mkdir(parents=True, exist_ok=True)
        obj.save_prompts(str(out_dir))
        for prompt_name, prompt in adapted.items():
            first_instruction = str(getattr(prompt, "instruction", prompt))[:200]
            logger.info("[adapt-prompts] %s/%s: %s", obj.name, prompt_name, first_instruction)
    logger.info("Đã adapt + lưu prompt tiếng Việt vào %s", prompts_dir)


def load_adapted_synthesizer(synth_cls, llm, prompts_dir: Path = DEFAULT_PROMPTS_DIR):
    """Nạp lại synthesizer đã adapt. Thiếu prompt đã lưu -> lỗi rõ ràng: chạy adapt-prompts trước."""
    synth = synth_cls(llm=llm)
    prompt_path = prompts_dir / synth.name
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Chưa có prompt tiếng Việt cho '{synth.name}' tại {prompt_path}. "
            "Chạy `python -m eval adapt-prompts` trước."
        )
    loaded = synth.load_prompts(str(prompt_path), language=LANGUAGE)
    synth.set_prompts(**loaded)
    return synth


def load_adapted_transforms(llm, embeddings, prompts_dir: Path = DEFAULT_PROMPTS_DIR):
    """Transforms cho KG build (T08): extractor LLM-based nạp prompt đã adapt nếu có,
    ngược lại dùng transform nhẹ chỉ-embedding (theo hướng dẫn ragas cho ngôn ngữ non-English)
    + cảnh báo. Relationship builder dựa-embedding giữ nguyên (trung lập ngôn ngữ)."""
    from ragas.testset.graph import NodeType
    from ragas.testset.transforms import Parallel
    from ragas.testset.transforms.extractors import EmbeddingExtractor
    from ragas.testset.transforms.relationship_builders import (
        CosineSimilarityBuilder,
        OverlapScoreBuilder,
    )

    def _filter_chunks(node):
        return node.type == NodeType.CHUNK

    llm_based = _llm_based_extractor_factories(llm, _filter_chunks)
    loaded_llm_based = []
    for extractor in llm_based:
        prompt_path = prompts_dir / extractor.name
        if prompt_path.exists():
            loaded = extractor.load_prompts(str(prompt_path), language=LANGUAGE)
            extractor.set_prompts(**loaded)
            loaded_llm_based.append(extractor)
        else:
            logger.warning(
                "Không có prompt tiếng Việt đã adapt cho '%s' — bỏ qua extractor này "
                "(chỉ dùng transform embedding-only, theo hướng dẫn ragas cho ngôn ngữ non-English). "
                "Chạy `python -m eval adapt-prompts` để bật lại.",
                extractor.name,
            )

    summary_emb_extractor = EmbeddingExtractor(
        embedding_model=embeddings,
        property_name="summary_embedding",
        embed_property_name="summary",
        filter_nodes=_filter_chunks,
    )
    cosine_sim_builder = CosineSimilarityBuilder(
        property_name="summary_embedding",
        new_property_name="summary_similarity",
        threshold=0.7,
        filter_nodes=_filter_chunks,
    )
    ner_overlap_sim = OverlapScoreBuilder(threshold=0.01, filter_nodes=_filter_chunks)

    transforms = list(loaded_llm_based)
    transforms.append(Parallel(summary_emb_extractor))
    transforms.append(Parallel(cosine_sim_builder, ner_overlap_sim))
    return transforms
