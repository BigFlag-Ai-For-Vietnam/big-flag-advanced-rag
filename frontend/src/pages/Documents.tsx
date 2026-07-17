import { useEffect, useState } from "react";
import {
  deleteDocument, getDocument, listDocuments, reprocessDocument,
  type DocumentDetail, type DocumentSummary,
} from "../api/client";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try { setDocs(await listDocuments()); } finally { setLoading(false); }
  };

  useEffect(() => {
    refresh();
    const t = window.setInterval(refresh, 4000); // auto-refresh trạng thái pipeline
    return () => window.clearInterval(t);
  }, []);

  const onView = async (id: string) => setDetail(await getDocument(id));
  const onDelete = async (id: string) => {
    if (!confirm("Xoá document này (kèm pages/chunks/vectors)?")) return;
    await deleteDocument(id);
    if (detail?.id === id) setDetail(null);
    refresh();
  };
  const onReprocess = async (id: string) => { await reprocessDocument(id); refresh(); };

  return (
    <div>
      <h2>Documents {loading && <span className="muted">(đang tải...)</span>}</h2>
      <div className="card">
        <table>
          <thead>
            <tr><th>Title</th><th>Status</th><th>Pages</th><th>Chunks</th><th></th></tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>{d.title}</td>
                <td><span className={`badge ${d.status}`}>{d.status}</span></td>
                <td>{d.page_count ?? "-"}</td>
                <td>{d.chunk_count}</td>
                <td style={{ display: "flex", gap: 6 }}>
                  <button onClick={() => onView(d.id)}>Xem</button>
                  <button className="secondary" onClick={() => onReprocess(d.id)}>Reprocess</button>
                  <button className="danger" onClick={() => onDelete(d.id)}>Xoá</button>
                </td>
              </tr>
            ))}
            {docs.length === 0 && <tr><td colSpan={5} className="muted">Chưa có document nào.</td></tr>}
          </tbody>
        </table>
      </div>

      {detail && (
        <div className="card">
          <h3>{detail.title}</h3>
          {detail.error_message && <pre style={{ color: "#991b1b" }}>{detail.error_message}</pre>}

          <h4>Pages ({detail.pages.length}) — parsed_text</h4>
          {detail.pages.map((p) => (
            <details key={p.id}>
              <summary>Trang {p.page_number}</summary>
              <pre>{p.parsed_text || "(trống)"}</pre>
            </details>
          ))}

          <h4>Chunks ({detail.chunks.length}) — final_content</h4>
          {detail.chunks.map((c) => (
            <details key={c.id}>
              <summary>Chunk #{c.chunk_index} ({c.token_count} tokens)</summary>
              <div className="muted">Câu định vị: {c.contextual_prefix || "(none)"}</div>
              <pre>{c.final_content}</pre>
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
