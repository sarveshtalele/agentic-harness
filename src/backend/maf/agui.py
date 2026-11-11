"""AG-UI endpoint for the chatbot. MAF's AgentFrameworkAgent produces the protocol stream.

The project comes from the server-side thread row, never from the client, so a thread id cannot reach
another project's tools. This thin route replaces add_agent_framework_fastapi_endpoint because agents are
built per request with project-scoped tools. Messages are persisted here, around the MAF stream.
"""
from __future__ import annotations

import json
import logging

from ag_ui.core import RunErrorEvent
from ag_ui.encoder import EventEncoder
from agent_framework.ag_ui import AgentFrameworkAgent
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.core import auth, ledger, plugins
from backend.core import skills
from backend.core.errors import stack_of
from backend.core.security import redact, sha256
from backend.db import db, new_id, now, row, rows
from backend.maf import engine, governance, harness, llm, skill_chat, tools
from backend.maf import runtime as agents
from backend.maf.harness_kit import prompt_hooks
from backend.maf.harness_kit.nudges import HideLoopNudges

router = APIRouter()
BUDGET_NOTICE = ("\n\n*Stopped: this turn reached its tool budget before the model finished, so its last tool call did not run. Reply \"continue\" to go on; the harness keeps its todos.*")


def create_thread(project_id: str, agent: str, title: str = "New chat", model: str = "") -> dict:
    if agent not in agents.CHAT_AGENTS:
        raise ValueError(f"Unknown agent {agent}")
    if model:
        auth.permit_model(auth.signer(), model)
    thread = {"id": new_id("thr"), "project_id": project_id, "title": title, "agent": agent, "created_at": now(), "updated_at": now(), "model": model}
    with db() as con:
        con.execute("INSERT INTO chat_threads (id, project_id, title, agent, created_at, updated_at, model) VALUES (:id,:project_id,:title,:agent,:created_at,:updated_at,:model)", thread)
    return thread


def thread_messages(thread_id: str) -> list[dict]:
    with db() as con:
        return rows(con.execute("SELECT id, role, content, agent, created_at FROM chat_messages WHERE thread_id=? ORDER BY seq", (thread_id,)))


def _append(thread_id: str, role: str, content: str, agent: str, message_id: str | None = None) -> None:
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        seq = con.execute("SELECT COALESCE(MAX(seq),0)+1 FROM chat_messages WHERE thread_id=?", (thread_id,)).fetchone()[0]
        con.execute("INSERT INTO chat_messages VALUES (?,?,?,?,?,?,?)", (thread_id, seq, message_id or new_id("msg"), role, redact(content), agent, now()))
        con.execute("UPDATE chat_threads SET updated_at=? WHERE id=?", (now(), thread_id))
        title = con.execute("SELECT title FROM chat_threads WHERE id=?", (thread_id,)).fetchone()["title"]
        if role == "user" and title == "New chat":
            con.execute("UPDATE chat_threads SET title=? WHERE id=?", (" ".join(content.split())[:60], thread_id))


def _text_of(message: dict) -> str:
    content = message.get("content")
    if isinstance(content, list):
        return " ".join(part.get("text", "") for part in content if isinstance(part, dict))
    return content or ""


