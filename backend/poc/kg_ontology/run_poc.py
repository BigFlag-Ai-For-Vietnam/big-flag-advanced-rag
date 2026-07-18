"""PoC entrypoint: build 3 knowledge graph để so sánh trực quan.

  1. baseline           — LightRAG mặc định (11 entity type generic: Person/Organization/
                           Location/Event/Concept/...), KHÔNG có ontology, KHÔNG post-process.
  2. ontology_raw        — LightRAG với `entity_types_guidance` constrain theo ontology.py
                           (native lever của LightRAG), KHÔNG post-process.
  3. ontology_filtered   — (2) + canonicalize_graph + apply_ontology_filter (noise_filter.py)
                           = pipeline đề xuất, tương ứng bước "Validation & Filtering" mà
                           arXiv:2507.06107 mô tả.

Input dùng chung cho cả 3 (sample_input.SAMPLE_TEXT) để so sánh công bằng.

Chạy (từ thư mục backend/, cần FPT_API_KEY + FPT_CHAT_MODEL + FPT_EMBED_MODEL trong .env):

    pip install -r requirements-poc.txt
    python -m poc.kg_ontology.run_poc

Output: backend/poc/kg_ontology/_poc_storage/out/{baseline,ontology_raw,ontology_filtered}.html
(mở trực tiếp bằng trình duyệt) + metrics.json (số liệu before/after + danh sách node/edge
bị loại, để soi bằng mắt là ontology filter có hợp lý không).

KHÔNG wire vào app/services/pipeline.py — script độc lập, không đụng luồng ingest thật.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys

# Cho phép chạy trực tiếp `python poc/kg_ontology/run_poc.py` (không chỉ `-m`) bằng cách
# tự thêm backend/ vào sys.path để import được cả `app.*` lẫn `poc.*`.
_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import networkx as nx  # noqa: E402
from lightrag import LightRAG  # noqa: E402
from lightrag.kg.shared_storage import initialize_pipeline_status  # noqa: E402

from app.config import settings  # noqa: E402
from poc.kg_ontology.llm_adapter import build_embedding_func, llm_model_func  # noqa: E402
from poc.kg_ontology.noise_filter import apply_ontology_filter, canonicalize_graph  # noqa: E402
from poc.kg_ontology.ontology_v1_bieuphi import build_entity_types_guidance  # noqa: E402
from poc.kg_ontology.sample_input import SAMPLE_TEXT  # noqa: E402
from poc.kg_ontology.visualize import export_html  # noqa: E402

_STORAGE_ROOT = os.path.join(os.path.dirname(__file__), "_poc_storage")


async def _build_and_insert(working_dir: str, *, ontology_guided: bool) -> nx.Graph:
    if os.path.isdir(working_dir):
        shutil.rmtree(working_dir)
    os.makedirs(working_dir, exist_ok=True)

    addon_params = {"language": "Vietnamese"}
    if ontology_guided:
        addon_params["entity_types_guidance"] = build_entity_types_guidance()

    rag = LightRAG(
        working_dir=working_dir,
        llm_model_func=llm_model_func,
        embedding_func=build_embedding_func(),
        addon_params=addon_params,
    )
    await rag.initialize_storages()
    await initialize_pipeline_status()
    await rag.ainsert(SAMPLE_TEXT)
    await rag.finalize_storages()

    graphml_path = os.path.join(working_dir, "graph_chunk_entity_relation.graphml")
    return nx.read_graphml(graphml_path)


def _graph_summary(G: nx.Graph) -> dict:
    types = [d.get("entity_type") for _, d in G.nodes(data=True)]
    name_lens = [len(n) for n in G.nodes()]
    return {
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "distinct_entity_types": len(set(t for t in types if t)),
        "entity_type_breakdown": {t: types.count(t) for t in sorted(set(types), key=str)},
        "avg_node_name_len": round(sum(name_lens) / len(name_lens), 1) if name_lens else 0,
        "max_node_name_len": max(name_lens) if name_lens else 0,
    }


async def main() -> None:
    if not settings.fpt_api_key:
        raise SystemExit(
            "FPT_API_KEY chưa cấu hình (.env) — PoC cần gọi thật FPT chat + embed model."
        )

    print(f"[1/3] Build baseline graph (LightRAG mặc định, không ontology)...")
    baseline = await _build_and_insert(os.path.join(_STORAGE_ROOT, "baseline"), ontology_guided=False)

    print(f"[2/3] Build ontology-guided graph (entity_types_guidance constrain)...")
    ontology_raw = await _build_and_insert(os.path.join(_STORAGE_ROOT, "ontology"), ontology_guided=True)

    print("[3/3] Áp post-processing (canonicalize + ontology relation filter)...")
    canonical, n_merged = canonicalize_graph(ontology_raw)
    ontology_filtered, stats = apply_ontology_filter(canonical)
    stats.nodes_merged = n_merged

    out_dir = os.path.join(_STORAGE_ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)
    export_html(baseline, os.path.join(out_dir, "baseline.html"), "Baseline (LightRAG mặc định)")
    export_html(ontology_raw, os.path.join(out_dir, "ontology_raw.html"), "Ontology-guided (chưa filter)")
    export_html(
        ontology_filtered,
        os.path.join(out_dir, "ontology_filtered.html"),
        "Ontology-guided + post-filter (đề xuất)",
    )

    summary = {
        "baseline": _graph_summary(baseline),
        "ontology_raw": _graph_summary(ontology_raw),
        "ontology_filtered": _graph_summary(ontology_filtered),
        "filter_stats": stats.__dict__,
    }
    with open(os.path.join(out_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n=== So sánh ===")
    for name in ("baseline", "ontology_raw", "ontology_filtered"):
        s = summary[name]
        print(f"{name:20s} nodes={s['nodes']:3d}  edges={s['edges']:3d}  distinct_types={s['distinct_entity_types']:2d}  avg_name_len={s['avg_node_name_len']}")
    print(
        f"\nfilter: merged={stats.nodes_merged} dropped_bad_type={stats.nodes_dropped_bad_type} "
        f"dropped_unclassified_relation={stats.edges_dropped_unclassified_relation} "
        f"dropped_invalid_triple={stats.edges_dropped_invalid_triple} dropped_orphan={stats.nodes_dropped_orphan}"
    )
    print(f"\nHTML: {out_dir}/{{baseline,ontology_raw,ontology_filtered}}.html")
    print(f"Metrics: {out_dir}/metrics.json")


if __name__ == "__main__":
    asyncio.run(main())
