"""A real run environment for the validity tests: a .venv beside the worktree that sees this test interpreter's packages (pytest)."""
import subprocess
import sys
import venv
from pathlib import Path

from backend.qe.validity.collect import run_python


def make_run_env(worktree: Path) -> None:
    """What install_dependencies leaves: <worktree parent>/.venv. No pip and no network: a .pth file lends it the test interpreter's packages."""
    folder = worktree.parent / ".venv"
    venv.create(folder, with_pip=False)
    python = run_python(worktree)
    purelib = subprocess.run([str(python), "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"], capture_output=True, text=True, timeout=60, check=True).stdout.strip()
    (Path(purelib) / "lent.pth").write_text("\n".join(p for p in sys.path if p and Path(p).is_dir()) + "\n", encoding="utf-8")


CASES = {"TC-APP-001": {"id": "TC-APP-001", "expected_result": "returns 5"}, "TC-APP-002": {"id": "TC-APP-002", "expected_result": "raises TypeError"}}
GOOD = "# CASE_ID: TC-APP-001\nfrom calc import add\n\n\ndef test_TC_APP_001_adds():\n    assert add(2, 3) == 5\n"
