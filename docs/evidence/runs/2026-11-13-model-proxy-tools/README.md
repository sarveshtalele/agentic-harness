# Withdrawn: "the model proxy does not pass the request's tools" (2026-11-13)

An earlier version of this file claimed that the LiteLLM proxy replaced the request's tools with stale ones. That claim
is withdrawn. Retests were inconsistent, and the owner uses the same proxy with tool calling every day without the problem.

The harness failures it was meant to explain had a cause in this project's stack, now fixed:

- **"Collected approval authority is no longer pending"** when one model response held three or more tool calls that each
  need approval. MAF AG-UI (1.8.0 and 1.8.1) shows such a batch one card at a time. When it shows the next card, it
  records the answers already collected as settled, though nothing has run. On the next resume it refuses those answers.
  A batch of two never reaches that path, so short tests passed. Fixed in `src/backend/maf/harness_kit/snapshots.py`
  (`_Approvals`); `tests/test_harness_parallel_approvals.py` runs batches of 2, 3 and 5 and checks each command ran once.
- After that error, every later turn in the thread was refused (`APPROVAL_RESUME_REQUIRED`). That is why the requirements
  turns of `../2026-11-13-qe-cycle-g5-gpt-5/` ended empty.
