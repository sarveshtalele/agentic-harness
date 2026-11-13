"""Several tool calls in one model response, each needing approval (live QE cycle, 2026-11-13): MAF collects them and asks
one card at a time; every card must resume, and the turn must end with the model's answer, not
"Collected approval authority is no longer pending"."""
import pytest

from backend.maf import llm
from backend.maf.harness_kit import shells
from tests.helpers_harness import NEEDLE, steps
from tests.scripted_client import ScriptedClient
from tests.test_aqh_cli import cli  # noqa: F401 - fixture: the platform in-process, a folder bound in place


@pytest.mark.skipif(not shells.find_bash(), reason="no bash on this machine")
@pytest.mark.parametrize("count", [2, 3, 5])
def test_every_card_of_a_parallel_batch_resumes(cli, count):  # noqa: F811
    session, project, folder, _ = cli
    batch = {"calls": [{"call": "bash", "args": {"command": f"echo n{i} >> f{i}.txt", "description": f"note {i}"}} for i in range(count)]}
    llm.set_client_override(ScriptedClient([(NEEDLE, steps(batch, "All written."))]))
    events, cards = [], []
    thread = session.new_thread(project)
    session.turn(thread, "write the notes", lambda card: cards.append(card["id"]) or True, events.append, folder)
    errors = [e for e in events if e["type"] == "RUN_ERROR"]
    assert not errors, errors
    assert len(cards) == count and all((folder / f"f{i}.txt").read_text() == f"n{i}\n" for i in range(count))
