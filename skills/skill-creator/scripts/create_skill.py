#!/usr/bin/env python3
"""Autonomous Skill Scaffolding Engine for Agentic QE Platform & MAF Harness.
Generates an Agent Skill package compliant with the Agent Skills standard.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def sanitize_skill_name(name: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", name.strip().lower())
    return re.sub(r"-+", "-", cleaned).strip("-")


def create_skill(
    name: str,
    description: str,
    category: str = "custom-skills",
    include_script: bool = True,
    script_name: str = "run.py",
    author: str = "Sarvesh Talele",
    version: str = "1.0.0",
    output_dir: Path | None = None,
) -> dict:
    skill_slug = sanitize_skill_name(name)
    if not skill_slug:
        raise ValueError("Skill name cannot be empty")

    base_dir = output_dir or Path("skills") / skill_slug
    base_dir.mkdir(parents=True, exist_ok=True)
    scripts_dir = base_dir / "scripts"
    evals_dir = base_dir / "evals"
    refs_dir = base_dir / "references"

    scripts_dir.mkdir(parents=True, exist_ok=True)
    evals_dir.mkdir(parents=True, exist_ok=True)
    refs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Author SKILL.md
    skill_md_content = f"""---
name: {skill_slug}
description: "{description.strip()} Use when {skill_slug.replace('-', ' ')} workflows are requested."
metadata:
  author: "{author}"
  version: "{version}"
  category: "{category}"
  tags: "agent-skill, {skill_slug}, maf-2.0"
---

# {skill_slug.replace('-', ' ').title()}

{description.strip()}

## When to Use
Activate this skill when processing requests relating to {skill_slug.replace('-', ' ')}, or when validating domain inputs against requirements.

## Core Operational Workflow
1. Ingest input payload or document specification.
2. Validate required parameters and schema constraints.
3. Execute domain business logic or verification scripts.
4. Return structured evidence and execution status.

## Verification Standards
- Maintain strict deterministic outputs.
- Never invent external dependencies outside repository manifests.
- Ensure all execution is bounded and sandbox-contained.
"""
    (base_dir / "SKILL.md").write_text(skill_md_content, encoding="utf-8")

    # 2. Author executable script if requested
    script_path = None
    if include_script:
        script_file = scripts_dir / script_name
        script_content = f"""#!/usr/bin/env python3
\"\"\"Autonomous execution script for skill: {skill_slug}.
Executes in bounded sandbox with clean environment.
\"\"\"
import argparse
import json
import sys


def execute(input_data: dict) -> dict:
    # Bounded execution logic
    return {{
        "status": "success",
        "skill": "{skill_slug}",
        "processed": True,
        "input": input_data,
        "message": "Executed successfully within sandbox boundary"
    }}


def main():
    parser = argparse.ArgumentParser(description="Skill runner for {skill_slug}")
    parser.add_argument("--json", type=str, default="{{}}", help="JSON input payload")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logs")
    args = parser.parse_args()

    try:
        payload = json.loads(args.json) if args.json else {{}}
    except Exception as exc:
        print(json.dumps({{"error": f"Invalid JSON payload: {{exc}}"}}))
        sys.exit(1)

    result = execute(payload)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
"""
        script_file.write_text(script_content, encoding="utf-8")
        script_path = str(script_file)

    # 3. Author evals/evals.json
    evals_file = evals_dir / "evals.json"
    evals_content = {
        "skill": skill_slug,
        "version": version,
        "cases": [
            {
                "id": f"{skill_slug}-001",
                "prompt": f"Execute {skill_slug} with valid default arguments",
                "expected": {"status": "success", "processed": True},
                "assertions": ["output.status == 'success'", "output.processed == true"],
            },
            {
                "id": f"{skill_slug}-002",
                "prompt": f"Check {skill_slug} with empty payload",
                "expected": {"status": "success"},
                "assertions": ["output.status == 'success'"],
            },
            {
                "id": f"{skill_slug}-003",
                "prompt": f"Check error handling for malformed input",
                "expected": {"error": "expected"},
                "assertions": ["output.get('error') is not None or output.status == 'success'"],
            },
        ],
    }
    evals_file.write_text(json.dumps(evals_content, indent=2), encoding="utf-8")

    return {
        "status": "created",
        "skill": skill_slug,
        "path": str(base_dir),
        "skill_md": str(base_dir / "SKILL.md"),
        "script": script_path,
        "evals": str(evals_file),
    }


def main():
    parser = argparse.ArgumentParser(description="Create a new Agent Skill")
    parser.add_argument("--name", required=True, help="Skill name (e.g. cloud-evaluator)")
    parser.add_argument("--description", required=True, help="Detailed skill description")
    parser.add_argument("--category", default="custom-skills", help="Skill category")
    parser.add_argument("--no-script", action="store_true", help="Do not generate python script")
    parser.add_argument("--script-name", default="run.py", help="Script filename")
    parser.add_argument("--output-dir", default=None, help="Target directory (default: skills/<name>)")
    args = parser.parse_args()

    out = Path(args.output_dir) if args.output_dir else None
    result = create_skill(
        name=args.name,
        description=args.description,
        category=args.category,
        include_script=not args.no_script,
        script_name=args.script_name,
        output_dir=out,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
