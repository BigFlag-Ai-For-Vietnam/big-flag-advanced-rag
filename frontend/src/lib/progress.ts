import type { ProgressEvent } from "../api/client";

function eventKey(event: ProgressEvent) {
  const detail = event.detail;
  return [event.stage, detail?.subgoal_id ?? "", detail?.hop ?? ""].join(":");
}

function canClose(started: ProgressEvent, terminal: ProgressEvent) {
  if (started.stage !== terminal.stage) return false;
  const startedDetail = started.detail;
  const terminalDetail = terminal.detail;
  if (
    startedDetail?.subgoal_id != null
    && terminalDetail?.subgoal_id != null
    && startedDetail.subgoal_id !== terminalDetail.subgoal_id
  ) return false;
  if (
    startedDetail?.hop != null
    && terminalDetail?.hop != null
    && startedDetail.hop !== terminalDetail.hop
  ) return false;
  return true;
}

/** Ghép started -> terminal của cùng một step; bỏ event lặp/out-of-order. */
export function upsertProgress(current: ProgressEvent[], event: ProgressEvent): ProgressEvent[] {
  if (current.some((item) => item.seq === event.seq && item.pipeline === event.pipeline)) return current;
  const maxSeq = current.reduce((max, item) => Math.max(max, item.seq), 0);
  if (event.seq < maxSeq) return current;
  const key = eventKey(event);
  if (event.status !== "started") {
    let index = -1;
    for (let i = current.length - 1; i >= 0; i -= 1) {
      if (eventKey(current[i]) === key && current[i].status === "started") {
        index = i;
        break;
      }
    }
    // Một số producer cũ không gắn hop/subgoal vào event started nhưng có ở
    // terminal event. Fallback tương thích này vẫn đóng đúng lifecycle step.
    if (index < 0) {
      for (let i = current.length - 1; i >= 0; i -= 1) {
        if (current[i].status === "started" && canClose(current[i], event)) {
          index = i;
          break;
        }
      }
    }
    if (index >= 0) {
      const next = [...current];
      next[index] = event;
      return next;
    }
  }
  return [...current, event];
}
