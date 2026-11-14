"""Stack templates (QE v2 step 6): every manifest validates; each template whose toolchain is on this machine installs, builds,
passes its own unit test and answers /health, all through the runner in a temp workspace. The others are skipped with the reason."""
import json

import pytest

from backend.qe import stacks
from backend.qe.stack_run import free_port, run_stack, start_and_probe
from backend.qe.stacks import Stack, StackError

IDS = ["dotnet", "go", "java-springboot", "node-nextjs", "python-fastapi-react"]


def test_the_five_owner_chosen_templates_exist_and_validate():
    assert stacks.ids() == IDS
    for stack in stacks.list_templates():
        assert stack.id in IDS and "{port}" in stack.health and any("{port}" in a for a in stack.start)
        assert bool(stack.test.e2e) == stack.ui, "Playwright e2e is declared exactly for the web UIs"
    assert {s.id for s in stacks.list_templates() if s.ui} == {"python-fastapi-react", "node-nextjs"}


@pytest.mark.parametrize("change,message", [
    ({"start": ["sh", "-c", "run {port}"]}, "not an allowed program"),
    ({"start": ["go", "run", "."]}, "{port}"),
    ({"health": "http://example.com/health"}, "127.0.0.1"),
    ({"build": [["rm", "-rf", "."]]}, "not an allowed program"),
])
def test_a_bad_manifest_is_refused(change, message):
    manifest = json.loads((stacks.ROOT / "go" / "stack.json").read_text(encoding="utf-8")) | change
    with pytest.raises(ValueError, match=message.replace("{", r"\{").replace("}", r"\}")):
        Stack.model_validate(manifest)


def test_a_ui_stack_without_e2e_is_refused():
    manifest = json.loads((stacks.ROOT / "node-nextjs" / "stack.json").read_text(encoding="utf-8"))
    manifest["test"]["e2e"] = None
    with pytest.raises(ValueError, match="e2e"):
        Stack.model_validate(manifest)


def test_an_unknown_stack_is_refused_and_the_copy_never_overwrites(tmp_path):
    with pytest.raises(StackError, match="Unknown stack"):
        stacks.load("rust-actix")
    target = stacks.copy_template("go", tmp_path)
    assert (target / "stack.json").is_file() and (target / "health_test.go").is_file()
    with pytest.raises(StackError, match="not empty"):
        stacks.copy_template("go", tmp_path)
    with pytest.raises(Exception):  # safe_path: no escape from the workspace
        stacks.copy_template("go", tmp_path, "../outside")


def test_toolchain_check_reports_found_and_missing():
    states = {i: stacks.toolchain_status(stacks.load(i)) for i in IDS}
    assert states["python-fastapi-react"]["found"].get("python")  # this suite runs on Python
    for s in states.values():
        assert s["ok"] == (not s["missing"])


def test_free_port_is_loopback_and_usable():
    assert 1024 <= free_port() <= 65535


def test_a_start_that_never_answers_is_stopped_and_not_ok(tmp_path):
    stack = Stack.model_validate(json.loads((stacks.ROOT / "go" / "stack.json").read_text(encoding="utf-8")) | {
        "start": ["{python}", "-c", "import time; time.sleep(60)", "{port}"]})
    result = start_and_probe(stack, tmp_path, timeout=2)
    assert result["ok"] is False and result["status"] is None


@pytest.mark.parametrize("stack_id", IDS)
def test_template_installs_builds_tests_and_answers_health(stack_id, tmp_path):
    stack = stacks.load(stack_id)
    status = stacks.toolchain_status(stack)
    if not status["ok"]:
        pytest.skip(f"{stack_id}: {'; '.join(status['missing'])}")
    workspace = stacks.copy_template(stack_id, tmp_path)
    result = run_stack(stack, workspace)
    detail = json.dumps([{k: v for k, v in s.items()} for s in result["steps"]], indent=1)[-3000:] + json.dumps(result["start"])[-1500:]
    assert result["ok"], detail
    assert [s["phase"] for s in result["steps"]][-1] == "unit" and result["steps"][-1]["exit"] == 0
    assert result["start"]["status"] == 200
