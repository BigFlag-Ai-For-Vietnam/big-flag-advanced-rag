import { useState } from "react";
import { API_BASE_URL, type Citation } from "../api/client";

export default function PlaygroundPage() {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async () => {
    if (!question.trim()) return;
    setBusy(true); setAnswer(""); setCitations([]); setError(null);
    try {
      // Dùng fetch để đọc SSE stream từ /api/playground/query.
      const resp = await fetch(`${API_BASE_URL}/api/playground/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: topK, stream: true }),
      });
      if (!resp.ok || !resp.body) {
        throw new Error(`HTTP ${resp.status}`);
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          const line = part.trim();
          if (!line.startsWith("data:")) continue;
          const data = line.slice(5).trim();
          if (data === "[DONE]") continue;
          try {
            const evt = JSON.parse(data);
            if (evt.type === "citations") setCitations(evt.citations);
            else if (evt.type === "token") setAnswer((prev) => prev + evt.content);
            else if (evt.type === "error") setError(evt.message);
          } catch { /* bỏ qua dòng không parse được */ }
        }
      }
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2>Playground — Hỏi đáp RAG</h2>
      <div className="card">
        <textarea
          style={{ width: "100%", minHeight: 80 }}
          placeholder="Nhập câu hỏi về tài liệu đã index..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 12 }}>
          <label>top_k:&nbsp;
            <input type="number" min={1} max={20} value={topK}
              onChange={(e) => setTopK(Number(e.target.value))} style={{ width: 60 }} />
          </label>
          <button onClick={ask} disabled={busy}>{busy ? "Đang hỏi..." : "Hỏi"}</button>
        </div>
      </div>

      {error && <div className="card"><pre style={{ color: "#991b1b" }}>{error}</pre></div>}

      {(answer || busy) && (
        <div className="card">
          <h3>Câu trả lời</h3>
          <pre>{answer || "..."}</pre>
        </div>
      )}

      {citations.length > 0 && (
        <div className="card">
          <h3>Nguồn ({citations.length})</h3>
          {citations.map((c, i) => (
            <details key={i}>
              <summary>[{i + 1}] {c.title} — đoạn #{c.chunk_index} (score {c.score.toFixed(3)})</summary>
              <pre>{c.final_content}</pre>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
