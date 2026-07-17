import { useEffect, useRef, useState } from "react";
import { getStatus, uploadDocument, type DocStatus } from "../api/client";

const TERMINAL: DocStatus[] = ["indexed", "failed"];

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [docId, setDocId] = useState<string | null>(null);
  const [status, setStatus] = useState<DocStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => () => { if (timer.current) window.clearInterval(timer.current); }, []);

  const poll = (id: string) => {
    if (timer.current) window.clearInterval(timer.current);
    timer.current = window.setInterval(async () => {
      try {
        const s = await getStatus(id);
        setStatus(s.status);
        setError(s.error_message);
        if (TERMINAL.includes(s.status) && timer.current) {
          window.clearInterval(timer.current);
        }
      } catch (e) { /* ignore transient */ }
    }, 2000);
  };

  const onUpload = async () => {
    if (!file) return;
    setBusy(true); setError(null); setStatus(null);
    try {
      const doc = await uploadDocument(file);
      setDocId(doc.id);
      setStatus(doc.status);
      poll(doc.id);
    } catch (e: any) {
      setError(e?.response?.data?.detail || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h2>Upload PDF</h2>
      <div className="card">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <div style={{ marginTop: 12 }}>
          <button onClick={onUpload} disabled={!file || busy}>
            {busy ? "Đang tải lên..." : "Upload & xử lý"}
          </button>
        </div>
      </div>

      {docId && (
        <div className="card">
          <div>Document ID: <code>{docId}</code></div>
          <div style={{ marginTop: 8 }}>
            Trạng thái: <span className={`badge ${status}`}>{status}</span>
          </div>
          {status && !TERMINAL.includes(status) && (
            <p className="muted">Đang xử lý pipeline (uploaded → parsed → indexed)...</p>
          )}
          {status === "indexed" && <p className="muted">✅ Hoàn tất! Vào tab Playground để hỏi–đáp.</p>}
          {error && <pre style={{ color: "#991b1b" }}>{error}</pre>}
        </div>
      )}
    </div>
  );
}
