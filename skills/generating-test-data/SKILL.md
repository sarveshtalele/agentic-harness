---
name: generating-test-data
description: Generates deterministic synthetic test fixtures, schema mocks, and boundary edge datasets. Use when preparing test data for test execution.
metadata:
  author: Sarvesh Talele
  version: "1.4.0"
---

# Generating Test Data

Synthesizes high-fidelity mock fixtures conforming to application JSON schemas, TypeScript types, or database tables.

## When to use
Activate when the data stage runs (plugin command `qe-data`), or when creating mock payloads and test fixtures for test automation suites.

## Features
- **Typed boundaries:** a Negative case gets the boundary set of its requirement's stated `input_type` (string, number or JSON), never one chosen from its wording. A requirement with no stated type gets no shared boundary set.
- **Negative & Edge Fixtures:** empty and whitespace strings, long strings, special characters, number extremes, empty and nested JSON.
- **Data Privacy & Masking:** Never embeds actual secrets or real user PII in synthetic fixtures. E-mail addresses, SSN-like and card-like numbers in a case's own data are masked.

There is no schema conformance yet: the platform has no data schema to check against.

## Workflow
1. Read the requirement's `input_type` and the case's own test data. Take field rules from [assets/schema-templates.json](assets/schema-templates.json).
2. Build valid, invalid and boundary datasets, masking anything that looks like PII or a credential.
3. Produce `04-design/fixtures.json` (ask before creating it).

## Platform code step
The platform builds the datasets in code in `qe/test_data.py` (`build_fixtures`), with no model call. Given `{"kind":"user|boundary|pagination|auth", ...}`, `synthesize` returns deterministic JSON and writes nothing. `fixtures.json` holds `datasets` (the shared sets) and `cases`, where each case id has exactly two keys: `data` (its own masked test data) and `uses` (the shared sets it uses).
