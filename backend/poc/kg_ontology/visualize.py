"""Export networkx graph -> file HTML tự chứa (pyvis, cdn_resources='in_line') để mở
trực tiếp bằng trình duyệt và xem graph — không cần server, không cần internet, không
phụ thuộc thư mục `lib/` cạnh file."""
from __future__ import annotations

import networkx as nx
from pyvis.network import Network

from poc.kg_ontology.ontology_v1_bieuphi import ENTITY_TYPES

_PALETTE = [
    "#4C6EF5", "#12B886", "#F59F00", "#E64980", "#7048E8", "#15AABF", "#82C91E", "#FA5252",
]
_TYPE_COLOR = {name: _PALETTE[i % len(_PALETTE)] for i, name in enumerate(ENTITY_TYPES)}
_UNKNOWN_COLOR = "#ADB5BD"


def export_html(G: nx.Graph, out_path: str, title: str) -> None:
    net = Network(height="750px", width="100%", directed=False, cdn_resources="in_line", heading=title)
    net.barnes_hut(spring_length=180, gravity=-3000)

    for node_id, data in G.nodes(data=True):
        etype = data.get("entity_type")
        desc = (data.get("description") or "").strip()
        tooltip = f"{node_id}\n[{etype}]\n{desc[:300]}"
        net.add_node(
            node_id,
            label=node_id if len(node_id) <= 28 else node_id[:26] + "…",
            title=tooltip,
            color=_TYPE_COLOR.get(etype, _UNKNOWN_COLOR),
        )

    for u, v, data in G.edges(data=True):
        label = data.get("ontology_relation") or data.get("keywords") or ""
        tooltip = (data.get("description") or "").strip()[:300]
        net.add_edge(u, v, label=label, title=tooltip, width=max(1.0, float(data.get("weight", 1) or 1)))

    net.write_html(out_path, notebook=False, open_browser=False)
