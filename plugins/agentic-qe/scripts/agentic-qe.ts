// Wrapper so `node scripts/agentic-qe.ts ...` keeps working; the CLI lives with the qe-doctor skill.
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const r = spawnSync(process.execPath, [join(import.meta.dirname, "..", "skills", "qe-doctor", "scripts", "agentic-qe.ts"), ...process.argv.slice(2)], { stdio: "inherit" });
process.exitCode = r.status ?? 1;
