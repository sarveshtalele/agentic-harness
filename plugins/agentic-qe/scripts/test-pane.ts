// Created 2026-11-03 00:20 IST by agentic-qe 1.4.1.
// Runs the pane mod's tests with `claude plugin test`. That command runs every *.test.ts under the folder it is given,
// so this copies only the mod (manifest, hooks.json with the module alone, pane.tsx, its test, the state contract) into
// a temp folder first; the node:test suite in tests/plugin stays out of it. CLAUDE_BIN picks another claude binary.
import { cpSync, mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const repo = join(dirname(fileURLToPath(import.meta.url)), "..");
const dir = mkdtempSync(join(tmpdir(), "qe-pane-test-"));
try {
  for (const d of [".claude-plugin", "hooks", "types"]) mkdirSync(join(dir, d));
  cpSync(join(repo, ".claude-plugin", "plugin.json"), join(dir, ".claude-plugin", "plugin.json"));
  cpSync(join(repo, "types", "index.d.ts"), join(dir, "types", "index.d.ts"));
  for (const f of ["pane.tsx", "pane.test.tsx"]) cpSync(join(repo, "hooks", f), join(dir, "hooks", f));
  writeFileSync(join(dir, "hooks", "hooks.json"), JSON.stringify({ modules: ["./pane.tsx"] }) + "\n");
  const r = spawnSync(process.env.CLAUDE_BIN || "claude", ["plugin", "test", dir], { stdio: "inherit", shell: process.platform === "win32" });
  process.exitCode = r.status ?? 1;
} finally {
  rmSync(dir, { recursive: true, force: true });
}
