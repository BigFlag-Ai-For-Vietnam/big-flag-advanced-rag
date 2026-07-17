"""BaseChatModel (LangChain) wrap quanh llm_client.chat_with_tools()/chat().

Cầu nối để react subgraph (langgraph.prebuilt.create_react_agent) dùng được LLM FPT
qua interface LangChain — mọi lệnh gọi thật vẫn đi qua llm_client.py (single
choke-point cho FPT theo invariant CLAUDE.md), file này không tự gọi openai/FPT.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.outputs import ChatGeneration, ChatResult

from app.services import llm_client


def _to_openai_message(message: BaseMessage) -> dict:
    if isinstance(message, SystemMessage):
        return {"role": "system", "content": message.content}
    if isinstance(message, HumanMessage):
        return {"role": "user", "content": message.content}
    if isinstance(message, ToolMessage):
        return {"role": "tool", "content": message.content, "tool_call_id": message.tool_call_id}
    if isinstance(message, AIMessage):
        out: dict = {"role": "assistant", "content": message.content or None}
        if message.tool_calls:
            out["tool_calls"] = [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["args"], ensure_ascii=False),
                    },
                }
                for tc in message.tool_calls
            ]
        return out
    raise ValueError(f"Không hỗ trợ message type: {type(message)}")


class ChatFPT(BaseChatModel):
    """Chat model FPT cho LangGraph — chỉ dùng cho react subgraph của Retrieval Engine."""

    temperature: float = 0.0
    max_tokens: int = 1024

    @property
    def _llm_type(self) -> str:
        return "fpt-chat"

    def bind_tools(self, tools, *, tool_choice: str | None = None, **kwargs: Any):
        from langchain_core.utils.function_calling import convert_to_openai_tool

        formatted = [convert_to_openai_tool(t) for t in tools]
        return super().bind(tools=formatted, tool_choice=tool_choice or "auto", **kwargs)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        openai_messages = [_to_openai_message(m) for m in messages]
        tools = kwargs.get("tools")
        tool_choice = kwargs.get("tool_choice", "auto")

        if tools:
            raw = llm_client.chat_with_tools(
                openai_messages,
                tools,
                tool_choice=tool_choice,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tag="react_agent",
            )
            content = raw.content or ""
            raw_tool_calls = raw.tool_calls
        else:
            content = llm_client.chat(
                openai_messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                tag="react_agent",
            )
            raw_tool_calls = None

        tool_calls: list[ToolCall] = []
        for tc in raw_tool_calls or []:
            tool_calls.append(
                ToolCall(
                    name=tc.function.name,
                    args=json.loads(tc.function.arguments or "{}"),
                    id=tc.id,
                    type="tool_call",
                )
            )

        ai_message = AIMessage(content=content, tool_calls=tool_calls)
        return ChatResult(generations=[ChatGeneration(message=ai_message)])
