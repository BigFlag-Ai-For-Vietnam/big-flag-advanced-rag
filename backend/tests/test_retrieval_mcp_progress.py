"""Progress bridge của MCP client — offline, không mở transport thật."""
import asyncio
import json
from types import SimpleNamespace

from app.retrieval.mcp import client


def test_client_forwards_versioned_progress_and_ignores_malformed(monkeypatch):
    class FakeSession:
        async def call_tool(self, _name, _arguments, progress_callback=None):
            await progress_callback(1, None, "not-json")
            await progress_callback(2, None, json.dumps({
                "v": 1, "seq": 2, "stage": "plan", "status": "completed", "label": "done"
            }))
            return SimpleNamespace(
                isError=False,
                structuredContent={
                    "citations": [], "graph_facts": [], "normalized_question": "q",
                    "rewritten_question": "q", "tool_calls": [], "subgoals": [],
                },
            )

    monkeypatch.setattr(client, "_session", FakeSession())
    events = []

    async def collect(event):
        events.append(event)

    result = asyncio.run(client.retrieve("q", progress=collect))

    assert result.rewritten_question == "q"
    assert [event["stage"] for event in events] == ["plan"]