@router.post("/agui/{agent_key}")
async def agui(agent_key: str, request: Request):
    if agent_key not in agents.CHAT_AGENTS:
        raise HTTPException(404, "Unknown agent")
    body = await request.json()
    thread_id = body.get("threadId") or body.get("thread_id") or ""
    with db() as con:
        thread = row(con.execute("SELECT * FROM chat_threads WHERE id=?", (thread_id,)))
    if not thread:
        raise HTTPException(404, "Unknown thread. Create one first")
    project_id = thread["project_id"]
    if not auth.can_see_project(project_id):
        raise HTTPException(404, "Unknown thread. Create one first")
    if not auth.can_write(project_id):
        raise HTTPException(403, "Your role is viewer. A viewer can read but not chat with the agents")
    incoming = body.get("messages") or []
    last_user = next((m for m in reversed(incoming) if m.get("role") == "user"), None)
    hooked = None  # the plugins' prompt hooks' outcome (harness only)
    if last_user:
        clean = governance.guard_text(agent_key, _text_of(last_user), "input", project_id)
        if clean != _text_of(last_user):  # the model and the store only ever see the redacted text
            last_user["content"] = clean
        first = not thread_messages(thread_id)
        _append(thread_id, "user", clean, agent_key, last_user.get("id"))
        if agent_key == harness.AGENT:
            # plan H3: plugins' SessionStart and UserPromptSubmit hooks see the human's own text, before any expansion
            hooked = None if body.get("resume") else await prompt_hooks.submitted(project_id, thread_id, auth.acting_user(project_id), clean, first)
            command = plugins.expand_slash(clean)  # the model gets the command's instructions; the chat keeps what the user typed
            last_user["content"] = prompt_hooks.for_model(command or clean, hooked) if hooked else (command or clean)
    encoder = EventEncoder()

    async def stream():
        if hooked and hooked.blocked:  # a plugin's UserPromptSubmit hook refused the message: the model is not called
            for event in prompt_hooks.blocked_events(thread_id, body.get("runId") or new_id("rn"), hooked.reason):
                yield encoder.encode(event)
            return
        answer: list[str] = []
        agents.set_emitter(None)
        try:
            user_id = auth.acting_user(project_id)
            if agent_key == harness.AGENT:  # MAF's own harness: it loads skills itself through progressive disclosure
                agent = harness.build(project_id, thread_id, engine.start, user_id=user_id, model=thread["model"])
            else:
                chat_tools = tools.document_tools(project_id) + tools.chat_tools(project_id, thread_id, engine.start)
                model = auth.model_for(project_id, agent_key, None, user_id, thread["model"])
                rendered = skills.render([])
                if last_user and skill_chat.mode(agent_key, model) == "pick":  # one small call per user message; a failure means no skill
                    text = _text_of(last_user)
                    chosen = await skill_chat.pick(agent_key, project_id, user_id, model, text, key=(thread_id, last_user.get("id") or sha256(text)))
                    rendered = skills.render(chosen)
                    if chosen:
                        logging.getLogger("aqe.chat").info("chat %s uses skill %s", thread_id, ", ".join(chosen))
                agent = agents.build(agent_key, project_id, chat_tools, chat=True, source="chat", user_id=user_id, model=model, skill_set=rendered)
            payload = {"messages": incoming, "thread_id": thread_id, "run_id": body.get("runId") or new_id("rn"),
                       "state": body.get("state") or {}, "tools": body.get("tools") or [], "context": body.get("context") or [],
                       "forwarded_props": body.get("forwardedProps") or {}}
            if agent_key == harness.AGENT:
                # The thread snapshot keeps mode, approvals and history per project and person across requests. The scope
                # is set here from the server's own ids; a risky tool ends the run with an approval interrupt, and the
                # client's next request carries `resume` with the human's answer.
                wrapped = AgentFrameworkAgent(HideLoopNudges(agent), require_confirmation=False, snapshot_store=harness.SNAPSHOTS)
                wrapped._approval_state_store = harness.APPROVALS  # ponytail: 1.24 takes no store argument; see harness_kit/snapshots.py
                payload["__ag_ui_snapshot_scope"] = payload["__ag_ui_approval_scope"] = harness.scope(project_id, user_id)
                if body.get("resume"):
                    payload["resume"] = body["resume"]
            else:
                wrapped = AgentFrameworkAgent(agent, require_confirmation=False)
            # When a turn reaches its tool budget, MAF asks for a final answer with tools off and some models then write
            # their next tool call as text (DeepSeek DSML). Nothing ran, so that text is cut and the user is told plainly.
            markup = False
            async for event in wrapped.run(payload):
                kind = str(getattr(getattr(event, "type", ""), "value", getattr(event, "type", "")))
                if kind == "TEXT_MESSAGE_CONTENT":
                    if markup:
                        continue
                    found = agents.TOOL_MARKUP.search("".join(answer) + event.delta)
                    if found:  # ponytail: markup split across two deltas leaves its first characters on screen
                        markup = True
                        event.delta = event.delta[: max(0, found.start() - sum(map(len, answer)))] + BUDGET_NOTICE
                    answer.append(event.delta)
                if markup and kind == "MESSAGES_SNAPSHOT":
                    continue  # the snapshot still holds the markup; the streamed text above is the clean copy
                # every event type is redacted, including the final message snapshot
                # ponytail: a secret split across two deltas passes in the live stream; the snapshot and stored copy are clean
                yield redact(encoder.encode(event))
            if markup:
                logging.getLogger("aqe.chat").warning("chat %s: %s reached its tool budget; tool-call text from the model was cut", thread_id, agent_key)
        except llm.LLMNotConfigured as exc:
            yield encoder.encode(RunErrorEvent(message=str(exc), code="LLM_NOT_CONFIGURED"))
        except Exception as exc:  # recorded in the log with an id, and the user sees the failure in chat instead of a dead stream
            error = governance.typed_error(agent_key, exc, project_id)
            error_id = new_id("err")
            logging.getLogger("aqe.chat").error("chat %s failed: %s error_id=%s %s", thread_id, error.code, error_id, error.message)
            logging.getLogger("aqe.chat").error("stack for %s: %s", error_id, stack_of(exc))
            yield encoder.encode(RunErrorEvent(message=f"{error.message} {error.action} (error {error_id})", code=error.code))
        finally:
            if answer:
                reply = governance.guard_text(agent_key, "".join(answer), "output", project_id)
                _append(thread_id, "assistant", reply, agent_key)
                ledger.append(project_id, f"agent:{agent_key}", "chat.reply", thread_id, {"chars": sum(map(len, answer))})

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


__all__ = ["router", "create_thread", "thread_messages", "json"]
