/** Parse SSE từ POST fetch. EventSource không hỗ trợ request body nên dùng ReadableStream. */
export function parseSseFrame(frame: string): any | null {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n")
    .trim();
  if (!data || data === "[DONE]") return null;
  try { return JSON.parse(data); } catch { return null; }
}

export async function consumeSse(
  url: string,
  body: unknown,
  signal: AbortSignal,
  onEvent: (event: any) => void,
): Promise<void> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    let detail = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      if (payload?.detail) detail = payload.detail;
    } catch { /* response không phải JSON */ }
    throw new Error(detail);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const processFrame = (frame: string) => {
    const event = parseSseFrame(frame);
    if (event != null) onEvent(event);
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split(/\r?\n\r?\n/);
    buffer = frames.pop() ?? "";
    frames.forEach(processFrame);
  }
  buffer += decoder.decode();
  if (buffer.trim()) processFrame(buffer);
}
