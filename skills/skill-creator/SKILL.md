---
name: skill-creator
description: "Guides the creation, testing, iteration, and packaging of agent skills from requirements, BRDs, and user stories. Use when creating or updating agent skills."
metadata:
  author: "Sarvesh Talele"
  version: "1.4.0"
  archetype: "meta-agent-skill"
  category: "agentic-skills"
  tags: "skill-development, scaffolding, packaging, maf-harness"
---

# Skill Creator: Autonomous Agent Skill Engineering

The `skill-creator` skill guides agents and developers to build, test, package, and onboard high-precision Agent Skills conforming to the Agent Skills standard and Microsoft Agent Framework (MAF 2.0).

## When to Use
- When generating a new agent skill from a Business Requirements Document (BRD), User Stories, or Gherkin scenarios.
- When creating custom deterministic verification scripts for an agent persona.
- When packaging and validating an agent skill for the Agent Marketplace.

## Strict Standards
1. **Frontmatter Specification:** Every skill must begin with standard YAML frontmatter containing:
   - `name`: Lowercase, hyphen-delimited (e.g. `generating-test-code`, `skill-creator`).
   - `description`: A single concise paragraph stating what the skill does and explicit trigger conditions ("Use when...").
   - `metadata`: Including `author`, `version`, and `tags`.
2. **Directory Structure:**
   ```text
   skills/<skill-name>/
     ├── SKILL.md            # Frontmatter and actionable agent instructions
     ├── scripts/            # Executable verification tools (Python / Node)
     │   └── run.py
     ├── evals/              # Benchmark evaluation test cases
     │   └── evals.json
     └── references/         # Supporting domain schemas and guidelines
   ```
3. **Execution Script Sandboxing:**
   - Any bundled script in `scripts/` must accept `--json` or CLI flags and emit structured stdout.
   - Scripts run inside the platform's bounded sandbox with scrubbed environment variables (`clean_env`).
4. **Deterministic Evaluation:**
   - Skills must include at least 3 benchmark test cases in `evals/evals.json` testing groundedness, format conformance, and edge case handling.

## Bundled CLI Tooling
This skill bundles executable Python scripts:
- `python3 skills/skill-creator/scripts/create_skill.py --name <name> --description <desc> --output <dir>`: Scaffolds a complete skill directory.
- `python3 skills/skill-creator/scripts/package_skill.py --skill-dir <dir>`: Validates frontmatter and packages the skill into a distribution ZIP.
