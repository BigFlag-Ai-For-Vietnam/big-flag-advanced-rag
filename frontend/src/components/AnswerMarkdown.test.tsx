import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import AnswerMarkdown, { linkCitations } from "./AnswerMarkdown";

const citations = [{
  document_id: "doc-1",
  title: "Quy chế An toàn thông tin",
  chunk_index: 4,
  score: 0.91,
  final_content: "Mật khẩu tối thiểu 12 ký tự.",
}];

describe("AnswerMarkdown", () => {
  it("renders emphasis and turns numeric citations into document anchors", () => {
    const html = renderToStaticMarkup(
      <AnswerMarkdown
        content="Mật khẩu **tối thiểu 12 ký tự** [1]."
        citations={citations}
        anchorPrefix="advanced-citation"
      />,
    );
    expect(html).toContain("<strong");
    expect(html).toContain("tối thiểu 12 ký tự</strong>");
    expect(html).toContain('href="#advanced-citation-1"');
    expect(html).toContain("Quy chế An toàn thông tin");
  });

  it("does not rewrite an existing markdown link", () => {
    expect(linkCitations("Xem [1](https://example.com)")).toBe("Xem [1](https://example.com)");
  });
});
