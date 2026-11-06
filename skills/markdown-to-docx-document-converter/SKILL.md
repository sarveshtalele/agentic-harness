---
name: markdown-to-docx-document-converter
description: "Autonomous skill for validating, executing, and verifying Markdown to DOCX Document Converter. Use when processing markdown to docx document converter requirements, executing domain contracts, or verifying state invariants. Grounded in project specifications and requirements."
metadata:
  author: "admin"
  version: "1.4.0"
  category: "custom-sdlc"
  tags: "agent-skill, markdown-to-docx-document-converter, maf-2.0"
---

# Markdown to DOCX Document Converter

Autonomous skill for validating, executing, and verifying Markdown to DOCX Document Converter. Use when processing markdown to docx document converter requirements, executing domain contracts, or verifying state invariants.

## Capabilities & Scope
- Grounded execution of domain workflows according to enterprise verification rules.
- Automated parameter validation, error handling, and structured evidence logging.

## Core Operational Workflow (Step-by-Step Checklist)
1. **Ingest markdown source file and validate formatting syntax**
2. **Parse markdown AST into headings, block elements, and paragraphs**
3. **Map styling, typography, and code blocks to OpenXML/DOCX specifications**
4. **Format embedded tables, images, hyperlinks, and metadata**
5. **Serialize to .docx binary, calculate checksum, and emit conversion trace**

## Quality & Security Guardrails
- **Sandboxed Execution**: Runs in isolated subshell with sanitized environment.
- **Deterministic**: Returns structured JSON responses with zero hallucinations.
- **Zero-Trust**: Does not permit unauthorized shell escapes or unvetted network calls.


### Provided Grounding Context:
create a skill to convert docx to md file

