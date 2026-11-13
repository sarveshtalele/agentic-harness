"""MAF's OpenAI chat client with tool call ids that are unique within a conversation turn.

Found on the live QE cycle with gpt-5 (2026-11-13): this endpoint names tool calls `functions.bash:3` and reuses an id in
a later round of the same turn. MAF's AG-UI approval store keys an approval by that id, so the second call replaced the
first one's record, the resume failed with "Collected approval authority is no longer pending", a card stayed open, and
every later message was refused (APPROVAL_RESUME_REQUIRED). Each id the model sends gets a suffix unique to its response:
the same id across the chunks of one streamed response keeps one suffix, so arguments still merge.
"""
from __future__ import annotations

import itertools

from agent_framework.openai import OpenAIChatCompletionClient


class UniqueCallIdClient(OpenAIChatCompletionClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._response_key = ""
        self._ids: dict[tuple[str, str], str] = {}
        self._counter = itertools.count(1)

    def _unique(self, contents: list) -> list:
        for item in contents:
            original = getattr(item, "call_id", None)
            if getattr(item, "type", "") == "function_call" and original:
                key = (self._response_key, original)
                if key not in self._ids:
                    self._ids[key] = f"{original}~{next(self._counter)}"
                item.call_id = self._ids[key]
        return contents

    def _parse_response_from_openai(self, response, options):
        self._response_key = getattr(response, "id", "") or f"r{next(self._counter)}"
        return super()._parse_response_from_openai(response, options)

    def _parse_response_update_from_openai(self, chunk):
        self._response_key = getattr(chunk, "id", "") or self._response_key
        return super()._parse_response_update_from_openai(chunk)

    def _parse_tool_calls_from_openai(self, choice):
        return self._unique(super()._parse_tool_calls_from_openai(choice))
