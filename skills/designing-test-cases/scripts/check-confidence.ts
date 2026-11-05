// CLI for the confidence-reviewer's per-case record: checks the arithmetic and the verdict rule, and that every cited
// file:line exists in the repository under test. Exit 1 when any record fails; a citation that does not exist makes that case REJECT.
//   node check-confidence.ts <confidence.json> --kind design|code [--source <repo>] [--stamp <label>]
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { parseArgs } from "node:util";
import { isMain, projectRoot, safeWrite, localIso } from "../../../hooks/src/hook-common.ts";
import { checkDoc, type Kind } from "../../../hooks/src/confidence.ts";

if (isMain(import.meta.url)) {
  const { values: v, positionals: [file] } = parseArgs({ allowPositionals: true, options: { kind: { type: "string" }, source: { type: "string" }, stamp: { type: "string" } } });
  if (!file || (v.kind !== "design" && v.kind !== "code")) {
    console.error("usage: node check-confidence.ts <confidence.json> --kind design|code [--source <repo>] [--stamp <label>]");
    process.exit(2);
  }
  const root = projectRoot({}), source = resolve(v.source ?? root), path = resolve(root, file);
  const doc = JSON.parse(readFileSync(path, "utf-8"));
  const { items, summary } = checkDoc(doc, v.kind as Kind, source, true);
  for (const i of items) {
    console.log(`${i.tc_id}\t${i.total}\t${i.effective}\t${i.evidence}`);
    for (const p of i.problems) console.log(`  problem: ${p}`);
  }
  console.log(`${summary.count} cases: ${summary.approved} APPROVED, ${summary.revise} REVISE, ${summary.reject} REJECT; average ${summary.average}; ${summary.low} low confidence; ${summary.problems} with problems`);
  // records that the evidence was verified where the source lives, for folders that hold only the outputs (examples)
  if (v.stamp && !summary.problems) safeWrite(path, JSON.stringify({ ...doc, evidence_checked: `${summary.evidence.verified} of ${summary.count} verified against ${v.stamp} on ${localIso().slice(0, 10)}` }, null, 2) + "\n", root);
  process.exit(summary.problems ? 1 : 0);
}
