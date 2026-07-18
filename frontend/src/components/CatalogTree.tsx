import type { CatalogNode } from "../api/client";

/** Render đệ quy cây entities (catalog lean): facet gốc đậm, mục con thụt lề. */
function TreeNodes({ nodes, depth = 0 }: { nodes: CatalogNode[]; depth?: number }) {
  return (
    <ul className={depth === 0 ? "space-y-2" : "mt-1 space-y-1 border-l pl-3"}>
      {nodes.map((n, i) => (
        <li key={i}>
          <span
            className={
              depth === 0 ? "text-sm font-semibold text-accent" : "text-sm text-muted"
            }
          >
            {n.name}
          </span>
          {n.children.length > 0 && <TreeNodes nodes={n.children} depth={depth + 1} />}
        </li>
      ))}
    </ul>
  );
}

export default function CatalogTree({ nodes }: { nodes: CatalogNode[] }) {
  return <TreeNodes nodes={nodes} />;
}
