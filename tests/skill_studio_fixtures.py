"""Shared pieces for the Skill Studio tests: a typed source, and ScriptedClient replies that stand in for the model.

The scripted model "writes" a real script and a real pytest file, so the test step runs genuine tests offline.
"""
from __future__ import annotations

import json
import time

SOURCE = "Invoice INV-7: 3 x Widget at 10 EUR\nInvoice INV-8: 2 x Bolt at 4 EUR\nEach ledger line holds the invoice, the item, the quantity and the net amount."
DESCRIPTION = "Turns invoice text into ledger lines with quantity and net amount. Use when invoice lines must be booked."
SCRIPT = '''"""Ledger lines from invoice text."""
import re

LINE = re.compile(r"Invoice (\\S+): (\\d+) x (\\w+) at (\\d+) EUR")


def lines(text):
    return [{"invoice": m[0], "item": m[2], "quantity": int(m[1]), "net": int(m[1]) * int(m[3])} for m in LINE.findall(text)]
'''
TEST = '''from ledger import lines


def test_net_is_quantity_times_price():
    assert lines("Invoice INV-7: 3 x Widget at 10 EUR") == [{"invoice": "INV-7", "item": "Widget", "quantity": 3, "net": 30}]


def test_text_without_invoices_gives_no_lines():
    assert lines("no invoices here") == []
'''
FILES = ["SKILL.md", "scripts/ledger.py", "scripts/test_ledger.py", "references/rules.md", "assets/ledger.md"]


def unique_name() -> str:
    return f"invoice-lines-{time.time_ns()}"


def plan(name: str, kind: str = "scripts") -> dict:
    files = FILES if kind == "scripts" else [f for f in FILES if not f.startswith("scripts/")]
    return {
        "name": name, "description": DESCRIPTION,
        "tasks": ["Find each invoice line", "Multiply quantity by unit price", "Write one ledger line per item"],
        "files": [{"path": p, "purpose": f"holds {p}"} for p in files],
        "subagents": [],
        "formats": [{"name": "ledger table", "purpose": "one row per item", "template_path": "assets/ledger.md"}],
        "eval_cases": [
            {"input": "Invoice INV-7: 3 x Widget at 10 EUR", "assertions": [{"kind": "contains", "value": "30 EUR"}, {"kind": "regex", "value": r"net \d+"}]},
            {"input": "Invoice INV-8: 2 x Bolt at 4 EUR", "assertions": [{"kind": "contains", "value": "8 EUR"}, {"kind": "not_contains", "value": "cannot"}]},
        ],
    }


def files(name: str, kind: str = "scripts", extra: list[dict] | None = None) -> dict:
    skill_md = f"---\nname: {name}\ndescription: {DESCRIPTION}\n---\n# Invoice lines\n\n1. Find each invoice line.\n2. Multiply quantity by unit price.\n3. Write rows as in assets/ledger.md.\n\nRules: references/rules.md\n"
    out = [{"path": "SKILL.md", "content": skill_md}, {"path": "references/rules.md", "content": "# Rules\n\nAmounts are in EUR.\n"},
           {"path": "assets/ledger.md", "content": "| invoice | item | quantity | net |\n"}]
    if kind == "scripts":
        out += [{"path": "scripts/ledger.py", "content": SCRIPT}, {"path": "scripts/test_ledger.py", "content": TEST}]
    return {"files": out + (extra or [])}


def rules(name: str, kind: str = "scripts", extra: list[dict] | None = None) -> list:
    return [
        ("TASK: plan a new agent skill", json.dumps(plan(name, kind))),
        ("TASK: write every file of the approved skill plan", json.dumps(files(name, kind, extra))),
        ("TASK: apply the skill under test", lambda text: "INV-8 Bolt 2 net 8 EUR" if "INV-8: 2 x Bolt" in text.split("TASK: apply")[-1] else "INV-7 Widget 3 net 30 EUR"),
        ("TASK: handle the input below", "This cannot be booked without more detail."),
    ]


def new_plan(client, project_id: str, kind: str = "scripts") -> dict:
    made = client.post("/api/skill-studio/plans", json={"project_id": project_id, "kind": kind, "source": {"type": "text", "text": SOURCE}, "request": "Book invoice lines"})
    assert made.status_code == 201, made.text
    return made.json()
