"""Query TOÀN BỘ graph hiện có trong Neo4j (mọi node + mọi relation) và xuất ra 1 file
HTML tự chứa (pyvis, không cần internet để mở) để xem trực quan.

Chạy (từ backend/, cần Neo4j đang chạy):
    NEO4J_URI=bolt://localhost:7687 NEO4J_USERNAME=neo4j NEO4J_PASSWORD=<pass> \
        python -m poc.kg_ontology.export_neo4j_viz
"""
from __future__ import annotations

import os
import sys

_BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import networkx as nx  # noqa: E402
from neo4j import GraphDatabase  # noqa: E402
from pyvis.network import Network  # noqa: E402

from poc.kg_ontology.ontology.loader import ENTITY_TYPES  # noqa: E402

_OUT_PATH = os.path.join(os.path.dirname(__file__), "_kg_storage", "compliance_graph.html")

_PALETTE = [
    "#4C6EF5", "#12B886", "#F59F00", "#E64980", "#7048E8", "#15AABF", "#82C91E", "#FA5252",
]
_TYPE_COLOR = {name: _PALETTE[i % len(_PALETTE)] for i, name in enumerate(ENTITY_TYPES)}
_UNKNOWN_COLOR = "#ADB5BD"


def _fetch_graph() -> nx.DiGraph:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USERNAME", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        raise SystemExit("NEO4J_PASSWORD chưa set.")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    G = nx.DiGraph()
    try:
        with driver.session() as session:
            for rec in session.run("MATCH (n) RETURN n"):
                node = rec["n"]
                node_id = node.get("entity_id") or node.element_id
                G.add_node(
                    node_id,
                    entity_type=node.get("entity_type"),
                    description=node.get("description") or "",
                )

            for rec in session.run("MATCH (a)-[r]->(b) RETURN a, r, b"):
                a, r, b = rec["a"], rec["r"], rec["b"]
                src = a.get("entity_id") or a.element_id
                tgt = b.get("entity_id") or b.element_id
                if src not in G:
                    G.add_node(src, entity_type=a.get("entity_type"), description=a.get("description") or "")
                if tgt not in G:
                    G.add_node(tgt, entity_type=b.get("entity_type"), description=b.get("description") or "")
                G.add_edge(
                    src, tgt,
                    ontology_relation=r.get("ontology_relation") or "",
                    description=r.get("description") or "",
                    weight=r.get("weight", 1.0),
                )
    finally:
        driver.close()
    return G


def _export_html(G: nx.DiGraph, out_path: str) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    net = Network(
        height="900px", width="100%", directed=True, cdn_resources="in_line",
        heading=f"Compliance KG ({G.number_of_nodes()} node, {G.number_of_edges()} edge)",
    )
    net.barnes_hut(spring_length=200, gravity=-4000)

    for node_id, data in G.nodes(data=True):
        etype = data.get("entity_type")
        desc = (data.get("description") or "").strip()
        tooltip = f"{node_id}\n[{etype}]\n{desc[:400]}"
        net.add_node(
            node_id,
            label=node_id if len(node_id) <= 32 else node_id[:30] + "…",
            title=tooltip,
            color=_TYPE_COLOR.get(etype, _UNKNOWN_COLOR),
        )

    for u, v, data in G.edges(data=True):
        label = data.get("ontology_relation") or ""
        tooltip = (data.get("description") or "").strip()[:400]
        net.add_edge(u, v, label=label, title=tooltip, width=max(1.0, float(data.get("weight", 1) or 1)), arrows="to")

    net.write_html(out_path, notebook=False, open_browser=False)


def main() -> None:
    print("Đọc toàn bộ graph từ Neo4j...")
    G = _fetch_graph()
    print(f"  -> {G.number_of_nodes()} node, {G.number_of_edges()} edge")

    isolated = [n for n in G.nodes() if G.degree(n) == 0]
    if isolated:
        print(f"  ({len(isolated)} node mồ côi — không có edge nào, vẫn hiển thị trong HTML)")

    _export_html(G, _OUT_PATH)
    print(f"\nĐã ghi {_OUT_PATH}")
    print("Mở file này bằng trình duyệt để xem toàn bộ graph.")


if __name__ == "__main__":
    main()
