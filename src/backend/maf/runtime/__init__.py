"""Agent construction on the real Microsoft Agent Framework, with middleware and JSON validation."""
from __future__ import annotations

import time
from pathlib import Path

from pydantic import BaseModel

from backend.config import RUN_TOKEN_LIMIT, repo_dir
from backend.core import auth, ledger, prompts
from backend.core import skills as skill_lib
from backend.core.errors import AllowanceError, ModelJsonError, ModelTruncated
from backend.db import db, new_id, now
from backend.core.security import redact
from backend.maf import governance, llm
from backend.maf.runtime.factory import CHAT_AGENTS, build, tool_audit
from backend.maf.runtime.context import ProjectContext
from backend.maf.runtime.emit import _emit, set_emitter
from backend.maf.runtime.gate import _gates, _model_gate
from backend.maf.runtime.json_reply import (
    TOOL_MARKUP,
    ReplyError,
    TypedReply,
    _decode,
    _fit_schema,
    _strip_tool_markup,
    extract_json,
    format_rule,
)


class AgentCall(TypedReply):
    """One agent bound to a run: tracks tokens and records which prompt version produced an output."""

    def __init__(self, run_id: str | None, project_id: str, agent_key: str, *, root: Path | None = None, tool_list=None, source: str = "workflow", chat: bool = False,
                 skills: tuple[str, ...] | None = None, refs: tuple[str, ...] | None = None):
        """`skills` picks which of the agent's plugin skills this stage sends (default all of them, () none) and `refs` which of their reference files (default all)."""
        self.run_id, self.project_id, self.key, self.source = run_id, project_id, agent_key, source
        policy_skills = governance.POLICIES[agent_key].skills
        if skills is not None and (unknown := [n for n in skills if n not in policy_skills]):
            raise ValueError(f"{agent_key} does not use the skill {', '.join(unknown)}. Its policy lists: {', '.join(policy_skills) or 'none'}")
        available = skill_lib.for_agent(agent_key)
        self.skill_set = skill_lib.render([n for n in (policy_skills if skills is None else skills) if n in available], refs)
        self._skill_sent = False
        self.user_id = auth.acting_user(project_id, run_id)
        self.model = auth.model_for(project_id, agent_key, run_id, self.user_id)  # refused here when this account may not use it
        self.agent = build(agent_key, project_id, tool_list, root=root, run_id=run_id, source=source, chat=chat, user_id=self.user_id, model=self.model, skill_set=self.skill_set)
        self.prompt_ref = prompts.ref(agent_key) + skill_lib.ref_suffix(self.skill_set)  # names the prompt version and the skill text sent
        # one session per call, so retries keep the conversation
        self.session = self.agent.create_session()
        self.has_tools = bool(self.agent.default_options.get("tools"))
        self.last_response = None
        self.last_call: dict = {}
        self.tokens = 0  # everything this call object has used, retries included, so a stage can report what a review really cost

    def _facts(self, **more) -> dict:
        """What a failure record needs to prove what was asked of which model."""
        return {"agent": self.key, "prompt_ref": self.prompt_ref, "model": self.model or str(getattr(self.agent.client, "model", "") or ""), **self.last_call, **more}

    def _check_run_limit(self) -> None:
        """Stops the run at its token limit. Checked again once a call has its turn at the model gate: calls queued behind the concurrency limit were otherwise all admitted before the first one had spent anything."""
        if RUN_TOKEN_LIMIT <= 0:
            return
        if self.run_id:
            with db() as con:
                row_val = con.execute("SELECT tokens_in+tokens_out FROM runs WHERE id=?", (self.run_id,)).fetchone()
                used = row_val[0] if row_val else 0
            if used >= RUN_TOKEN_LIMIT:
                raise AllowanceError(f"Run stopped: it used {used} tokens, over the limit of {RUN_TOKEN_LIMIT}.", action="Raise ATLAS_RUN_TOKEN_LIMIT, or ask your administrator, then retry the stage.", agent=self.key)

    async def text(self, message: str, tools_allowed: bool = True, *, cut_off_ok: bool = False) -> str:
        self._check_run_limit()
        auth.check_allowance(self.project_id, self.user_id, self.model)  # long runs can reach a limit part way through
        options = {"tool_choice": "none"} if not tools_allowed and self.has_tools else {}
        emit = _emit.get()
        if emit:
            emit("agent_call", f"{self.key} is working, waiting for the model", {"agent": self.key})
        message = governance.guard_text(self.key, message, "input", self.project_id, self.run_id)
        if self.skill_set.text and not self._skill_sent:
            # trusted platform text goes after the guard, which is for untrusted text. It comes first, so the stable part leads the message
            message = f"{self.skill_set.text}\n\nTASK:\n{message}"
            self._skill_sent = True  # the session keeps it, so a retry does not send it again
            if emit:
                for item in self.skill_set.items:
                    emit("skill", f"Skill {item['name']} v{item['version']} is in use by {self.key}", {"agent": self.key, "skill": item["name"], "version": item["version"], "refs": item["refs"], "sha256": item["sha256"][:12]})
                for left_out in self.skill_set.skipped:
                    emit("warning", f"Reference {left_out} was left out: over the size limit", {"agent": self.key})
        started = time.perf_counter()
        try:
            async with _model_gate():
                self._check_run_limit()
                response = await self.agent.run(message, session=self.session, options=options)
        except AllowanceError:
            raise
        except Exception as exc:
            self.last_call = {"duration_ms": int((time.perf_counter() - started) * 1000)}
            error = governance.typed_error(self.key, exc, self.project_id, self.run_id)
            error.detail = {**self._facts(), **error.detail}
            raise error from exc
        self.last_response = response
        usage = response.usage_details or {}
        tokens = (usage.get("input_token_count") or 0) + (usage.get("output_token_count") or 0)
        self.last_call = {"tokens_in": usage.get("input_token_count") or 0, "tokens_out": usage.get("output_token_count") or 0, "duration_ms": int((time.perf_counter() - started) * 1000),
                          "finish_reason": str(getattr(response.finish_reason, "value", response.finish_reason) or "")}
        self.tokens += tokens
        if self.run_id:
            with db() as con:
                con.execute("UPDATE runs SET tokens_in=tokens_in+?, tokens_out=tokens_out+? WHERE id=?",
                            (usage.get("input_token_count") or 0, usage.get("output_token_count") or 0, self.run_id))
        emit = _emit.get()
        if emit:
            emit("agent", f"{self.key} replied ({tokens} tokens)", {"agent": self.key, "tokens": tokens, "prompt": self.prompt_ref})
        ledger.append(self.project_id, f"agent:{self.key}", "agent.run", self.prompt_ref, {"run_id": self.run_id, "usage": dict(usage)})
        # response.text joins narration from every tool round; the answer is the last assistant message
        final = next((clean for m in reversed(response.messages) if m.role == "assistant" and (clean := _strip_tool_markup(m.text or "")).strip()), "")
        if not final.strip() and self.has_tools:
            final = "The agent finished without a written summary."
        if not final.strip():
            raise ModelJsonError(f"Agent {self.key} returned an empty reply", **self._facts())
        final = governance.guard_text(self.key, final.strip(), "output", self.project_id, self.run_id)
        if self.last_call["finish_reason"] == "length" and not cut_off_ok:
            raise ModelTruncated(f"Agent {self.key} was cut off at the token limit after {len(final)} characters.", reply=final, **self._facts())
        self._live_groundedness(final)
        return final

    def _live_groundedness(self, reply: str) -> None:
        """Free check of every real reply: do its cited files, lines, and quotes exist in this project's repository? A reply with no citations records nothing."""
        root = repo_dir(self.project_id)
        if self.source == "eval" or not root.is_dir():
            return
        from backend.maf.evals import metrics, store  # late: evals imports this module

        try:
            store.record_live(self.key, self.project_id, self.prompt_ref, metrics.groundedness(reply, root=root))
        except (OSError, ValueError):  # the check must never fail a run
            return


def memory_add(project_id: str, content: str, source: str) -> dict:
    memory = {"id": new_id("mem"), "content": redact(content.strip()), "source": source, "created_at": now()}
    with db() as con:
        con.execute("INSERT INTO memories VALUES (?,?,?,?,?)", (memory["id"], project_id, memory["content"], source, memory["created_at"]))
    return memory


__all__ = ["AgentCall", "BaseModel", "CHAT_AGENTS", "ProjectContext", "ReplyError", "TOOL_MARKUP", "_decode", "_emit", "_fit_schema", "_gates", "_model_gate", "_strip_tool_markup", "build",
           "extract_json", "format_rule", "governance", "llm", "memory_add", "set_emitter", "tool_audit", "Path"]
