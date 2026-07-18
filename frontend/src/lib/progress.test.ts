import { describe, expect, it } from "vitest";
import type { ProgressEvent } from "../api/client";
import { upsertProgress } from "./progress";

const event = (seq: number, status: ProgressEvent["status"]): ProgressEvent => ({
  type: "progress", run_id: "r1", pipeline: "advanced", seq,
  stage: "kb_search", status, label: status, elapsed_ms: seq,
  detail: { subgoal_id: "g1", hop: 1 },
});

describe("upsertProgress", () => {
  it("replaces a started step with its terminal event", () => {
    const result = upsertProgress([event(1, "started")], event(2, "completed"));
    expect(result).toHaveLength(1);
    expect(result[0].status).toBe("completed");
    expect(result[0].seq).toBe(2);
  });

  it("ignores duplicate and out-of-order events", () => {
    const current = [event(4, "completed")];
    expect(upsertProgress(current, event(4, "completed"))).toBe(current);
    expect(upsertProgress(current, event(3, "warning"))).toBe(current);
  });

  it("closes a started step when only the terminal event contains hop metadata", () => {
    const started = { ...event(1, "started"), stage: "assess" as const, detail: undefined };
    const completed = {
      ...event(2, "completed"), stage: "assess" as const, detail: { hop: 1 },
    };
    const result = upsertProgress([started], completed);
    expect(result).toHaveLength(1);
    expect(result[0].status).toBe("completed");
  });
});
