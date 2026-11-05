import { readFileSync } from "node:fs";
import { resolve, sep } from "node:path";
import { pathToFileURL } from "node:url";

export interface Requirement {
  id: string;
  title: string;
  actor: string;
  tier: "product" | "component";
  behavior: string;
  sourceFile: string;
  lineNumber: number;
  evidenceQuote: string;
}

export function parseObservableRequirement(raw: {
  id: string;
  title: string;
  actor: string;
  tier: "product" | "component";
  behavior: string;
  sourceFile: string;
  lineNumber: number;
  evidenceQuote: string;
}): Requirement {
  if (!raw.evidenceQuote || raw.evidenceQuote.trim().length === 0) {
    throw new Error(`Requirement ${raw.id} rejected: Mandatory evidenceQuote is missing.`);
  }
  return {
    ...raw,
    tier: raw.tier || "component"
  };
}

const isCli = !!process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href;

/** Brownfield check: the evidence quote must appear verbatim in the cited source file under root. */
export function quoteInSource(root: string, req: { sourceFile: string; evidenceQuote: string }): boolean {
  const file = resolve(root, req.sourceFile);
  if (file !== resolve(root) && !file.startsWith(resolve(root) + sep)) return false;
  try { return readFileSync(file, "utf-8").includes(req.evidenceQuote.trim()); } catch { return false; }
}

// CLI: node extract-contracts.ts <requirements.json> [--root <repo>] -> JSON {accepted, rejected[]}
// Without --root only the mandatory quote is checked (greenfield: quotes come from user stories).
if (isCli) {
  const [file, flag, root] = process.argv.slice(2);
  if (!file) { console.error("usage: node extract-contracts.ts <requirements.json> [--root <repo>]"); process.exit(2); }
  const reqs: Requirement[] = JSON.parse(readFileSync(file, "utf-8"));
  const rejected: { id: string; error: string }[] = [];
  let accepted = 0;
  for (const r of reqs) {
    try {
      parseObservableRequirement(r);
      if (flag === "--root" && root && !quoteInSource(root, r)) throw new Error(`Requirement ${r.id} rejected: quote not found verbatim in ${r.sourceFile}.`);
      accepted++;
    } catch (e) { rejected.push({ id: r.id, error: (e as Error).message }); }
  }
  console.log(JSON.stringify({ accepted, rejected }, null, 2));
  process.exit(rejected.length ? 1 : 0);
}
