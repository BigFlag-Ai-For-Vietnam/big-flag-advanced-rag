import { describe, expect, it } from "vitest";
import { parseSseFrame } from "./sse";

describe("parseSseFrame", () => {
  it("parses CRLF and ignores SSE metadata", () => {
    expect(parseSseFrame("event: message\r\ndata: {\"type\":\"token\",\"content\":\"xin chào\"}\r\n"))
      .toEqual({ type: "token", content: "xin chào" });
  });

  it("ignores heartbeat, done, and malformed frames", () => {
    expect(parseSseFrame(": ping")).toBeNull();
    expect(parseSseFrame("data: [DONE]")).toBeNull();
    expect(parseSseFrame("data: nope")).toBeNull();
  });
});
