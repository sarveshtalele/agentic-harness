"""Getting JSON out of a model reply: tolerant decoding, shape checks, the format rule, and the typed ask with retries."""
from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from backend.core.errors import ModelJsonError, ModelSchemaError, ModelTruncated
from backend.core.security import redact

T = TypeVar("T", bound=BaseModel)


TOOL_MARKUP = re.compile(r"<[｜|]DSML[｜|]")  # DeepSeek's native tool-call syntax, written as text instead of a real call


def _strip_tool_markup(text: str) -> str:
    """Some models write tool syntax as text when tools are switched off for the final answer."""
    found = TOOL_MARKUP.search(text)
    return (text[:found.start()] if found else text).strip()


_LENIENT = json.JSONDecoder(strict=False)  # models put raw line breaks inside strings
_BAD_ESCAPE = re.compile(r'\\(?!["\\/bfnrtu])')


def _decode(text: str, start: int):
    try:
        return _LENIENT.raw_decode(text, start)[0]
    except json.JSONDecodeError:
        return _LENIENT.raw_decode(_BAD_ESCAPE.sub(r"\\\\", text[start:]))[0]  # paths and regexes often carry a lone backslash


class ReplyError(ValueError):
    """Why a reply gave no usable JSON. kind is "json" when it is not JSON at all and "shape" when it is JSON of the wrong shape."""

    def __init__(self, message: str, pos: int | None = None, kind: str = "json"):
        super().__init__(message)
        self.pos, self.kind = pos, kind


_LOOKS_LIKE_JSON = re.compile(r'[\[{]\s*(?:["\[{}\]]|$)')  # prose brackets such as [FR-001] or {note} do not match


def _list_is_answer(text: str, start: int, required: tuple[str, ...]) -> bool:
    """A list that is the value of some other key belongs to a bigger object, so on its own it is a fragment."""
    key = re.search(r'"([^"\\]+)"\s*:\s*$', text[max(0, start - 200) : start])
    return key is None or key.group(1) in required


def extract_json(text: str, required: tuple[str, ...] = ()):
    """Return the first real object or list of objects. Prose can hold brackets like [FR-001].

    A reply that starts as JSON but does not parse is an error with the position. An inner fragment is never the
    answer: an object needs every required name, and a list must be the answer itself or the value of a required name.
    """
    broken = None
    seen = None
    for match in re.finditer(r"[\[{]", text):
        try:
            found = _decode(text, match.start())
        except json.JSONDecodeError as exc:
            if broken is None and _LOOKS_LIKE_JSON.match(text, match.start()):
                broken = (match.start() + exc.pos, exc.msg)
            continue
        if isinstance(found, dict) and found and all(name in found for name in required) and (required or not broken):
            return found
        if isinstance(found, list) and found and all(isinstance(item, dict) for item in found) and _list_is_answer(text, match.start(), required):
            return found
        if isinstance(found, dict) and found and seen is None:
            seen = found
    if broken:
        raise ReplyError(f"not valid JSON near character {broken[0]} of {len(text)}: {broken[1]}", broken[0])
    if seen is not None:
        raise ReplyError(f"valid JSON but without the required fields {[name for name in required if name not in seen]}; it has {sorted(seen)}", kind="shape")
    raise ReplyError("not JSON at all: no object or list was found")


def _fit_schema(found, schema: type[BaseModel]):
    """Some models send a bare list when the schema is one object holding a list, such as {"cases": [...]}."""
    if isinstance(found, list):
        names = [name for name, field in schema.model_fields.items() if field.is_required()]
        if len(names) != 1:
            raise ValueError("Expected one JSON object, not a list")
        return {names[0]: found}
    return found


def format_rule(schema: type[BaseModel]) -> str:
    return ("Reply with only one JSON object matching this schema. Every value must be a plain JSON value, never code or an expression: "
            f"describe long or repeated data in words, as in \"a string of 81 spaces\".\n{json.dumps(schema.model_json_schema())}")


class TypedReply:
    """AgentCall's typed ask: JSON of a schema, with the validation errors fed back until it passes."""

    async def typed(self, message: str, schema: type[T], attempts: int = 3) -> T:
        """Ask for JSON matching schema, feeding validation errors back until it passes."""
        rule = format_rule(schema)
        prompt = f"{message}\n\n{rule}"
        failure = None
        for attempt in range(1, attempts + 1):
            # some models narrate after tool calls and never answer, so retries answer from what was already read
            reply = await self.text(prompt, tools_allowed=attempt == 1, cut_off_ok=True)
            facts = self._facts(attempt=attempt, reply=reply)
            # a cut-off reply can still hold a parseable fragment, so it never reaches the parser
            if facts["finish_reason"] == "length":
                failure = ModelTruncated(f"Agent {self.key} was cut off at the token limit after {len(reply)} characters.", **facts)
                prompt = f"Your reply was cut off at the token limit. Send the complete answer again with every text field much shorter. {rule}"
                continue
            try:
                required = tuple(name for name, field in schema.model_fields.items() if field.is_required())
                return schema.model_validate(_fit_schema(extract_json(reply, required), schema))
            except ReplyError as exc:
                where = {"parse_pos": exc.pos, "parse_context": redact(reply[max(0, exc.pos - 80) : exc.pos + 80])} if exc.pos is not None else {}
                failure = (ModelSchemaError if exc.kind == "shape" else ModelJsonError)(f"Agent {self.key} sent a reply that is {exc}.", technical=str(exc), **where, **facts)
                # the position alone means little to a model, so it sees the text that broke
                error = f"{exc}. The problem is here: {where['parse_context']}" if where else str(exc)
            except ValidationError as exc:
                fields = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'reply'}: {e['msg']}" for e in exc.errors()[:5])
                failure = ModelSchemaError(f"Agent {self.key} sent JSON that does not match {schema.__name__}: {fields}.", technical=str(exc)[:1500], **facts)
                error = str(exc)[:1500]
            except ValueError as exc:
                failure = ModelSchemaError(f"Agent {self.key} sent JSON of the wrong shape: {exc}.", technical=str(exc), **facts)
                error = str(exc)
            # same session, so the agent keeps what it read and only has to format its answer
            prompt = f"That reply was rejected: {error}\nUsing what you have already read, send the complete answer now. {rule}"
        raise failure
