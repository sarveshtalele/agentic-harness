"""Tool call ids unique per turn (live QE cycle with gpt-5, 2026-11-13): an endpoint that reuses `functions.bash:3` in a
later round must not collide in MAF's approval store; one streamed response keeps one id across its chunks."""
import pytest
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk

from backend.maf.unique_calls import UniqueCallIdClient


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")  # never used: nothing is sent, only responses are parsed
    return UniqueCallIdClient(model="m", async_client=AsyncOpenAI(base_url="http://127.0.0.1:9/v1"))


def _completion(response_id: str) -> ChatCompletion:
    return ChatCompletion.model_validate({"id": response_id, "object": "chat.completion", "created": 0, "model": "m", "choices": [{
        "index": 0, "finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": "functions.bash:3", "type": "function", "function": {"name": "bash", "arguments": "{\"command\": \"ls\"}"}}]}}]})


def _chunk(response_id: str, call_id: str, args: str) -> ChatCompletionChunk:
    return ChatCompletionChunk.model_validate({"id": response_id, "object": "chat.completion.chunk", "created": 0, "model": "m", "choices": [{
        "index": 0, "delta": {"tool_calls": [{"index": 0, "id": call_id or None, "type": "function",
                                              "function": {"name": "bash" if call_id else None, "arguments": args}}]}}]})


def _ids(contents) -> list[str]:
    return [c.call_id for c in contents if c.type == "function_call"]


def test_the_same_id_in_two_responses_becomes_two_ids(client):
    first = _ids(client._parse_response_from_openai(_completion("resp-1"), {}).messages[0].contents)
    second = _ids(client._parse_response_from_openai(_completion("resp-2"), {}).messages[0].contents)
    assert first[0].startswith("functions.bash:3") and second[0].startswith("functions.bash:3") and first != second


def test_one_streamed_response_keeps_one_id_across_its_chunks(client):
    a = _ids(client._parse_response_update_from_openai(_chunk("resp-1", "functions.bash:3", "{\"command\"")).contents)
    b = _ids(client._parse_response_update_from_openai(_chunk("resp-1", "functions.bash:3", ": \"ls\"}")).contents)
    c = _ids(client._parse_response_update_from_openai(_chunk("resp-2", "functions.bash:3", "{}")).contents)
    assert a == b and a != c
