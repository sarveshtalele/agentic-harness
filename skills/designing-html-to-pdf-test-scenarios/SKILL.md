---
name: designing-html-to-pdf-test-scenarios
description: >
  Designs deterministic test cases and a scenario matrix for an HTML to PDF
  converter across positive, negative, boundary and exception categories for
  headings, tables, images, CSS, page breaks, encodings and very large files,
  each with an exact expected result. Use when a quality engineer needs
  structured, repeatable test designs for validating an HTML to PDF conversion
  engine.
author: admin
---

# Designing HTML to PDF Test Scenarios

This skill takes an HTML to PDF converter specification and produces a set of
structured, repeatable test designs covering all key features and categories.

## Steps

1. **Analyze the specification** – Identify the features explicitly listed:
   headings, tables, images, CSS, page breaks, encodings, and very large files.
2. **For each feature, define test cases** under these categories:
   - **positive** – valid inputs should produce correct output.
   - **negative** – invalid or malformed inputs should be handled gracefully (error or fallback).
   - **boundary** – edge values (maximum, minimum, large, etc.).
   - **exception** – unsupported constructs or corrupted data.
3. **For every test case, record**:
   - id (e.g., `H-POS-01`)
   - feature
   - category
   - input description or HTML snippet
   - expected result (exact, deterministic)
4. **Compile all cases into a scenario matrix** – a markdown table mapping each
   feature to its coverage across the four categories.
5. **Output the matrix** using `assets/scenario-matrix-template.md` and the
   full case details using `assets/test-case-detail-template.md`.

## Decision Rules

- Every test case must be deterministic – same input always produces same output.
- Positive cases cover supported features with valid data.
- Negative cases use invalid/malformed input; expect an error, gracefully
  degraded output, or fallback behavior.
- Boundary cases target the documented limits (see
  [references/feature-boundaries.md](references/feature-boundaries.md)).
- Exception cases target unsupported constructs (e.g., `<canvas>`, corrupted
  HTML, unclosed tags).
- Do not create cases for features not mentioned in the specification.

## References

- [Test Design Rules](references/test-design-rules.md)
- [Feature Boundaries](references/feature-boundaries.md)

## Outputs

- Scenario matrix (markdown table) per `assets/scenario-matrix-template.md`
- Test case details (structured markdown document) per
  `assets/test-case-detail-template.md`
