import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Citation } from "../api/client";

export function linkCitations(markdown: string, anchorPrefix = "citation") {
  // LLM đang trả citation dạng [1]. Đổi marker chưa phải Markdown link thành
  // anchor; ReactMarkdown vẫn escape raw HTML theo mặc định.
  return markdown.replace(/(?<!\[)\[(\d+)\](?!\()/g, `[$1](#${anchorPrefix}-$1)`);
}

export default function AnswerMarkdown({ content, citations, anchorPrefix = "citation" }: {
  content: string;
  citations: Citation[];
  anchorPrefix?: string;
}) {
  return (
    <div className="text-[15px] leading-relaxed text-fg">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
          strong: ({ children }) => <strong className="font-bold text-fg">{children}</strong>,
          ul: ({ children }) => <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="mb-3 list-decimal space-y-1 pl-5">{children}</ol>,
          li: ({ children }) => <li className="pl-1">{children}</li>,
          h1: ({ children }) => <h1 className="mb-2 mt-4 text-xl font-bold first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 mt-4 text-lg font-bold first:mt-0">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-2 mt-3 font-bold first:mt-0">{children}</h3>,
          blockquote: ({ children }) => <blockquote className="mb-3 border-l-2 border-accent pl-3 text-muted">{children}</blockquote>,
          code: ({ children }) => <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[0.9em]">{children}</code>,
          a: ({ href, children }) => {
            const match = href?.match(new RegExp(`^#${anchorPrefix}-(\\d+)$`));
            if (!match) return <a href={href} className="text-accent underline underline-offset-2">{children}</a>;
            const number = Number(match[1]);
            const citation = citations[number - 1];
            return (
              <a
                href={href}
                title={citation ? `Nguồn ${number}: ${citation.title}` : `Nguồn ${number}`}
                className="mx-0.5 inline-flex translate-y-[-1px] items-center rounded bg-accent-soft px-1.5 py-0.5 font-mono text-xs font-bold text-accent no-underline hover:ring-1 hover:ring-accent/40"
              >
                [{children}]
              </a>
            );
          },
        }}
      >
        {linkCitations(content, anchorPrefix)}
      </ReactMarkdown>

      {citations.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-3 text-xs">
          <span className="font-semibold text-faint">Trích dẫn:</span>
          {citations.map((citation, index) => (
            <a
              key={`${citation.document_id}:${citation.chunk_index}:${index}`}
              href={`#${anchorPrefix}-${index + 1}`}
              title={citation.final_content}
              className="max-w-full truncate rounded-full border bg-surface-2 px-2.5 py-1 text-muted transition-colors hover:border-accent/40 hover:text-fg"
            >
              <span className="mr-1 font-mono font-bold text-accent">[{index + 1}]</span>
              {citation.title} · đoạn #{citation.chunk_index}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
