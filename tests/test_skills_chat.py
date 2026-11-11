"""Plugin skills on MAF: the chat pick."""
import pytest

from backend.db import db, rows
from backend.maf import llm, skill_chat
from tests.scripted_client import ScriptedClient
from tests.helpers_api import client, project, unique  # noqa: F401 - fixtures
from tests.helpers_skills import ARCHITECT


# ---- chat: one small pick per user message, never a failed chat ---------------------

def chat_body(thread, text="Plan the tests for the calculator", message_id="m1"):
    return {"threadId": thread["id"], "runId": "r1", "messages": [{"id": message_id, "role": "user", "content": text}], "state": {}, "tools": [], "context": [], "forwardedProps": {}}


def chat(client, project, rules, text="Plan the tests for the calculator", message_id="m1"):
    scripted = ScriptedClient(rules)
    llm.set_client_override(scripted)
    thread = client.post(f"/api/projects/{project['id']}/chats", json={"agent": "principal-test-architect"}).json()
    with client.stream("POST", "/agui/principal-test-architect", json=chat_body(thread, text, message_id)) as response:
        body = "".join(response.iter_text())
    return scripted, thread, body


def test_chat_picks_a_skill_once_and_adds_it_to_the_turn(client, project):
    scripted, thread, body = chat(client, project, [("You decide which skill", '{"skill": "planning-tests"}'), (ARCHITECT, "Here is a plan"), ("Plan", "x")], message_id=unique("m"))
    assert "Here is a plan" in body and "RUN_FINISHED" in body
    picks = [c for c in scripted.calls if "You decide which skill" in c]
    answers = [c for c in scripted.calls if "You decide which skill" not in c]
    assert len(picks) == 1 and "planning-tests: " in picks[0] and "authoring-user-stories" not in picks[0], "it sees only this agent's skills, by name and description"
    assert len(answers) == 1 and '<skill name="planning-tests"' in answers[0]
    saved = client.get(f"/api/chats/{thread['id']}").json()["messages"]
    assert [m["content"] for m in saved] == ["Plan the tests for the calculator", "Here is a plan"], "the skill text is not stored in the thread"
    with db() as con:
        spent = rows(con.execute("SELECT tokens_in, tokens_out FROM agent_calls WHERE source='chat-skill' ORDER BY id DESC LIMIT 1"))
    assert spent and spent[0]["tokens_in"] + spent[0]["tokens_out"] > 0, "the pick counts as tokens for the user"


@pytest.mark.parametrize("pick_reply", ["I cannot decide.", '{"skill": "healing-tests"}', '{"skill": "none"}', RuntimeError("model down")])
def test_a_failed_pick_leaves_chat_working_without_a_skill(client, project, pick_reply):
    def reply(_text):
        if isinstance(pick_reply, Exception):
            raise pick_reply
        return pick_reply

    scripted, _thread, body = chat(client, project, [("You decide which skill", reply), (ARCHITECT, "Plain answer")], message_id=unique("m"))
    assert "Plain answer" in body and "RUN_FINISHED" in body and "RUN_ERROR" not in body
    assert not any("<skill name=" in c for c in scripted.calls)


def test_the_pick_is_asked_once_for_the_same_message(client, project):
    scripted = ScriptedClient([("You decide which skill", '{"skill": "planning-tests"}')])
    llm.set_client_override(scripted)
    key = ("thr_once", unique("m"))
    first = client.portal.call(lambda: skill_chat.pick("principal-test-architect", project["id"], None, "", "Plan the tests", key=key))
    again = client.portal.call(lambda: skill_chat.pick("principal-test-architect", project["id"], None, "", "Plan the tests", key=key))
    assert first == again == ["planning-tests"] and len(scripted.calls) == 1
    assert client.portal.call(lambda: skill_chat.pick("project-copilot", project["id"], None, "", "anything")) == [] and len(scripted.calls) == 1, "an agent with no skills makes no call"
