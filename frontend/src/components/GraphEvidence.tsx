import { Network } from "lucide-react";
import type { GraphFact } from "../api/client";

export default function GraphEvidence({ facts }: { facts: GraphFact[] }) {
  if (!facts.length) return null;
  return (
    <div>
      <p className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-fg">
        <Network className="size-4 text-accent" /> Tri thức đồ thị ({facts.length})
      </p>
      <div className="space-y-2">
        {facts.map((fact, index) => (
          <details key={fact.fact_id || index} className="rounded-xl border bg-surface shadow-sm">
            <summary className="cursor-pointer px-3.5 py-2.5 text-sm">
              <span className="font-medium text-fg">{fact.source_entity}</span>
              <span className="mx-2 rounded bg-accent-soft px-1.5 py-0.5 font-mono text-[11px] text-accent">
                {fact.relation}
              </span>
              <span className="font-medium text-fg">{fact.target_entity}</span>
            </summary>
            <div className="space-y-2 border-t px-3.5 py-3 text-xs leading-relaxed text-muted">
              {fact.description && <p>{fact.description}</p>}
              {Object.keys(fact.properties ?? {}).length > 0 && (
                <pre className="overflow-auto rounded-lg bg-surface-2 p-2 font-mono text-[11px]">
                  {JSON.stringify(fact.properties, null, 2)}
                </pre>
              )}
              <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-faint">
                {fact.source_document_title && <span>nguồn: {fact.source_document_title}</span>}
                {fact.strategy && <span>strategy: {fact.strategy}</span>}
                <span>score: {fact.score.toFixed(2)}</span>
              </div>
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
