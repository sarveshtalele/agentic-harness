// Copies the screenshots of a Playwright JSON report into docs/qe/<app>/06-execution/evidence/e2e/, one file per
// image named by case and step, so reports and the dashboard can show them after test-results/ is cleaned.
// Images come from attachment bodies (base64, from testInfo.attach) or attachment paths. Only real PNG/JPEG data is kept.
import { readFileSync, realpathSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { isMain, isInside, projectRoot, safeWrite } from "../../../hooks/src/hook-common.ts";
import { caseIdOf } from "./parse-junit.ts";

export const MAX_IMAGE = 5 * 1024 * 1024;
export interface Shot { caseId: string; name: string; file: string; status: string }

const kind = (b: Uint8Array): "png" | "jpg" | null =>
  b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47 ? "png" : b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff ? "jpg" : null;
const slug = (s: string): string => s.replace(/[^A-Za-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "shot";

/** Every image attachment in a Playwright JSON report: [caseId, attachment name, bytes, result status]. Paths must stay inside root. */
export function screenshotsOf(report: any, root: string): { caseId: string; name: string; data: Uint8Array; status: string }[] {
  const out: { caseId: string; name: string; data: Uint8Array; status: string }[] = [];
  const walk = (suite: any, titles: string[]) => {
    for (const s of suite?.suites ?? []) walk(s, [...titles, String(s.title ?? "")]);
    for (const spec of suite?.specs ?? []) {
      const caseId = caseIdOf([...titles, spec.title ?? ""].join(" ")) ?? caseIdOf(String(spec.file ?? ""));
      for (const t of spec.tests ?? []) for (const r of t.results ?? []) for (const a of r.attachments ?? []) {
        if (!/^image\/(png|jpe?g)$/.test(String(a.contentType))) continue;
        let data: Uint8Array | null = null;
        if (typeof a.body === "string") data = Buffer.from(a.body, "base64");
        else if (typeof a.path === "string") {
          const p = resolve(root, a.path);
          // real path, so a symlink inside the project cannot pull in a file from outside it (AQE140-009)
          try { const r = realpathSync(p); if (isInside(realpathSync(root), r) && statSync(r).size <= MAX_IMAGE) data = readFileSync(r); } catch { /* cleaned up */ }
        }
        if (data && data.length <= MAX_IMAGE && kind(data)) out.push({ caseId: caseIdOf(String(a.name ?? "")) ?? caseId ?? "UNMAPPED", name: String(a.name ?? "screenshot"), data, status: String(r.status ?? "") });
      }
    }
  };
  walk(report, []);
  return out;
}

/** Writes the screenshots to <outDir> (inside root) and returns what was written, in report order. */
export function collectEvidence(reportFile: string, outDir: string, root: string): Shot[] {
  const report = JSON.parse(readFileSync(resolve(root, reportFile), "utf-8"));
  const seen = new Map<string, number>();
  return screenshotsOf(report, root).map((s) => {
    const base = `${s.caseId}-${slug(s.name.replace(s.caseId, ""))}`;
    const n = (seen.get(base) ?? 0) + 1; seen.set(base, n);
    const file = join(outDir, `${base}${n > 1 ? `-${n}` : ""}.${kind(s.data)}`);
    safeWrite(file, s.data, root);
    return { caseId: s.caseId, name: s.name, file, status: s.status };
  });
}

// CLI: node collect-evidence.ts <playwright.json> docs/qe/<app>/06-execution/evidence/e2e
if (isMain(import.meta.url)) {
  const [report, out] = process.argv.slice(2);
  if (!report || !out || !/^docs\/qe\/[A-Za-z0-9._-]+\/06-execution\/evidence(\/|$)/.test(out)) {
    console.error("usage: node collect-evidence.ts <playwright.json> docs/qe/<app>/06-execution/evidence/e2e");
    process.exit(2);
  }
  const root = projectRoot({});
  const shots = collectEvidence(report, out, root);
  for (const s of shots) console.log(`${s.caseId}\t${s.status}\t${s.file}`);
  console.log(`${shots.length} screenshot(s) written to ${out}`);
}
