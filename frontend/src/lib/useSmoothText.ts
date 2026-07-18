import { useCallback, useEffect, useRef } from "react";

/** Gom provider delta để React render đều, tránh setState cho mọi token nhỏ. */
export function useSmoothText(append: (text: string) => void, intervalMs = 40) {
  const pending = useRef("");
  const timer = useRef<number | null>(null);
  const appendRef = useRef(append);
  appendRef.current = append;

  const flush = useCallback(() => {
    if (timer.current != null) window.clearTimeout(timer.current);
    timer.current = null;
    if (!pending.current) return;
    const text = pending.current;
    pending.current = "";
    appendRef.current(text);
  }, []);

  const push = useCallback((text: string) => {
    pending.current += text;
    if (timer.current == null) timer.current = window.setTimeout(flush, intervalMs);
  }, [flush, intervalMs]);

  const reset = useCallback(() => {
    if (timer.current != null) window.clearTimeout(timer.current);
    timer.current = null;
    pending.current = "";
  }, []);

  useEffect(() => () => flush(), [flush]);
  return { push, flush, reset };
}
