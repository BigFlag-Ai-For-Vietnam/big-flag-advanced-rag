"""Async answer stream retry đúng 1 lần trước token đầu tiên."""
import asyncio
from types import SimpleNamespace

from app.services import llm_client


class FakeStream:
    def __init__(self, contents=None, error=None):
        self.contents = contents or []
        self.error = error

    async def __aiter__(self):
        if self.error:
            raise self.error
        for content in self.contents:
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


class FakeAsyncClient:
    def __init__(self, stream):
        self.stream = stream
        self.closed = False
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **_kwargs):
        return self.stream

    async def close(self):
        self.closed = True


def test_stream_retries_once_when_provider_fails_before_first_token(monkeypatch):
    clients = [
        FakeAsyncClient(FakeStream(error=RuntimeError("CancelledError"))),
        FakeAsyncClient(FakeStream(contents=["xin ", "chào"])),
    ]
    monkeypatch.setattr(llm_client, "AsyncOpenAI", FakeAsyncClient)
    monkeypatch.setattr(llm_client, "make_openai_client", lambda **_kwargs: clients.pop(0))

    async def collect():
        return [item async for item in llm_client.chat_stream_async(
            [{"role": "user", "content": "q"}], model="test-model"
        )]

    assert asyncio.run(collect()) == ["xin ", "chào"]
    assert clients == []


def test_stream_does_not_retry_after_content_was_emitted(monkeypatch):
    class PartialStream:
        async def __aiter__(self):
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="một phần"))])
            raise RuntimeError("CancelledError")

    created = []

    def factory(**_kwargs):
        client = FakeAsyncClient(PartialStream())
        created.append(client)
        return client

    monkeypatch.setattr(llm_client, "AsyncOpenAI", FakeAsyncClient)
    monkeypatch.setattr(llm_client, "make_openai_client", factory)

    async def collect():
        return [item async for item in llm_client.chat_stream_async(
            [{"role": "user", "content": "q"}], model="test-model"
        )]

    try:
        asyncio.run(collect())
        assert False, "partial stream failure must be surfaced"
    except llm_client.LLMError:
        pass
    assert len(created) == 1
