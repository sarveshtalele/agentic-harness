"""Naming (docs/PHASE3_PLAN.md section 3): visible UI text uses the agreed names and none of the retired words.
The `ATLAS_` setting names and URL slugs are identifiers, not text, and stay."""
import re
from pathlib import Path

UI = Path(__file__).resolve().parents[1] / "src" / "frontend"
RETIRED = re.compile(r"\b(Autonomous|autonomous|Enterprise|enterprise|AI SDLC|Atlas)\b")


def test_no_retired_words_in_visible_ui_text():
    found = []
    for folder in ("app", "features", "components", "content"):
        for path in (UI / folder).rglob("*.ts*"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if RETIRED.search(line) and "slug:" not in line and "ATLAS_" not in line:
                    found.append(f"{path.relative_to(UI)}:{number}: {line.strip()[:100]}")
    assert not found, "Use the agreed names (docs/DEVELOPER_GUIDE.md section 7):\n" + "\n".join(found)
